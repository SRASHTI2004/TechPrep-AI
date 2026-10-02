"""Primary → fallback LLM routing (Gemini first, Groq if Gemini fails or is rate-limited).

Streaming caveat: we can only fail over *before the first token*. Once text has been sent
to the user, switching providers would produce a stitched answer, so a mid-stream failure
is raised and the UI shows an error.
"""

from collections.abc import Iterator
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.rag.llm.base import ChatMessage, LLMError, LLMProvider

log = get_logger(__name__)


@lru_cache(maxsize=8)
def _build(name: str) -> LLMProvider | None:
    s: Settings = get_settings()
    if name == "fake":
        from app.rag.llm.fake import FakeProvider

        return FakeProvider()
    if name == "gemini" and s.gemini_api_key:
        from app.rag.llm.gemini import GeminiProvider

        return GeminiProvider(
            s.gemini_api_key,
            s.gemini_model,
            s.llm_temperature,
            s.llm_max_tokens,
            s.llm_timeout_seconds,
        )
    if name == "groq" and s.groq_api_key:
        from app.rag.llm.groq import GroqProvider

        return GroqProvider(
            s.groq_api_key,
            s.groq_model,
            s.llm_temperature,
            s.llm_max_tokens,
            s.llm_timeout_seconds,
            reasoning_effort=s.groq_reasoning_effort,
        )
    if name not in ("none", ""):
        log.warning("llm_provider_unavailable", provider=name, reason="missing API key")
    return None


class FallbackLLM:
    """Tries providers in order. `used` records which one actually answered."""

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise LLMError(
                "No LLM provider is configured. Set GEMINI_API_KEY and/or GROQ_API_KEY in .env."
            )
        self.providers = providers
        self.used: LLMProvider | None = None

    @property
    def name(self) -> str:
        return (self.used or self.providers[0]).name

    @property
    def model(self) -> str:
        return (self.used or self.providers[0]).model

    def complete(self, messages: list[ChatMessage], **kwargs) -> str:
        last_error: LLMError | None = None
        for provider in self.providers:
            try:
                result = provider.complete(messages, **kwargs)
                self.used = provider
                return result
            except LLMError as exc:
                log.warning("llm_failover", provider=provider.name, error=str(exc)[:300])
                last_error = exc
        raise last_error or LLMError("all providers failed")

    def stream(self, messages: list[ChatMessage], **kwargs) -> Iterator[str]:
        last_error: LLMError | None = None
        for provider in self.providers:
            started = False
            try:
                for token in provider.stream(messages, **kwargs):
                    if not started:
                        started = True
                        self.used = provider
                    yield token
                if started:
                    return
                # Provider produced nothing at all: treat as failure, try the next one.
                raise LLMError(f"{provider.name}: empty stream")
            except LLMError as exc:
                if started:
                    raise
                log.warning("llm_failover", provider=provider.name, error=str(exc)[:300])
                last_error = exc
        raise last_error or LLMError("all providers failed")


def get_llm() -> FallbackLLM:
    """A fresh router per request (cheap: the provider clients are cached)."""
    s = get_settings()
    names = [s.llm_primary] + ([s.llm_fallback] if s.llm_fallback != s.llm_primary else [])
    return FallbackLLM([p for p in (_build(n) for n in names) if p is not None])


def get_judge_llm() -> FallbackLLM:
    """LLM used by the offline evaluation to grade answers (a bigger model than the answerer)."""
    s = get_settings()
    if s.eval_judge_provider == "fake":
        return FallbackLLM([_build("fake")])
    if s.eval_judge_provider == "groq" and s.groq_api_key:
        from app.rag.llm.groq import GroqProvider

        return FallbackLLM(
            [
                GroqProvider(
                    s.groq_api_key,
                    s.eval_judge_model,
                    0.0,
                    2048,  # room for the reasoning tokens of gpt-oss judges
                    s.llm_timeout_seconds,
                    reasoning_effort="low",
                )
            ]
        )
    if s.eval_judge_provider == "gemini" and s.gemini_api_key:
        from app.rag.llm.gemini import GeminiProvider

        return FallbackLLM(
            [GeminiProvider(s.gemini_api_key, s.eval_judge_model, 0.0, 1024, s.llm_timeout_seconds)]
        )
    raise LLMError(f"Judge provider '{s.eval_judge_provider}' has no API key configured")
