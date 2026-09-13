from app.llm.interfaces import LLMProvider


class LLMProviderFactory:
    """
    Crea el proveedor de LLM correcto según el nombre indicado.
    Agregar un nuevo proveedor solo requiere registrarlo aquí
    sin tocar ninguna otra clase (Open/Closed Principle).
    """

    _registry: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> LLMProvider:
        provider_class = cls._registry.get(provider_name)
        if not provider_class:
            available = ", ".join(cls._registry.keys()) or "ninguno registrado"
            raise ValueError(
                f"Proveedor LLM desconocido: '{provider_name}'. "
                f"Disponibles: {available}"
            )
        return provider_class(**kwargs)


def _register_defaults() -> None:
    from app.llm.providers.anthropic import AnthropicProvider
    from app.llm.providers.openai import OpenAIProvider
    from app.llm.providers.groq import GroqProvider
    from app.llm.providers.gemini import GeminiProvider

    LLMProviderFactory.register("anthropic", AnthropicProvider)
    LLMProviderFactory.register("openai", OpenAIProvider)
    LLMProviderFactory.register("groq", GroqProvider)
    LLMProviderFactory.register("gemini", GeminiProvider)


_register_defaults()
