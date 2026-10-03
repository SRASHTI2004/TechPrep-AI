"""Chat flow with the fake LLM and hash embedder: citations, refusal gate, history, streaming."""

import json

import pytest

from app.models.query_log import QueryLog
from app.rag.llm.base import LLMError
from app.rag.prompts import REFUSAL

NOTES = b"""# Databases

## Sharding

Sharding splits a large database horizontally across several machines. Each shard holds a \
subset of the rows, chosen by a shard key such as the user id.

## Replication

Master-slave replication copies writes from a master to read replicas. Replicas serve reads \
and can be promoted if the master fails.
"""


@pytest.fixture
def notes(client, auth_headers):
    r = client.post(
        "/api/v1/documents",
        headers=auth_headers,
        files={"file": ("db.md", NOTES, "text/markdown")},
    )
    assert r.status_code == 202
    return r.json()


def _ask(client, headers, message, **extra):
    return client.post("/api/v1/chat", headers=headers, json={"message": message, **extra})


def parse_sse(text: str) -> list[tuple[str, object]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_answer_has_validated_page_level_citations(client, auth_headers, notes):
    r = _ask(client, auth_headers, "How does sharding split a database?")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answered"] is True
    assert "[1]" in body["answer"]
    assert body["citations"][0]["n"] == 1
    assert body["citations"][0]["filename"] == "db.md"
    assert body["citations"][0]["section"] == "Databases > Sharding"
    assert body["invalid_citations"] == []
    assert body["provider"] == "fake"
    assert body["latency"]["total_ms"] >= 0


def test_unrelated_question_refuses_without_calling_llm(client, auth_headers, notes, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("LLM must not be called when nothing relevant was retrieved")

    monkeypatch.setattr("app.rag.llm.fake.FakeProvider.complete", boom)
    r = _ask(client, auth_headers, "zebra giraffe safari")
    body = r.json()
    assert body["answered"] is False
    assert body["answer"] == REFUSAL
    assert body["citations"] == [] and body["sources"] == []


def test_user_without_documents_gets_refusal(client, other_auth_headers):
    body = _ask(client, other_auth_headers, "How does sharding work?").json()
    assert body["answered"] is False


def test_other_users_documents_are_never_used(client, auth_headers, other_auth_headers, notes):
    body = _ask(client, other_auth_headers, "How does sharding split a database?").json()
    assert body["answered"] is False and body["sources"] == []


def test_follow_up_is_rewritten_and_history_persisted(client, auth_headers, notes):
    first = _ask(client, auth_headers, "What is sharding?").json()
    conv_id = first["conversation_id"]
    second = _ask(client, auth_headers, "and what about replication?", conversation_id=conv_id)
    body = second.json()
    assert body["conversation_id"] == conv_id
    assert body["rewritten_question"].startswith("(standalone)")

    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers).json()
    roles = [m["role"] for m in detail["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][1]["citations"][0]["filename"] == "db.md"
    assert detail["title"] == "What is sharding?"


def test_conversation_isolation(client, auth_headers, other_auth_headers, notes):
    conv_id = _ask(client, auth_headers, "What is sharding?").json()["conversation_id"]
    assert (
        client.get(f"/api/v1/conversations/{conv_id}", headers=other_auth_headers).status_code
        == 404
    )
    r = _ask(client, other_auth_headers, "hi", conversation_id=conv_id)
    assert r.status_code == 404
    assert client.get("/api/v1/conversations", headers=other_auth_headers).json() == []


def test_streaming_event_sequence(client, auth_headers, notes):
    r = client.post(
        "/api/v1/chat/stream", headers=auth_headers, json={"message": "Explain sharding"}
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    names = [e for e, _ in events]
    assert names[0] == "meta" and names[1] == "sources" and names[-1] == "done"
    assert names.count("token") >= 2
    streamed = "".join(d["text"] for e, d in events if e == "token")
    assert "[1]" in streamed
    done = events[-1][1]
    assert done["answered"] is True and done["citations"][0]["n"] == 1


def test_streaming_refusal(client, auth_headers, notes):
    events = parse_sse(
        client.post(
            "/api/v1/chat/stream", headers=auth_headers, json={"message": "zebra giraffe safari"}
        ).text
    )
    assert [e for e, _ in events] == ["meta", "sources", "token", "done"]
    assert events[2][1]["text"] == REFUSAL and events[3][1]["answered"] is False


def test_llm_failure_mid_stream_emits_error_event_and_logs(
    client, auth_headers, notes, db, monkeypatch
):
    def failing_stream(self, messages, **kw):
        yield "Partial "
        raise LLMError("boom")

    monkeypatch.setattr("app.rag.llm.fake.FakeProvider.stream", failing_stream)
    events = parse_sse(
        client.post(
            "/api/v1/chat/stream", headers=auth_headers, json={"message": "Explain sharding"}
        ).text
    )
    assert events[-1][0] == "error"
    log = db.query(QueryLog).one()
    assert log.error and "boom" in log.error and log.answered is False


def test_feedback_and_admin_stats(client, auth_headers, notes):
    body = _ask(client, auth_headers, "What is sharding?").json()
    r = client.post(
        f"/api/v1/messages/{body['message_id']}/feedback", headers=auth_headers, json={"value": 1}
    )
    assert r.status_code == 204
    from tests.conftest import register_and_login

    admin = register_and_login(client, "admin@example.com")
    stats = client.get("/api/v1/admin/stats", headers=admin).json()
    assert stats["queries"]["total"] == 1
    assert stats["queries"]["feedback_up"] == 1
    assert stats["queries"]["answer_rate"] == 1.0


def test_feedback_on_someone_elses_message_is_404(client, auth_headers, other_auth_headers, notes):
    body = _ask(client, auth_headers, "What is sharding?").json()
    r = client.post(
        f"/api/v1/messages/{body['message_id']}/feedback",
        headers=other_auth_headers,
        json={"value": -1},
    )
    assert r.status_code == 404


def test_delete_conversation(client, auth_headers, notes):
    conv_id = _ask(client, auth_headers, "What is sharding?").json()["conversation_id"]
    assert (
        client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers).status_code == 204
    )
    assert client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers).status_code == 404


def test_every_source_is_persisted_with_its_cited_flag(client, auth_headers, notes):
    first = _ask(client, auth_headers, "How does sharding split a database?").json()
    conv_id = first["conversation_id"]
    second = _ask(
        client, auth_headers, "How does replication work?", conversation_id=conv_id
    ).json()

    detail = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers).json()
    answers = [m for m in detail["messages"] if m["role"] == "assistant"]
    # Each answer keeps its own sources (not just the latest answer's), with cited flags.
    for stored, live in zip(answers, [first, second], strict=True):
        assert stored["mode"] == "qa"
        assert [s["chunk_id"] for s in stored["sources"]] == [
            s["chunk_id"] for s in live["sources"]
        ]
        cited = {c["n"] for c in live["citations"]}
        assert cited and {s["n"] for s in stored["sources"] if s["cited"]} == cited
        for s in stored["sources"]:
            assert {"filename", "page", "section", "snippet", "score", "cited"} <= s.keys()


def test_odd_citation_markers_are_normalized(client, auth_headers, notes, monkeypatch):
    monkeypatch.setattr(
        "app.rag.llm.fake.FakeProvider.complete",
        lambda self, messages, **kw: "Sharding splits a database 【1†L1-L2】.",
    )
    body = _ask(client, auth_headers, "How does sharding split a database?").json()
    assert body["answer"] == "Sharding splits a database [1]."
    assert [c["n"] for c in body["citations"]] == [1]


def test_rename_conversation(client, auth_headers, other_auth_headers, notes):
    conv_id = _ask(client, auth_headers, "What is sharding?").json()["conversation_id"]
    url = f"/api/v1/conversations/{conv_id}"
    r = client.patch(url, headers=auth_headers, json={"title": "  Sharding notes  "})
    assert r.status_code == 200 and r.json()["title"] == "Sharding notes"
    listed = client.get("/api/v1/conversations", headers=auth_headers).json()
    assert listed[0]["title"] == "Sharding notes"
    assert client.patch(url, headers=auth_headers, json={"title": "   "}).status_code == 422
    assert client.patch(url, headers=other_auth_headers, json={"title": "x"}).status_code == 404


def test_validation(client, auth_headers):
    assert _ask(client, auth_headers, "").status_code == 422
    assert _ask(client, auth_headers, "x" * 2001).status_code == 422
