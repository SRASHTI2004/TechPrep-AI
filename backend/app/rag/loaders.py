"""Turn an uploaded file into clean text pages.

PDFs keep one entry per page (so citations can say "p. 14"); Markdown/text is one "page"
with no page number, because their structure comes from headings instead.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Page:
    text: str
    number: int | None  # 1-based for PDFs, None for markdown/text


@dataclass(frozen=True)
class LoadedDocument:
    kind: str  # "pdf" | "markdown" | "text"
    pages: list[Page]

    @property
    def num_pages(self) -> int | None:
        return len(self.pages) if self.kind == "pdf" else None


class LoaderError(Exception):
    """A problem with the file itself (user-facing message, not retried)."""


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG = re.compile(r"</?[a-zA-Z][^>]*>")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:[^()]|\([^)]*\))*\)")
_MD_REF_DEF = re.compile(r"^\s*\[[^\]]+\]:\s+\S+.*$", re.MULTILINE)
_BARE_URL_LINE = re.compile(r"^\s*https?://\S+\s*$", re.MULTILINE)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_link_list_line(line: str) -> bool:
    """True for lines that are mostly hyperlinks, e.g. "* [Foo](url) * [Bar](url)".

    Reference lists, tables of contents and "further reading" sections contain the exact
    keywords of a topic but none of its explanation, so they win keyword *and* rerank
    matches while being useless as answer context. Removing them is a big precision win.
    """
    if not _MD_LINK.search(line):
        return False
    # What's left once the links are removed: real prose has words, a link list has only
    # bullets and separators ("*", "-", "|", "∙").
    residual_words = re.findall(r"[^\W\d_]{2,}", _MD_LINK.sub(" ", line))
    return len(residual_words) <= 2


_FURTHER_READING = re.compile(
    r"^#{1,6}\s*(source\(s\)( and further reading)?|sources|further reading|references)"
    r"(\s*:.*)?$",
    re.IGNORECASE,
)


def clean_markdown(text: str) -> str:
    """Remove markup that adds tokens but no meaning (images, HTML, URLs, link lists)."""
    kept: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if _FURTHER_READING.match(line.strip()) or _is_link_list_line(line):
            continue
        kept.append(line)
    text = "\n".join(kept)
    text = _HTML_COMMENT.sub("", text)
    text = _MD_IMAGE.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    text = _MD_REF_DEF.sub("", text)
    text = _BARE_URL_LINE.sub("", text)
    return clean_text(text)


def _fix_pdf_text(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join hyphenated line breaks
    text = re.sub(r"\bPage \d+ of \d+\b", "", text)
    return clean_text(text)


def load_pdf(path: Path) -> LoadedDocument:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise LoaderError("Password-protected PDFs are not supported")
        pages = [
            Page(text=_fix_pdf_text(page.extract_text() or ""), number=i)
            for i, page in enumerate(reader.pages, start=1)
        ]
    except PdfReadError as exc:
        raise LoaderError(f"Could not read PDF: {exc}") from exc
    return LoadedDocument(kind="pdf", pages=pages)


def load_document(path: Path, content_type: str) -> LoadedDocument:
    if content_type == "application/pdf":
        return load_pdf(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    if content_type == "text/markdown":
        return LoadedDocument(kind="markdown", pages=[Page(clean_markdown(raw), None)])
    return LoadedDocument(kind="text", pages=[Page(clean_text(raw), None)])
