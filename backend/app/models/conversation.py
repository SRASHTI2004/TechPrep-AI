from uuid import UUID

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict]] = mapped_column(JSONB, default=list)  # cited sources only
    # Every source the model was given, each with a "cited" flag (for the sources panel).
    sources: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    mode: Mapped[str | None] = mapped_column(String(20), default=None)  # "qa" | "summary"
    answered: Mapped[bool | None] = mapped_column(default=None)  # False = "I don't know"
    feedback: Mapped[int | None] = mapped_column(SmallInteger, default=None)  # 1 / -1

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
