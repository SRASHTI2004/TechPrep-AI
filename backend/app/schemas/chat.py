from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

AnswerMode = Literal["qa", "summary"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: UUID | None = None
    # Optional: restrict retrieval to these documents (must belong to the user).
    document_ids: list[UUID] | None = Field(default=None, max_length=50)
    # "auto" detects summary requests ("summarize this document"); the UI's Summarize
    # buttons send "summary" explicitly.
    mode: Literal["auto", "qa", "summary"] = "auto"


class Citation(BaseModel):
    n: int  # the number used in the answer text: [n]
    chunk_id: UUID
    document_id: UUID
    filename: str
    page: int | None
    section: str | None
    snippet: str
    score: float


class Source(Citation):
    """A source the model was given, and whether the final answer cited it."""

    cited: bool = False


class Latency(BaseModel):
    retrieval_ms: int
    generation_ms: int
    total_ms: int


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    answered: bool  # False = "I don't know based on your documents."
    mode: AnswerMode = "qa"
    citations: list[Citation]  # only sources the answer actually cites (validated)
    sources: list[Source]  # every source the model was given, with a cited flag
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
    sources: list[Source] = []
    mode: AnswerMode | None = None
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


class ConversationUpdate(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class FeedbackRequest(BaseModel):
    value: Literal[1, -1]
