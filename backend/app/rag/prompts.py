"""Prompt templates. Kept in one place so they can be versioned and evaluated together."""

from app.rag.llm.base import ChatMessage

REFUSAL = "I don't know based on your documents."
REWRITE_MARKER = "[[standalone-rewrite]]"

ANSWER_SYSTEM_PROMPT = f"""You are TechPrep, a study assistant. You answer questions using \
ONLY the numbered sources, which are excerpts from the user's own notes and documents.

Rules:
1. Use only facts stated in the sources. Do not add outside knowledge, even if you know the answer.
2. Cite the supporting source number in square brackets after every factual sentence, e.g. [1] \
or [2][3]. Only cite numbers that appear in the sources.
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


def build_rewrite_messages(question: str, history: list[ChatMessage]) -> list[ChatMessage]:
    convo = "\n".join(
        f"{'User' if m.role == 'user' else 'Assistant'}: {m.content[:600]}" for m in history
    )
    return [
        ChatMessage("system", REWRITE_SYSTEM_PROMPT),
        ChatMessage("user", f"Conversation:\n{convo}\n\nFollow-up question: {question}"),
    ]
