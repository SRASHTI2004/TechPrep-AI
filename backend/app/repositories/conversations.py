from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.conversation import Conversation, Message


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, owner_id: UUID, title: str) -> Conversation:
        conv = Conversation(owner_id=owner_id, title=title[:200])
        self.db.add(conv)
        self.db.flush()
        return conv

    def get_for_owner(self, conversation_id: UUID, owner_id: UUID) -> Conversation | None:
        return self.db.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.owner_id == owner_id
            )
        )

    def list_for_owner(self, owner_id: UUID, limit: int = 50) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.owner_id == owner_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def recent_messages(self, conversation_id: UUID, limit: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(list(self.db.scalars(stmt))))

    def add_message(self, conversation_id: UUID, role: str, content: str, **fields) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content, **fields)
        self.db.add(message)
        conv = self.db.get(Conversation, conversation_id)
        if conv is not None:
            conv.updated_at = utcnow()
        self.db.flush()
        return message

    def get_message_for_owner(self, message_id: UUID, owner_id: UUID) -> Message | None:
        return self.db.scalar(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Message.id == message_id, Conversation.owner_id == owner_id)
        )

    def rename(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title[:200]
        self.db.flush()
        return conversation

    def delete(self, conversation: Conversation) -> None:
        self.db.delete(conversation)
