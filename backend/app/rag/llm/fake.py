"""Deterministic fake LLM for tests and offline demos. Never calls the network.

- Query-rewrite prompts: returns the follow-up question unchanged (prefixed, so tests can see
  the rewrite happened).
- Answer prompts: quotes the first sentence of source [1] and cites it.
- No sources: returns the refusal sentence.
"""

import re
from collections.abc import Iterator

from app.rag.llm.base import ChatMessage
from app.rag.prompts import REFUSAL, REWRITE_MARKER

_SOURCE_1 = re.compile(
    r"^\[1\][^\n]*\n(.+?)(?:\n\n\[\d+\] |\n\nQuestion:|\Z)", re.DOTALL | re.MULTILINE
)


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def complete(self, messages: list[ChatMessage], *, temperature=None, max_tokens=None) -> str:
        last = messages[-1].content
        if any(REWRITE_MARKER in m.content for m in messages if m.role == "system"):
            question = last.rsplit("Follow-up question:", 1)[-1].strip()
            return f"(standalone) {question}"
        match = _SOURCE_1.search(last)
        if not match:
            return REFUSAL
        first_sentence = re.split(r"(?<=[.!?])\s", match.group(1).strip(), maxsplit=1)[0]
        return f"According to your notes, {first_sentence[:300]} [1]"

    def stream(self, messages, *, temperature=None, max_tokens=None) -> Iterator[str]:
        yield from re.findall(r"\S+\s*", self.complete(messages))
