import pytest

from app.rag.citations import extract_citation_numbers, is_refusal, validate_citations
from app.rag.llm.base import ChatMessage, LLMError
from app.rag.llm.router import FallbackLLM

MSG = [ChatMessage("user", "hi")]


class Broken:
    name, model = "broken", "b"

    def complete(self, messages, **kw):
        raise LLMError("429 rate limited")

    def stream(self, messages, **kw):
        raise LLMError("429 rate limited")
        yield  # pragma: no cover


class Works:
    name, model = "works", "w"

    def complete(self, messages, **kw):
        return "ok"

    def stream(self, messages, **kw):
        yield from ["o", "k"]


class DiesMidStream:
    name, model = "dies", "d"

    def complete(self, messages, **kw):
        return "x"

    def stream(self, messages, **kw):
        yield "partial"
        raise LLMError("connection reset")


def test_complete_falls_back_and_records_provider():
    llm = FallbackLLM([Broken(), Works()])
    assert llm.complete(MSG) == "ok"
    assert llm.name == "works"


def test_stream_falls_back_before_first_token():
    llm = FallbackLLM([Broken(), Works()])
    assert "".join(llm.stream(MSG)) == "ok"
    assert llm.used.name == "works"


def test_stream_failure_after_first_token_is_raised_not_stitched():
    llm = FallbackLLM([DiesMidStream(), Works()])
    tokens = []
    with pytest.raises(LLMError):
        for t in llm.stream(MSG):
            tokens.append(t)
    assert tokens == ["partial"]


def test_all_providers_fail():
    with pytest.raises(LLMError):
        FallbackLLM([Broken(), Broken()]).complete(MSG)


def test_no_providers_configured():
    with pytest.raises(LLMError, match="No LLM provider"):
        FallbackLLM([])


def test_citation_parsing_and_validation():
    answer = "Sharding splits data [1]. Replicas serve reads [2][3]. See also [1, 4] and [9]."
    assert extract_citation_numbers(answer) == [1, 2, 3, 4, 9]
    valid, invalid = validate_citations(answer, num_sources=4)
    assert valid == [1, 2, 3, 4] and invalid == [9]


def test_refusal_detection():
    assert is_refusal("I don't know based on your documents.")
    assert is_refusal('"I don’t know based on your documents."')
    assert not is_refusal("Sharding splits data [1].")
