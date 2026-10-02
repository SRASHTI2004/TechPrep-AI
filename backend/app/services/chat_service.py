"""The RAG chat flow.

    question
      → (follow-up?) rewrite into a standalone question using recent history
      → hybrid retrieval + rerank, scoped to the user's documents
      → relevance gate: nothing relevant? answer "I don't know" WITHOUT calling the LLM
      → prompt with numbered sources → LLM (streamed) → validate [n] citations
      → persist assistant message + query log

`prepare()` does everything up to the LLM call inside the request (so errors like
"conversation not found" are normal HTTP errors). `complete()` and `stream_events()` then
produce the answer as one JSON response or as Server-Sent Events.
"""

import json
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.query_log import QueryLog
from app.rag.citations import is_refusal, validate_citations
from app.rag.llm.base import ChatMessage, LLMError
from app.rag.llm.router import FallbackLLM, get_llm
from app.rag.prompts import (
    REFUSAL,
    build_answer_messages,
    build_rewrite_messages,
    format_source_header,
)
from app.rag.retrieval import RetrievalResult, RetrievedChunk, Retriever
from app.repositories.conversations import ConversationRepository
from app.repositories.query_logs import QueryLogRepository
from app.schemas.chat import ChatRequest, ChatResponse, Citation, Latency

log = get_logger(__name__)

_CITATION_MARK = re.compile(r"\s?\[\d{1,2}(?:\s*,\s*\d{1,2})*\]")


class ConversationNotFoundError(Exception):
    pass


class ChatUnavailableError(Exception):
    pass


@dataclass
class PreparedTurn:
    owner_id: UUID
    conversation_id: UUID
    user_message_id: UUID
    question: str
    rewritten_question: str | None
    retrieval: RetrievalResult
    sources: list[RetrievedChunk]
    llm_messages: list[ChatMessage] | None  # None => refused by the relevance gate
    llm: FallbackLLM | None
    started: float = field(default_factory=time.perf_counter)

    @property
    def refused(self) -> bool:
        return self.llm_messages is None

    @property
    def citations(self) -> list[Citation]:
        return [_to_citation(n, c) for n, c in enumerate(self.sources, start=1)]


def _to_citation(n: int, c: RetrievedChunk) -> Citation:
    return Citation(
        n=n,
        chunk_id=c.id,
        document_id=c.document_id,
        filename=c.filename,
        page=c.page,
        section=c.section,
        snippet=c.content[:300],
        score=round(c.score, 4),
    )


def relevance_threshold(reranked: bool) -> float:
    s = get_settings()
    return s.rerank_min_score if reranked else s.vector_min_similarity


class ChatService:
    def __init__(self, db: Session, retriever: Retriever | None = None):
        self.db = db
        self.settings = get_settings()
        self.conversations = ConversationRepository(db)
        self._retriever = retriever

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = Retriever(self.db)
        return self._retriever

    # ------------------------------------------------------------------ prepare
    def prepare(self, owner_id: UUID, req: ChatRequest) -> PreparedTurn:
        started = time.perf_counter()
        question = req.message.strip()
        if req.conversation_id:
            conv = self.conversations.get_for_owner(req.conversation_id, owner_id)
            if conv is None:
                raise ConversationNotFoundError
        else:
            conv = self.conversations.create(owner_id, title=question[:80])

        history = self._history(conv.id)
        try:
            llm: FallbackLLM | None = get_llm()
        except LLMError:
            llm = None

        rewritten = self._rewrite(question, history, llm) if history else None
        retrieval = self.retriever.search(
            owner_id, rewritten or question, document_ids=req.document_ids
        )

        # Relevance gate + context filtering: only sources above the threshold reach the LLM.
        threshold = relevance_threshold(retrieval.reranked)
        sources = [c for c in retrieval.chunks if c.score >= threshold]
        llm_messages = None
        if sources:
            if llm is None:
                raise ChatUnavailableError(
                    "No LLM provider is configured (set GEMINI_API_KEY or GROQ_API_KEY)."
                )
            numbered = [
                (format_source_header(n, c.filename, c.page, c.section), c.content)
                for n, c in enumerate(sources, start=1)
            ]
            llm_messages = build_answer_messages(rewritten or question, numbered, history)

        user_msg = self.conversations.add_message(conv.id, "user", question)
        self.db.commit()
        return PreparedTurn(
            owner_id=owner_id,
            conversation_id=conv.id,
            user_message_id=user_msg.id,
            question=question,
            rewritten_question=rewritten,
            retrieval=retrieval,
            sources=sources,
            llm_messages=llm_messages,
            llm=llm,
            started=started,
        )

    def _history(self, conversation_id: UUID) -> list[ChatMessage]:
        messages = self.conversations.recent_messages(
            conversation_id, self.settings.history_turns * 2
        )
        # Old answers cite *old* source numbers; strip them so the model can't reuse them.
        return [
            ChatMessage(
                m.role,  # type: ignore[arg-type]
                _CITATION_MARK.sub("", m.content) if m.role == "assistant" else m.content,
            )
            for m in messages
        ]

    def _rewrite(self, question: str, history: list[ChatMessage], llm) -> str | None:
        if not self.settings.query_rewrite_enabled or llm is None:
            return None
        try:
            out = llm.complete(
                build_rewrite_messages(question, history), temperature=0.0, max_tokens=400
            ).strip()
        except LLMError as exc:
            log.warning("query_rewrite_failed", error=str(exc)[:200])
            return None
        out = out.strip().strip('"').strip()
        return out if 0 < len(out) <= 500 else None

    # ------------------------------------------------------------------ answer
    def complete(self, turn: PreparedTurn) -> ChatResponse:
        if turn.refused:
            return self._finalize(turn, REFUSAL, generation_ms=0)
        t0 = time.perf_counter()
        try:
            answer = turn.llm.complete(turn.llm_messages)
        except LLMError as exc:
            self._finalize(turn, "", generation_ms=_ms(t0), error=str(exc))
            raise ChatUnavailableError("The language model is unavailable. Try again.") from exc
        return self._finalize(turn, answer, generation_ms=_ms(t0))

    def stream_events(self, turn: PreparedTurn) -> Iterator[str]:
        """Server-Sent Events: meta → sources → token* → done | error."""
        yield _sse(
            "meta",
            {
                "conversation_id": str(turn.conversation_id),
                "user_message_id": str(turn.user_message_id),
                "rewritten_question": turn.rewritten_question,
            },
        )
        yield _sse("sources", [c.model_dump(mode="json") for c in turn.citations])

        if turn.refused:
            yield _sse("token", {"text": REFUSAL})
            response = self._finalize(turn, REFUSAL, generation_ms=0)
            yield _sse("done", _done_payload(response))
            return

        parts: list[str] = []
        t0 = time.perf_counter()
        finished = False
        try:
            for token in turn.llm.stream(turn.llm_messages):
                parts.append(token)
                yield _sse("token", {"text": token})
            response = self._finalize(turn, "".join(parts), generation_ms=_ms(t0))
            finished = True
            yield _sse("done", _done_payload(response))
        except LLMError as exc:
            finished = True
            self._finalize(turn, "".join(parts), generation_ms=_ms(t0), error=str(exc))
            yield _sse("error", {"detail": "The language model failed. Please try again."})
        finally:
            if not finished:  # client disconnected mid-stream
                self._finalize(
                    turn, "".join(parts), generation_ms=_ms(t0), error="client disconnected"
                )

    # ------------------------------------------------------------------ persist
    def _finalize(
        self, turn: PreparedTurn, answer: str, generation_ms: int, error: str | None = None
    ) -> ChatResponse:
        """Validate citations, store the assistant message and the query log.

        Uses its own session: during streaming this runs after the request's session is gone.
        """
        answer = answer.strip()
        refused = turn.refused or is_refusal(answer)
        valid, invalid = validate_citations(answer, len(turn.sources)) if not refused else ([], [])
        all_citations = turn.citations
        cited = [all_citations[n - 1] for n in valid]
        llm = turn.llm
        provider = llm.name if (llm and not turn.refused) else None
        model = llm.model if (llm and not turn.refused) else None
        total_ms = _ms(turn.started)
        retrieval_ms = turn.retrieval.timings_ms.get("total_ms", 0)

        with SessionLocal() as db:
            message_id = None
            if not error:
                msg = ConversationRepository(db).add_message(
                    turn.conversation_id,
                    "assistant",
                    answer,
                    citations=[c.model_dump(mode="json") for c in cited],
                    answered=not refused,
                )
                message_id = msg.id
            QueryLogRepository(db).add(
                QueryLog(
                    owner_id=turn.owner_id,
                    message_id=message_id,
                    question=turn.question,
                    rewritten_question=turn.rewritten_question,
                    retrieval_mode=turn.retrieval.mode,
                    retrieved_chunk_ids=[str(c.id) for c in turn.retrieval.chunks],
                    top_score=turn.retrieval.top_score,
                    answered=not refused and not error,
                    provider=provider,
                    model=model,
                    retrieval_ms=retrieval_ms,
                    generation_ms=generation_ms,
                    total_ms=total_ms,
                    error=error[:2000] if error else None,
                )
            )
            db.commit()

        log.info(
            "chat_answered",
            answered=not refused,
            sources=len(turn.sources),
            cited=len(cited),
            invalid_citations=invalid,
            provider=provider,
            retrieval=turn.retrieval.timings_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
            error=error,
        )
        return ChatResponse(
            conversation_id=turn.conversation_id,
            message_id=message_id or turn.user_message_id,
            answer=answer,
            answered=not refused,
            citations=cited,
            sources=all_citations,
            invalid_citations=invalid,
            rewritten_question=turn.rewritten_question,
            provider=provider,
            model=model,
            latency=Latency(
                retrieval_ms=retrieval_ms, generation_ms=generation_ms, total_ms=total_ms
            ),
        )


def _done_payload(r: ChatResponse) -> dict:
    return r.model_dump(mode="json", exclude={"answer", "sources"})


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
