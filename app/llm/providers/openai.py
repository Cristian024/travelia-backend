from app.llm.interfaces import LLMProvider


class OpenAIProvider(LLMProvider):
    """Implementación de LLMProvider usando la API de OpenAI (GPT)."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "El paquete 'openai' no está instalado. "
                "Ejecuta: pip install openai"
            )
        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
