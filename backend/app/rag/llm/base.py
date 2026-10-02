"""Provider-agnostic LLM interface. The rest of the app only knows about `LLMProvider`."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


class LLMError(Exception):
    """Any provider failure (network, auth, rate limit, safety block). Triggers fallback."""


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str: ...

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]: ...


def split_system(messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
    system = "\n\n".join(m.content for m in messages if m.role == "system")
    return system, [m for m in messages if m.role != "system"]
