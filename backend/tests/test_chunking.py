from app.rag.chunking import chunk_document, pack_text, split_markdown_sections
from app.rag.loaders import LoadedDocument, Page, clean_markdown

MD = """# Caching

Intro paragraph about caching that is long enough to stand on its own as a chunk of text here.

## Cache-aside

The application reads from the cache first. On a miss it loads from the database and writes \
the result into the cache. This is also called lazy loading.

```python
# not a heading inside code
def get(key):
    return cache.get(key)
```

## Write-through

The application writes to the cache and the cache writes to the database synchronously.

# Load balancing

Load balancers distribute incoming requests across multiple servers to improve availability.
"""


def test_heading_paths_and_code_fences():
    sections = split_markdown_sections(MD)
    paths = [s.path for s in sections]
    assert ("Caching",) in paths
    assert ("Caching", "Cache-aside") in paths
    assert ("Caching", "Write-through") in paths
    assert ("Load balancing",) in paths  # H1 resets the stack
    cache_aside = next(s for s in sections if s.path == ("Caching", "Cache-aside"))
    assert "# not a heading inside code" in cache_aside.body


def test_markdown_chunks_carry_section_and_embedding_text():
    doc = LoadedDocument("markdown", [Page(MD, None)])
    drafts = chunk_document(doc, size=1000, overlap=100, min_chars=40)
    by_section = {d.section: d for d in drafts}
    d = by_section["Caching > Cache-aside"]
    assert d.page is None
    assert d.embedding_text.startswith("Caching > Cache-aside\n\n")
    assert [x.chunk_index for x in drafts] == list(range(len(drafts)))


def test_tiny_sections_merge_forward():
    md = "# A\n\nshort\n\n# B\n\n" + "Long enough body text for section B. " * 5
    drafts = chunk_document(LoadedDocument("markdown", [Page(md, None)]), 1000, 100, min_chars=80)
    assert len(drafts) == 1
    assert drafts[0].section == "B"
    assert drafts[0].content.startswith("A: short")


def test_pack_respects_size_and_overlaps():
    sentences = " ".join(f"Sentence number {i} talks about topic {i}." for i in range(200))
    chunks = pack_text(sentences, size=300, overlap=60)
    assert len(chunks) > 5
    assert all(len(c) <= 300 for c in chunks)
    # Consecutive chunks share some text (the overlap).
    shared = sum(1 for a, b in zip(chunks, chunks[1:], strict=False) if a[-30:].split()[-1] in b)
    assert shared >= len(chunks) // 2


def test_hard_split_of_unbroken_text():
    chunks = pack_text("x" * 2500, size=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert sum(len(c) for c in chunks) >= 2500


def test_pdf_chunks_keep_page_numbers_and_never_cross_pages():
    pages = [Page(f"Page {n} text. " * 40, n) for n in (1, 2, 3)]
    drafts = chunk_document(LoadedDocument("pdf", pages), size=200, overlap=20, min_chars=10)
    assert {d.page for d in drafts} == {1, 2, 3}
    for d in drafts:
        assert f"Page {d.page} text" in d.content
        assert d.section is None


def test_clean_markdown_strips_noise_keeps_link_text():
    raw = (
        '<p align="center"><img src="x.png"></p>\n'
        "![diagram](images/a.png)\n"
        "See [the CAP theorem](https://example.com/cap) for details.\n"
        "<!-- hidden -->\n"
    )
    cleaned = clean_markdown(raw)
    assert "the CAP theorem for details" in cleaned
    assert "http" not in cleaned and "<" not in cleaned and "png" not in cleaned


def test_link_lists_and_further_reading_are_removed():
    raw = (
        "## Consistent hashing\n\n"
        "Consistent hashing maps keys onto a ring so adding a node only moves a few keys.\n\n"
        "### Source(s) and further reading\n\n"
        "* [Consistent hashing](https://example.com/a)\n"
        "* [Shard database architecture](https://example.com/b)\n"
        "* [Index](#index) * [Cache](#cache) * [Sharding](#sharding)\n"
        "A sentence with [one link](https://example.com/c) inside a long line of real prose.\n"
    )
    cleaned = clean_markdown(raw)
    assert "ring so adding a node" in cleaned
    assert "further reading" not in cleaned.lower()
    assert "Shard database architecture" not in cleaned
    assert "Index Cache Sharding" not in cleaned
    assert "A sentence with one link inside" in cleaned
