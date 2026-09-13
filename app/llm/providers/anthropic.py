import anthropic
from app.llm.interfaces import LLMProvider


class AnthropicProvider(LLMProvider):
    """Implementación de LLMProvider usando la API de Anthropic (Claude)."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text
