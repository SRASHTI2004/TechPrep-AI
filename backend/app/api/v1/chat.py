from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.repositories.conversations import ConversationRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationOut,
    FeedbackRequest,
)
from app.services.chat_service import (
    ChatService,
    ChatUnavailableError,
    ConversationNotFoundError,
)

router = APIRouter(tags=["chat"])
settings = get_settings()


def _prepare(service: ChatService, user_id: UUID, body: ChatRequest):
    try:
        return service.prepare(user_id, body)
    except ConversationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found") from None
    except ChatUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
def chat(request: Request, body: ChatRequest, user: CurrentUser, db: DbSession):
    """Ask a question and get the whole answer as JSON (used by the eval and API clients)."""
    service = ChatService(db)
    turn = _prepare(service, user.id, body)
    try:
        return service.complete(turn)
    except ChatUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


@router.post("/chat/stream")
@limiter.limit(settings.rate_limit_chat)
def chat_stream(request: Request, body: ChatRequest, user: CurrentUser, db: DbSession):
    """Ask a question and receive Server-Sent Events: meta, sources, token..., done | error."""
    service = ChatService(db)
    turn = _prepare(service, user.id, body)
    return StreamingResponse(
        service.stream_events(turn),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # no proxy buffering
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: CurrentUser, db: DbSession):
    return ConversationRepository(db).list_for_owner(user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: UUID, user: CurrentUser, db: DbSession):
    conv = ConversationRepository(db).get_for_owner(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: UUID, user: CurrentUser, db: DbSession):
    repo = ConversationRepository(db)
    conv = repo.get_for_owner(conversation_id, user.id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    repo.delete(conv)
    db.commit()


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
def message_feedback(message_id: UUID, body: FeedbackRequest, user: CurrentUser, db: DbSession):
    message = ConversationRepository(db).get_message_for_owner(message_id, user.id)
    if message is None or message.role != "assistant":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    message.feedback = body.value
    db.commit()
