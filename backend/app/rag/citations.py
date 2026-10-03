"""Parse and validate inline citations like [1], [2][3] or [1, 4] in an LLM answer.

The LLM can hallucinate a citation number that doesn't exist. We never trust it: only numbers
that map to a source we actually sent count as citations. Invalid ones are reported (and counted
by the evaluation) instead of being linked.
"""

import re

from app.rag.prompts import REFUSAL

_CITATION = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]")

# Some models (e.g. gpt-oss) write citations as 【1】, 【1†L3-L5】 or with full-width
# brackets ［1］ instead of [1]. Same idea as _CITATION, but any bracket style, full-width
# commas, and an optional "†..." suffix.
_ANY_CITATION = re.compile(
    r"[\[【［]\s*(\d{1,2}(?:\s*[,，、]\s*\d{1,2})*)\s*(?:†[^\]】］\n]*)?[\]】］]"
)


def normalize_citations(text: str) -> str:
    """Rewrite every citation marker to the canonical [n] / [n, m] form."""

    def repl(match: re.Match[str]) -> str:
        if _CITATION.fullmatch(match.group(0)):
            return match.group(0)  # already canonical: leave its spacing untouched
        numbers = re.split(r"\s*[,，、]\s*", match.group(1).strip())
        return "[" + ", ".join(numbers) + "]"

    return _ANY_CITATION.sub(repl, text)


def extract_citation_numbers(answer: str) -> list[int]:
    """All cited numbers in order of first appearance (may include invalid ones)."""
    seen: list[int] = []
    for match in _CITATION.finditer(answer):
        for part in match.group(1).split(","):
            n = int(part)
            if n not in seen:
                seen.append(n)
    return seen


def validate_citations(answer: str, num_sources: int) -> tuple[list[int], list[int]]:
    """Return (valid, invalid) citation numbers, each in order of first appearance."""
    numbers = extract_citation_numbers(answer)
    valid = [n for n in numbers if 1 <= n <= num_sources]
    invalid = [n for n in numbers if not 1 <= n <= num_sources]
    return valid, invalid


def is_refusal(answer: str) -> bool:
    normalized = answer.strip().strip('"').lower().replace("’", "'")
    return normalized.startswith(REFUSAL.lower().rstrip(".")) or normalized.startswith(
        "i don't know"
    )
