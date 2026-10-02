"""Google Gemini via the official `google-genai` SDK (free tier available)."""

from collections.abc import Iterator

from app.rag.llm.base import ChatMessage, LLMError, split_system


class GeminiProvider:
    name = "gemini"

    def __init__(
        self, api_key: str, model: str, temperature: float, max_tokens: int, timeout_s: float
    ):
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=int(timeout_s * 1000))
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _request(self, messages: list[ChatMessage], temperature, max_tokens):
        types = self._types
        system, rest = split_system(messages)
        contents = [
            types.Content(
                role="model" if m.role == "assistant" else "user",
                parts=[types.Part.from_text(text=m.content)],
            )
            for m in rest
        ]
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            temperature=self.temperature if temperature is None else temperature,
            max_output_tokens=max_tokens or self.max_tokens,
        )
        if "flash" in self.model:
            # Flash models "think" by default, which adds latency and eats the token budget.
            config.thinking_config = types.ThinkingConfig(thinking_budget=0)
        return contents, config

    def complete(self, messages, *, temperature=None, max_tokens=None) -> str:
        contents, config = self._request(messages, temperature, max_tokens)
        try:
            resp = self._client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except Exception as exc:
            raise LLMError(f"gemini: {type(exc).__name__}: {exc}") from exc
        if not resp.text:
            raise LLMError("gemini: empty response (possibly blocked by safety filters)")
        return resp.text

    def stream(self, messages, *, temperature=None, max_tokens=None) -> Iterator[str]:
        contents, config = self._request(messages, temperature, max_tokens)
        try:
            for chunk in self._client.models.generate_content_stream(
                model=self.model, contents=contents, config=config
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            raise LLMError(f"gemini: {type(exc).__name__}: {exc}") from exc
