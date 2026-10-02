from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QueryLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per question: what was retrieved, which LLM answered and how long it took.

    This is our own lightweight replacement for an observability SaaS: it is enough to debug
    bad answers ("what did retrieval return?") and to compute latency / refusal-rate stats.
    """

    __tablename__ = "query_logs"

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), default=None
    )
    question: Mapped[str] = mapped_column(Text)
    rewritten_question: Mapped[str | None] = mapped_column(Text, default=None)
    retrieval_mode: Mapped[str] = mapped_column(String(20))
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    top_score: Mapped[float | None] = mapped_column(Float, default=None)
    answered: Mapped[bool] = mapped_column(default=True)
    provider: Mapped[str | None] = mapped_column(String(50), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    retrieval_ms: Mapped[int] = mapped_column(Integer, default=0)
    generation_ms: Mapped[int] = mapped_column(Integer, default=0)
    total_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)
