from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    # Optional: restrict retrieval to these documents (must belong to the user).
    document_ids: list[UUID] | None = Field(default=None, max_length=50)


class Citation(BaseModel):
    n: int  # the number used in the answer text: [n]
    chunk_id: UUID
    document_id: UUID
    filename: str
    page: int | None
    section: str | None
    snippet: str
    score: float


class Latency(BaseModel):
    retrieval_ms: int
    generation_ms: int
    total_ms: int


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    answered: bool  # False = "I don't know based on your documents."
    citations: list[Citation]  # only sources the answer actually cites (validated)
    sources: list[Citation]  # every source the model was given
    invalid_citations: list[int]
    rewritten_question: str | None
    provider: str | None
    model: str | None
    latency: Latency


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    citations: list[Citation] = []
    answered: bool | None
    feedback: int | None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class FeedbackRequest(BaseModel):
    value: Literal[1, -1]
