from app.llm.interfaces import LLMProvider


class GeminiProvider(LLMProvider):
    """Implementación de LLMProvider usando la API de Gemini."""

    def __init__(self, api_key: str, model: str) -> None:
        try:
            from google.genai import Client
        except ImportError:
            raise ImportError(
                "El paquete 'google-genai' no está instalado. "
                "Ejecuta: pip install google-genai"
            )
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en el .env")
        self._client = Client(api_key=api_key)
        self._model = model

    @property
    def provider_name(self) -> str:
        return "gemini"

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents={
                "role": "user",
                "parts": [
                    {"text": system},
                    {"text": user},
                ],
            },
        )
        return response.text
