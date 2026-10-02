"""Import every model here so Alembic autogenerate and `Base.metadata` see them all."""

from app.models.chunk import Chunk
from app.models.conversation import Conversation, Message
from app.models.document import Document, DocumentStatus
from app.models.query_log import QueryLog
from app.models.user import Role, User

__all__ = [
    "Chunk",
    "Conversation",
    "Document",
    "DocumentStatus",
    "Message",
    "QueryLog",
    "Role",
    "User",
]
