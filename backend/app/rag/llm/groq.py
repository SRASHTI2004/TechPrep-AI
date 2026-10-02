"""Groq (OpenAI-compatible chat API, very fast open-weight model inference, free tier)."""

from collections.abc import Iterator

from app.rag.llm.base import ChatMessage, LLMError


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_s: float,
        reasoning_effort: str | None = None,
    ):
        from groq import Groq

        # max_retries=1: fail over to the other provider quickly instead of retrying for long.
        self._client = Groq(api_key=api_key, timeout=timeout_s, max_retries=1)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # gpt-oss models reason before answering; "low" keeps chat latency reasonable.
        self.reasoning_effort = reasoning_effort if "gpt-oss" in model else None

    def _kwargs(self, messages: list[ChatMessage], temperature, max_tokens) -> dict:
        kwargs = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if self.reasoning_effort:
            kwargs["reasoning_effort"] = self.reasoning_effort
        return kwargs

    def complete(self, messages, *, temperature=None, max_tokens=None) -> str:
        try:
            resp = self._client.chat.completions.create(
                **self._kwargs(messages, temperature, max_tokens)
            )
        except Exception as exc:
            raise LLMError(f"groq: {type(exc).__name__}: {exc}") from exc
        return resp.choices[0].message.content or ""

    def stream(self, messages, *, temperature=None, max_tokens=None) -> Iterator[str]:
        try:
            for chunk in self._client.chat.completions.create(
                **self._kwargs(messages, temperature, max_tokens), stream=True
            ):
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except Exception as exc:
            raise LLMError(f"groq: {type(exc).__name__}: {exc}") from exc
