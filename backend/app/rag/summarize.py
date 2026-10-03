"""Whole-document summaries.

Why a separate path: retrieval answers *questions*. "Give me a summary of the doc" contains no
topic words to search for, so hybrid search returns weak matches, the relevance gate fires and
the chat says "I don't know". A summary needs the whole document, not the top 5 chunks.

So summary requests skip retrieval:
1. Read every chunk of the target documents in reading order.
2. Group consecutive chunks into citeable *units* (one PDF page or one Markdown section).
   Adjacent units are merged until there are at most `max_units`, so citation numbers stay
   small and every unit still points at a real page or section.
3. If all the text fits in one prompt: one LLM call ("stuff"). Otherwise map-reduce:
   summarize batches of units into cited bullet notes (map), then merge the notes (reduce).
   Citation numbers are global, so the final summary still cites pages/sections.
4. The reduce model sometimes drops the [n] markers it was told to keep. `restore_citations`
   gives every uncited summary bullet the citations of the most similar note bullet (word
   overlap), so the summary stays verifiable. Citations are still validated afterwards.
"""

import re
from collections.abc import Iterable
from pathlib import Path
from uuid import UUID

from app.rag.retrieval import RetrievedChunk

_SUMMARY_WORDS = re.compile(
    r"\b(summari[sz](?:e|es|ed|ing|ation)|summary|summaries|tl;?\s?dr|overview|gist|"
    r"key (?:points|takeaways|ideas)|main (?:points|ideas|topics))\b",
    re.IGNORECASE,
)
# Words that point at the uploaded material itself rather than at a topic.
_DOC_WORDS = re.compile(
    r"\b(doc|docs|document|documents|file|files|pdf|pdfs|notes|upload|uploads|uploaded|"
    r"this|these|that|it|everything|all|whole|entire|chapter|lecture|slides)\b",
    re.IGNORECASE,
)
_FILE_NAME = re.compile(r"\b[\w-]+\.(?:pdf|md|markdown|txt)\b", re.IGNORECASE)
# "a summary of my notes ON SHARDING" is a question about a topic: normal retrieval is right.
_TOPIC_TAIL = re.compile(
    r"\b(?:on|about|regarding)\s+(?!(?:this|these|that|it|my|the|all)\b)\w", re.IGNORECASE
)
_FILLER = {
    "a", "an", "the", "me", "my", "i", "you", "can", "could", "would", "please", "pls", "give",
    "provide", "write", "make", "want", "need", "quick", "short", "brief", "just", "of", "for",
    "now", "us", "some",
}  # fmt: skip


def detect_summary_intent(text: str) -> bool:
    """True for "summarize this document", "tl;dr", "key points of my notes", ...

    False for topic questions that merely use the word, like "summarize the CAP theorem",
    "give an overview of caching" or "summary of my notes on sharding": retrieval handles
    those better.
    """
    if not _SUMMARY_WORDS.search(text) or _TOPIC_TAIL.search(text):
        return False
    if _DOC_WORDS.search(text) or _FILE_NAME.search(text):
        return True
    rest = re.findall(r"[a-z0-9']+", _SUMMARY_WORDS.sub(" ", text.lower()))
    return all(word in _FILLER for word in rest)  # a bare command: "summarize", "tl;dr"


def documents_named_in(text: str, documents: Iterable[tuple[UUID, str]]) -> list[UUID]:
    """Documents whose file name (or name without extension) appears in the text."""
    lowered = text.lower()
    found = []
    for doc_id, filename in documents:
        name = filename.lower()
        stem = Path(name).stem
        candidates = {name, stem, re.sub(r"[_-]+", " ", stem)}
        if any(len(c) >= 4 and c in lowered for c in candidates):
            found.append(doc_id)
    return found


def build_units(
    rows: Iterable[tuple[object, str]], max_units: int, unit_chars: int
) -> list[RetrievedChunk]:
    """Group (chunk, filename) rows, already in reading order, into citeable units."""
    units: list[RetrievedChunk] = []
    for chunk, filename in rows:
        last = units[-1] if units else None
        same_place = last is not None and (last.document_id, last.page, last.section) == (
            chunk.document_id,
            chunk.page,
            chunk.section,
        )
        if same_place and len(last.content) + len(chunk.content) <= unit_chars:
            last.content += "\n\n" + chunk.content
            continue
        units.append(
            RetrievedChunk(
                id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                content=chunk.content,
                section=chunk.section,
                page=chunk.page,
                chunk_index=chunk.chunk_index,
                similarity=1.0,  # not a relevance score: the whole document is used
            )
        )
    return _merge_to_limit(units, max_units)


def _merge_to_limit(units: list[RetrievedChunk], max_units: int) -> list[RetrievedChunk]:
    """Merge the smallest adjacent pair (same document) until at most max_units remain."""
    units = list(units)
    while len(units) > max_units:
        pairs = [
            (len(units[i].content) + len(units[i + 1].content), i)
            for i in range(len(units) - 1)
            if units[i].document_id == units[i + 1].document_id
        ]
        if not pairs:
            break  # every document is already a single unit
        _, i = min(pairs)
        units[i : i + 2] = [_merge(units[i], units[i + 1])]
    return units[:max_units]  # very many small documents: keep the first ones


def _merge(a: RetrievedChunk, b: RetrievedChunk) -> RetrievedChunk:
    if a.page and b.page:
        section = f"pp. {a.page}–{b.page}" if b.page != a.page else a.section
    else:
        section = _common_section(a.section, b.section)
    return RetrievedChunk(
        id=a.id,
        document_id=a.document_id,
        filename=a.filename,
        content=f"{a.content}\n\n{b.content}",
        section=section,
        page=a.page,
        chunk_index=a.chunk_index,
        similarity=1.0,
    )


def _common_section(a: str | None, b: str | None) -> str | None:
    if not a or not b:
        return a or b
    common = []
    for x, y in zip(a.split(" > "), b.split(" > "), strict=False):
        if x != y:
            break
        common.append(x)
    return " > ".join(common) if common else a


def plan_batches(
    units: list[RetrievedChunk], batch_chars: int, max_batches: int
) -> list[list[tuple[int, str]]]:
    """Split units into batches of (citation number, text) that fit one prompt each.

    If the document is longer than max_batches * batch_chars, every unit is trimmed to the same
    maximum length, so the summary still covers the whole document (each part's beginning)
    instead of only its first pages.
    """
    texts = [u.content[:batch_chars] for u in units]
    budget = batch_chars * max_batches
    if texts and sum(len(t) for t in texts) > budget:
        cap = max(300, budget // len(texts))
        texts = [t if len(t) <= cap else t[:cap].rsplit(" ", 1)[0] + " …" for t in texts]

    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    size = 0
    for n, text in enumerate(texts, start=1):
        if current and size + len(text) > batch_chars:
            batches.append(current)
            current, size = [], 0
        current.append((n, text))
        size += len(text)
    if current:
        batches.append(current)
    return batches


_CITE_GROUP = re.compile(r"(?:\s*\[\d{1,2}(?:\s*,\s*\d{1,2})*\])+")
_WORD = re.compile(r"[a-z0-9]{4,}")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def restore_citations(summary: str, notes: list[str], min_overlap: float = 0.25) -> str:
    """Give each uncited bullet / paragraph line of the summary the citations of its closest note.

    `notes` are the map outputs, whose bullets end with citations like [4][7]. A line is matched
    to the note line sharing the largest fraction of its words; below `min_overlap` it is left
    alone (better no citation than a wrong one). Headings, code and short lines are skipped.
    """
    cited_lines: list[tuple[set[str], str]] = []
    for note in notes:
        for line in note.splitlines():
            marks = re.findall(r"\[\d{1,2}(?:\s*,\s*\d{1,2})*\]", line)
            words = _words(_CITE_GROUP.sub(" ", line))
            if marks and words:
                cited_lines.append((words, "".join(dict.fromkeys(marks))))
    if not cited_lines:
        return summary

    out: list[str] = []
    in_code = False
    for line in summary.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
        skip = (
            in_code
            or not stripped
            or stripped.startswith(("#", "|", ">", "---"))
            or re.search(r"\[\d{1,2}(?:\s*,\s*\d{1,2})*\]", line)
            or (not _LIST_ITEM.match(line) and len(stripped.split()) < 8)
        )
        words = _words(line)
        if skip or len(words) < 3:
            out.append(line)
            continue
        overlap, marks = max((len(words & w) / len(words), m) for w, m in cited_lines)
        if overlap >= min_overlap:
            trailing = line[len(line.rstrip()) :]  # keep Markdown hard breaks ("  ")
            line = f"{line.rstrip()} {marks}{trailing}"
        out.append(line)
    return "\n".join(out)
