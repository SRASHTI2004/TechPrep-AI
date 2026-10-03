"""Deterministic fake LLM for tests and offline demos. Never calls the network.

- Query-rewrite prompts: returns the follow-up question unchanged (prefixed, so tests can see
  the rewrite happened).
- Answer and summary prompts: quotes the first sentence of the first source and cites it.
- Summary reduce prompts: returns the notes it was given under a heading.
- No sources: returns the refusal sentence.
"""

import re
from collections.abc import Iterator

from app.rag.llm.base import ChatMessage
from app.rag.prompts import REFUSAL, REWRITE_MARKER, SUMMARY_REDUCE_MARKER

_FIRST_SOURCE = re.compile(
    r"^\[(\d+)\][^\n]*\n(.+?)(?:\n\n\[\d+\] |\n\n(?:Question|Request):|\Z)",
    re.DOTALL | re.MULTILINE,
)
_NOTES = re.compile(r"Notes:\n\n(.+?)\n\nRequest:", re.DOTALL)


class FakeProvider:
    name = "fake"
    model = "fake-1"

    def complete(self, messages: list[ChatMessage], *, temperature=None, max_tokens=None) -> str:
        last = messages[-1].content
        system = "\n".join(m.content for m in messages if m.role == "system")
        if REWRITE_MARKER in system:
            question = last.rsplit("Follow-up question:", 1)[-1].strip()
            return f"(standalone) {question}"
        if SUMMARY_REDUCE_MARKER in system:
            notes = _NOTES.search(last)
            return f"Summary of your notes:\n\n{notes.group(1) if notes else ''}"
        match = _FIRST_SOURCE.search(last)
        if not match:
            return REFUSAL
        n, text = match.group(1), match.group(2).strip()
        first_sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        return f"According to your notes, {first_sentence[:300]} [{n}]"

    def stream(self, messages, *, temperature=None, max_tokens=None) -> Iterator[str]:
        yield from re.findall(r"\S+\s*", self.complete(messages))
