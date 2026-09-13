from app.llm.interfaces import LLMProvider


class GroqProvider(LLMProvider):
    """Implementación de LLMProvider usando la API de Groq."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from groq import Groq
        except ImportError:
            raise ImportError(
                "El paquete 'groq' no está instalado. "
                "Ejecuta: pip install groq"
            )
        self._client = Groq(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "groq"

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
