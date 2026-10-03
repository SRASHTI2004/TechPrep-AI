"""Summary mode: intent detection, units/batches (pure functions) and the full chat flow."""

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.models.query_log import QueryLog
from app.rag.citations import normalize_citations
from app.rag.prompts import NO_DOCUMENTS_TO_SUMMARIZE
from app.rag.summarize import (
    build_units,
    detect_summary_intent,
    documents_named_in,
    plan_batches,
    restore_citations,
)
from tests.test_chat import NOTES, parse_sse

OTHER = b"""# Caching

## Cache-aside

The application reads from the cache first and loads from the database on a miss.

## Write-through

Every write goes to the cache and the database at the same time.
"""


# --------------------------------------------------------------------------- intent
@pytest.mark.parametrize(
    "text",
    [
        "give me a summary of the doc",
        "Summarize this document",
        "summarise",
        "tl;dr",
        "What are the key points of my notes?",
        "Can you give an overview of everything I uploaded?",
        "Summarize system_design.md",
        "summary please",
    ],
)
def test_detects_summary_requests(text):
    assert detect_summary_intent(text)


@pytest.mark.parametrize(
    "text",
    [
        "Summarize the CAP theorem",
        "Give an overview of caching",
        "summary of my notes on sharding",
        "What does this document say about load balancing?",
        "What is a summary table in SQL?",
        "How does consistent hashing work?",
    ],
)
def test_topic_questions_are_not_summary_requests(text):
    assert not detect_summary_intent(text)


def test_documents_named_in():
    a, b = uuid4(), uuid4()
    docs = [(a, "system_design.md"), (b, "Lecture-Notes.pdf")]
    assert documents_named_in("summarize system_design.md", docs) == [a]
    assert documents_named_in("overview of the system design notes", docs) == [a]
    assert documents_named_in("tl;dr lecture notes", docs) == [b]
    assert documents_named_in("summarize it", docs) == []


# --------------------------------------------------------------------------- units / batches
@dataclass
class _Row:
    id: object
    document_id: object
    content: str
    section: str | None
    page: int | None
    chunk_index: int


def _rows(doc, specs):
    return [
        (_Row(uuid4(), doc, text, section, page, i), "f.pdf")
        for i, (text, section, page) in enumerate(specs)
    ]


def test_units_group_consecutive_chunks_of_the_same_page():
    doc = uuid4()
    rows = _rows(doc, [("a", None, 1), ("b", None, 1), ("c", None, 2)])
    units = build_units(rows, max_units=10, unit_chars=1000)
    assert [(u.page, u.content) for u in units] == [(1, "a\n\nb"), (2, "c")]


def test_units_are_merged_down_to_the_limit_with_page_ranges():
    doc = uuid4()
    rows = _rows(doc, [(f"page {p}", None, p) for p in range(1, 9)])
    units = build_units(rows, max_units=3, unit_chars=1000)
    assert len(units) == 3
    assert units[0].page == 1 and units[0].section.startswith("pp. 1–")
    assert all(u.score == 1.0 for u in units)


def test_plan_batches_trims_evenly_when_the_document_is_too_long():
    doc = uuid4()
    rows = _rows(doc, [("word " * 200, f"S{i}", None) for i in range(6)])  # 6 x 1000 chars
    units = build_units(rows, max_units=10, unit_chars=5000)
    batches = plan_batches(units, batch_chars=1500, max_batches=2)
    numbers = [n for batch in batches for n, _ in batch]
    assert numbers == [1, 2, 3, 4, 5, 6]  # every part is still covered, in order
    assert all(sum(len(t) for _, t in batch) <= 1500 for batch in batches)


def test_restore_citations_from_notes():
    notes = [
        "- Sharding splits a large database horizontally across machines [3][4].\n"
        "- Each shard holds a subset of rows chosen by a shard key [4].",
        "- Replication copies writes from the master to read replicas [7].",
    ]
    summary = (
        "**Overview**\n"
        "The notes cover how databases scale out across many machines and replicas.\n\n"
        "### Scaling\n"
        "- Sharding splits a big database horizontally across several machines.\n"
        "- Replication copies every write from the master to the read replicas.  \n"
        "- Already cited bullet [9].\n"
        "- Completely unrelated bullet about cooking pasta recipes."
    )
    out = restore_citations(summary, notes).split("\n")
    assert out[0] == "**Overview**" and out[3] == "### Scaling"
    assert out[4].endswith("machines. [3][4]")
    assert out[5] == "- Replication copies every write from the master to the read replicas. [7]  "
    assert out[6] == "- Already cited bullet [9]."
    assert out[7].endswith("recipes.")  # no similar note: better no citation than a wrong one


def test_normalize_citations():
    assert normalize_citations("A 【1】. B 【2†L3-L5】【3】. C ［4］.") == "A [1]. B [2][3]. C [4]."
    assert (
        normalize_citations("D 【1，2】 and [1, 2] and arr[1]") == "D [1, 2] and [1, 2] and arr[1]"
    )


# --------------------------------------------------------------------------- chat flow
def _upload(client, headers, name, content):
    r = client.post(
        "/api/v1/documents", headers=headers, files={"file": (name, content, "text/markdown")}
    )
    assert r.status_code == 202, r.text
    return r.json()


def _ask(client, headers, message, **extra):
    r = client.post("/api/v1/chat", headers=headers, json={"message": message, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def test_summary_of_the_doc_is_answered_with_section_citations(client, auth_headers, db):
    _upload(client, auth_headers, "db.md", NOTES)
    body = _ask(client, auth_headers, "give me a summary of the doc")
    assert body["answered"] is True and body["mode"] == "summary"
    assert body["citations"] and body["invalid_citations"] == []
    sections = {s["section"] for s in body["sources"]}
    assert sections == {"Databases > Sharding", "Databases > Replication"}
    assert db.query(QueryLog).one().retrieval_mode == "summary"


def test_long_documents_use_map_reduce_and_stream_progress(
    client, auth_headers, settings, monkeypatch
):
    monkeypatch.setattr(settings, "summary_batch_chars", 150)  # force several map batches
    _upload(client, auth_headers, "db.md", NOTES)
    events = parse_sse(
        client.post(
            "/api/v1/chat/stream", headers=auth_headers, json={"message": "Summarize my notes"}
        ).text
    )
    names = [e for e, _ in events]
    assert names[:2] == ["meta", "sources"] and names[-1] == "done"
    assert events[0][1]["mode"] == "summary"
    assert names.count("status") >= 3  # two or more map parts + "Writing the summary"
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert answer.startswith("Summary of your notes")
    done = events[-1][1]
    assert done["answer"] == answer.strip()
    assert done["answered"] is True and done["citations"] and done["invalid_citations"] == []


def test_summary_is_scoped_to_selected_or_named_documents(client, auth_headers):
    db_doc = _upload(client, auth_headers, "db.md", NOTES)
    _upload(client, auth_headers, "caching.md", OTHER)

    scoped = _ask(client, auth_headers, "Summarize", mode="summary", document_ids=[db_doc["id"]])
    assert {s["filename"] for s in scoped["sources"]} == {"db.md"}

    named = _ask(client, auth_headers, "Summarize caching.md")
    assert named["mode"] == "summary"
    assert {s["filename"] for s in named["sources"]} == {"caching.md"}

    everything = _ask(client, auth_headers, "tl;dr of all my documents")
    assert {s["filename"] for s in everything["sources"]} == {"db.md", "caching.md"}


def test_summary_without_documents_does_not_call_the_llm(client, other_auth_headers, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called without documents")

    monkeypatch.setattr("app.rag.llm.fake.FakeProvider.complete", boom)
    body = _ask(client, other_auth_headers, "summarize this document")
    assert body["answered"] is False and body["answer"] == NO_DOCUMENTS_TO_SUMMARIZE


def test_summary_never_reads_other_users_documents(client, auth_headers, other_auth_headers):
    doc = _upload(client, auth_headers, "db.md", NOTES)
    body = _ask(client, other_auth_headers, "Summarize", mode="summary", document_ids=[doc["id"]])
    assert body["answered"] is False and body["sources"] == []


def test_topic_question_with_summary_word_uses_normal_retrieval(client, auth_headers):
    _upload(client, auth_headers, "db.md", NOTES)
    body = _ask(client, auth_headers, "Summarize sharding")
    assert body["mode"] == "qa" and body["answered"] is True
