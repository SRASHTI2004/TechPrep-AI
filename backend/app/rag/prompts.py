"""Prompt templates. Kept in one place so they can be versioned and evaluated together."""

from app.rag.llm.base import ChatMessage

REFUSAL = "I don't know based on your documents."
REWRITE_MARKER = "[[standalone-rewrite]]"

ANSWER_SYSTEM_PROMPT = f"""You are TechPrep, a study assistant. You answer questions using \
ONLY the numbered sources, which are excerpts from the user's own notes and documents.

Rules:
1. Use only facts stated in the sources. Do not add outside knowledge, even if you know the answer.
2. Cite the supporting source number in square brackets at the end of EVERY sentence or \
bullet that states a fact, e.g. "Sharding splits data across machines [1]." Use [2][3] when \
several sources support it. Only cite numbers that appear in the sources. Never write a \
single citation for the whole answer at the end.
3. If the sources do not contain the answer, reply with exactly this sentence and nothing else: \
"{REFUSAL}"
4. If the sources only partly answer the question, answer that part and say what is missing.
5. Be concise and clear: short paragraphs or bullet points, normally under 200 words. Use \
Markdown. Put code in fenced code blocks."""

REWRITE_SYSTEM_PROMPT = f"""{REWRITE_MARKER}
Rewrite the user's follow-up question as a standalone question that can be understood without \
the conversation. Resolve words like "it", "that" or "the second one" using the conversation. \
Keep the meaning and the technical terms. If it is already standalone, return it unchanged. \
Output only the rewritten question, nothing else."""

# Markers on the first line of the system prompt tell the fake LLM (tests) which task it has.
SUMMARY_MARKER = "[[summary]]"
SUMMARY_MAP_MARKER = "[[summary-map]]"
SUMMARY_REDUCE_MARKER = "[[summary-reduce]]"

NO_DOCUMENTS_TO_SUMMARIZE = (
    "There are no ready documents to summarize. Upload notes on the Documents page, "
    "or wait until processing has finished."
)

_SUMMARY_RULES = """Rules:
1. Use only what the sources say. No outside knowledge.
2. Cite the source number in square brackets at the end of EVERY sentence or bullet, e.g. \
"Sharding splits rows across machines [3]." Only cite numbers that appear in the sources."""

SUMMARY_SYSTEM_PROMPT = f"""{SUMMARY_MARKER}
You are TechPrep, a study assistant. Summarize the user's document(s). The numbered sources \
are consecutive sections or pages of the document(s), in reading order.

{_SUMMARY_RULES}
3. Start with one or two sentences on what the document covers, then list the main points as \
short bullets, grouped under small headings when there are several topics.
4. Cover the whole document, not just the beginning. Normally under 350 words. Use Markdown."""

SUMMARY_MAP_SYSTEM_PROMPT = f"""{SUMMARY_MAP_MARKER}
You are helping to summarize a long document part by part. The numbered sources are \
consecutive sections or pages from one part of it.

{_SUMMARY_RULES}
3. Write the key points of this part as concise bullets (at most 8). Output only the bullets."""

SUMMARY_REDUCE_SYSTEM_PROMPT = f"""{SUMMARY_REDUCE_MARKER}
You are TechPrep, a study assistant. You are given bullet notes that summarize consecutive \
parts of the user's document(s). Each note already ends with citations like [3].

Write the final summary:
1. Start with one or two sentences on what the document covers, then the main points as short \
bullets, grouped under small headings when there are several topics.
2. End EVERY bullet with the citations of the notes it comes from, copied exactly, e.g. \
"- Sharding splits rows across machines [8][9]." Never invent or renumber citations. Do not \
add outside knowledge.
3. Remove repetition. Normally under 350 words. Use Markdown."""


def format_source_header(n: int, filename: str, page: int | None, section: str | None) -> str:
    where = f", p. {page}" if page else ""
    sec = f" | {section}" if section else ""
    return f"[{n}] {filename}{where}{sec}"


def build_answer_messages(
    question: str, sources: list[tuple[str, str]], history: list[ChatMessage]
) -> list[ChatMessage]:
    """sources: list of (header, content) in citation order."""
    blocks = "\n\n".join(f"{header}\n{content}" for header, content in sources)
    user = f"Sources:\n\n{blocks}\n\nQuestion: {question}"
    return [ChatMessage("system", ANSWER_SYSTEM_PROMPT), *history, ChatMessage("user", user)]


def _sources_block(sources: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"{header}\n{content}" for header, content in sources)


def build_summary_messages(request: str, sources: list[tuple[str, str]]) -> list[ChatMessage]:
    """One-call summary (the whole document fits in one prompt)."""
    user = f"Sources:\n\n{_sources_block(sources)}\n\nRequest: {request}"
    return [ChatMessage("system", SUMMARY_SYSTEM_PROMPT), ChatMessage("user", user)]


def build_summary_map_messages(request: str, sources: list[tuple[str, str]]) -> list[ChatMessage]:
    """Map step: cited bullet notes for one batch of sections/pages."""
    user = f"Sources:\n\n{_sources_block(sources)}\n\nRequest: {request}"
    return [ChatMessage("system", SUMMARY_MAP_SYSTEM_PROMPT), ChatMessage("user", user)]


def build_summary_reduce_messages(request: str, notes: list[str]) -> list[ChatMessage]:
    """Reduce step: merge the notes of every batch into the final summary."""
    joined = "\n\n".join(f"Part {i}:\n{note.strip()}" for i, note in enumerate(notes, start=1))
    user = f"Notes:\n\n{joined}\n\nRequest: {request}"
    return [ChatMessage("system", SUMMARY_REDUCE_SYSTEM_PROMPT), ChatMessage("user", user)]


def build_rewrite_messages(question: str, history: list[ChatMessage]) -> list[ChatMessage]:
    convo = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content[:600]}" for m in history
    )
    return [
        ChatMessage("system", REWRITE_SYSTEM_PROMPT),
        ChatMessage("user", f"Conversation:\n{convo}\n\nFollow-up question: {question}"),
    ]
