"""Structure-aware chunking.

Markdown: split by headings first, so every chunk knows where it lives
("System Design Primer > Cache > Cache-aside"). That heading path is stored in
`section`, shown in citations, and prepended to the text we embed. A chunk that says
"it updates the cache lazily" is then still findable by "cache-aside".

PDF: split within each page, so every chunk has exactly one page number to cite.

Inside a section/page, paragraphs are packed greedily up to `chunk_size` characters.
Oversized paragraphs fall back to sentences, then to a hard character split. Consecutive
chunks of the same section overlap by about `overlap` characters so a fact on a boundary
isn't lost.
"""

import re
from dataclasses import dataclass

from app.rag.loaders import LoadedDocument

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    content: str
    section: str | None
    page: int | None

    @property
    def embedding_text(self) -> str:
        return f"{self.section}\n\n{self.content}" if self.section else self.content


@dataclass(frozen=True)
class _Section:
    path: tuple[str, ...]
    body: str


def split_markdown_sections(text: str) -> list[_Section]:
    """Split markdown into (heading path, body) sections, ignoring '#' inside code fences."""
    sections: list[_Section] = []
    stack: list[tuple[int, str]] = []
    body: list[str] = []
    in_fence = False

    def flush() -> None:
        content = "\n".join(body).strip()
        if content:
            sections.append(_Section(tuple(title for _, title in stack), content))
        body.clear()

    for line in text.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
            body.append(line)
            continue
        match = None if in_fence else _HEADING.match(line)
        if match:
            flush()
            level, title = len(match.group(1)), match.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            body.append(line)
    flush()
    return sections


def _split_blocks(text: str) -> list[str]:
    """Paragraphs separated by blank lines; a fenced code block stays one block."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if _FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [b for b in blocks if b]


def _hard_split(text: str, size: int) -> list[str]:
    """Split on whitespace into pieces <= size (last resort when there are no sentences)."""
    pieces: list[str] = []
    line = ""
    for word in text.split():
        while len(word) > size:  # pathological token (e.g. base64): cut it
            if line:
                pieces.append(line)
                line = ""
            pieces.append(word[:size])
            word = word[size:]
        if line and len(line) + len(word) + 1 > size:
            pieces.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        pieces.append(line)
    return pieces


def _units(block: str, size: int) -> list[str]:
    """A block that fits is one unit; an oversized block becomes sentence-sized units."""
    if len(block) <= size:
        return [block]
    units: list[str] = []
    for sentence in _SENTENCE_END.split(block):
        sentence = sentence.strip()
        if sentence:
            units.extend(_hard_split(sentence, size) if len(sentence) > size else [sentence])
    return units


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0 or len(text) <= overlap:
        return ""
    tail = text[-overlap:]
    # Start the tail at a word boundary so we don't begin mid-word.
    space = tail.find(" ")
    return tail[space + 1 :] if 0 <= space < len(tail) - 1 else tail


def pack_text(text: str, size: int, overlap: int) -> list[str]:
    """Greedily pack paragraphs/sentences into chunks of at most `size` chars, with overlap."""
    # (unit, block number): units from the same paragraph are joined with a space,
    # units from different paragraphs with a blank line.
    units = [(u, i) for i, block in enumerate(_split_blocks(text)) for u in _units(block, size)]

    chunks: list[str] = []
    current, current_block = "", -1
    for unit, block in units:
        sep = " " if block == current_block else "\n\n"
        if current and len(current) + len(sep) + len(unit) > size:
            chunks.append(current)
            tail = _overlap_tail(current, overlap)
            fits = tail and len(tail) + len(sep) + len(unit) <= size
            current = f"{tail}{sep}{unit}" if fits else unit
        else:
            current = f"{current}{sep}{unit}" if current else unit
        current_block = block
    if current:
        chunks.append(current)
    return chunks


def chunk_document(
    doc: LoadedDocument, size: int, overlap: int, min_chars: int = 80
) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []

    def add(content: str, section: str | None, page: int | None) -> None:
        drafts.append(ChunkDraft(len(drafts), content, section, page))

    if doc.kind == "markdown":
        # Tiny sections (a heading with one line) merge into the next section, but only
        # when it is a sibling or child: never glue a fragment onto an unrelated topic.
        carry, carry_path = "", ()
        for sec in split_markdown_sections(doc.pages[0].text):
            if carry and sec.path[: len(carry_path) - 1] != carry_path[:-1]:
                add(carry, " > ".join(carry_path) or None, None)
                carry = ""
            labelled = f"{sec.path[-1]}: {sec.body}" if sec.path else sec.body
            body = f"{carry}\n\n{sec.body}" if carry else sec.body
            if len(body) < min_chars:
                carry = f"{carry}\n\n{labelled}" if carry else labelled
                carry_path = sec.path
                continue
            carry = ""
            section = " > ".join(sec.path) or None
            for piece in pack_text(body, size, overlap):
                add(piece, section, None)
        if carry:
            add(carry, " > ".join(carry_path) or None, None)
    else:
        for page in doc.pages:
            for piece in pack_text(page.text, size, overlap):
                if len(piece) >= min_chars or doc.kind != "pdf":
                    add(piece, None, page.number)
    return drafts
