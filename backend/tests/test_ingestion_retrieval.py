"""End-to-end: upload via API → inline ingestion → hybrid retrieval, with owner isolation."""

from uuid import UUID

import pytest

from app.models.document import DocumentStatus
from app.rag.retrieval import Retriever
from app.repositories.chunks import ChunkRepository
from tests.helpers import make_pdf

NOTES = b"""# Databases

## Sharding

Sharding splits a large database horizontally across several machines. Each shard holds a \
subset of the rows, chosen by a shard key such as the user id.

## Replication

Master-slave replication copies writes from a master to read replicas. Replicas serve reads \
and can be promoted if the master fails.

# Algorithms

## Knapsack

The 0-1 knapsack problem is solved with dynamic programming over item weights and capacity W.
"""


def _upload(client, headers, name, content, ctype):
    r = client.post("/api/v1/documents", headers=headers, files={"file": (name, content, ctype)})
    assert r.status_code == 202, r.text
    doc = client.get(f"/api/v1/documents/{r.json()['id']}", headers=headers).json()
    return doc


def _user_id(client, headers) -> UUID:
    return UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])


def test_markdown_ingestion_marks_ready_with_chunks(client, auth_headers, db):
    doc = _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    assert doc["status"] == "ready", doc
    assert doc["num_chunks"] >= 3
    chunks = ChunkRepository(db).list_for_document(UUID(doc["id"]), _user_id(client, auth_headers))
    sections = {c.section for c in chunks}
    assert "Databases > Sharding" in sections
    assert all(len(c.embedding) == 384 for c in chunks)


@pytest.mark.parametrize("mode", ["hybrid", "vector", "keyword"])
def test_retrieval_finds_the_right_section(client, auth_headers, db, mode):
    _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    owner = _user_id(client, auth_headers)
    result = Retriever(db).search(owner, "How does sharding split a database?", mode=mode)
    assert result.chunks, mode
    assert result.chunks[0].section == "Databases > Sharding"
    assert result.chunks[0].filename == "db.md"


def test_keyword_search_matches_exact_terms(client, auth_headers, db):
    _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    owner = _user_id(client, auth_headers)
    result = Retriever(db).search(owner, "knapsack", mode="keyword")
    assert result.chunks and "knapsack" in result.chunks[0].content.lower()


def test_retrieval_never_returns_other_users_chunks(client, auth_headers, other_auth_headers, db):
    _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    bob = _user_id(client, other_auth_headers)
    for mode in ("hybrid", "vector", "keyword"):
        assert Retriever(db).search(bob, "sharding replication knapsack", mode=mode).chunks == []


def test_document_filter(client, auth_headers, db):
    a = _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    b = _upload(
        client,
        auth_headers,
        "other.md",
        b"# Other\n\nSharding is also mentioned here " * 3,
        "text/markdown",
    )
    owner = _user_id(client, auth_headers)
    result = Retriever(db).search(owner, "sharding", document_ids=[UUID(b["id"])])
    assert result.chunks and {c.document_id for c in result.chunks} == {UUID(b["id"])}
    assert UUID(a["id"]) not in {c.document_id for c in result.chunks}


def test_pdf_ingestion_keeps_page_numbers(client, auth_headers, db):
    pdf = make_pdf(
        [
            "Page one is about consistent hashing on a ring of nodes and virtual nodes.",
            "Page two is about the CAP theorem: consistency, availability, partition tolerance.",
        ]
    )
    doc = _upload(client, auth_headers, "lecture.pdf", pdf, "application/pdf")
    assert doc["status"] == "ready", doc
    assert doc["num_pages"] == 2
    owner = _user_id(client, auth_headers)
    top = Retriever(db).search(owner, "CAP theorem partition tolerance").chunks[0]
    assert top.page == 2 and top.filename == "lecture.pdf"


def test_pdf_without_text_fails_with_readable_error(client, auth_headers):
    doc = _upload(client, auth_headers, "scan.pdf", make_pdf([""]), "application/pdf")
    assert doc["status"] == DocumentStatus.FAILED.value
    assert "OCR" in doc["error"]


def test_delete_removes_chunks(client, auth_headers, db):
    doc = _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    owner = _user_id(client, auth_headers)
    assert ChunkRepository(db).count_for_owner(owner) > 0
    client.delete(f"/api/v1/documents/{doc['id']}", headers=auth_headers)
    assert ChunkRepository(db).count_for_owner(owner) == 0


def test_reingest_replaces_chunks_without_duplicates(client, auth_headers, db):
    doc = _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    before = doc["num_chunks"]
    r = client.post(f"/api/v1/documents/{doc['id']}/reingest", headers=auth_headers)
    assert r.status_code == 202
    after = client.get(f"/api/v1/documents/{doc['id']}", headers=auth_headers).json()
    assert after["status"] == "ready" and after["num_chunks"] == before
    assert ChunkRepository(db).count_for_owner(_user_id(client, auth_headers)) == before


class KeywordReranker:
    """Fake cross-encoder: relevance = fraction of query words present in the text."""

    def __init__(self):
        self.calls: list[int] = []

    def score(self, query, texts):
        self.calls.append(len(texts))
        words = set(query.lower().split())
        return [len(words & set(t.lower().split())) / len(words) for t in texts]


def test_rerank_path_reorders_limits_candidates_and_sets_scores(client, auth_headers, db):
    _upload(client, auth_headers, "db.md", NOTES, "text/markdown")
    owner = _user_id(client, auth_headers)
    reranker = KeywordReranker()
    result = Retriever(db, reranker=reranker).search(
        owner, "master replicas promoted", rerank=True, rerank_candidates=3, top_k=2
    )
    assert result.reranked and reranker.calls == [3]  # only the top fused candidates
    assert len(result.chunks) == 2
    assert result.chunks[0].section == "Databases > Replication"
    assert result.chunks[0].score == result.chunks[0].rerank_score
    assert result.chunks[0].rerank_score >= result.chunks[1].rerank_score
    assert "rerank_ms" in result.timings_ms
