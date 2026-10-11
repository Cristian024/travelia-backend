from app.models.user import LLMOperationType
from app.config import Settings
from app.llm.interfaces import LLMProvider
from app.models.user import SubscriptionType


def _provider_kwargs(provider_name: str, settings: Settings, model: str) -> dict:
    if provider_name == "anthropic":
        return {"api_key": settings.anthropic_api_key, "model": model}
    if provider_name == "openai":
        return {"api_key": settings.openai_api_key, "model": model}
    if provider_name == "groq":
        return {"api_key": settings.groq_api_key, "model": model}
    if provider_name == "gemini":
        return {"api_key": settings.gemini_api_key, "model": model}
    return {}


class LLMProviderFactory:
    """
    Crea el proveedor de LLM correcto según el nombre indicado.
    Agregar un nuevo proveedor solo requiere registrarlo aquí
    sin tocar ninguna otra clase (Open/Closed Principle).
    """

    _registry: dict[str, type[LLMProvider]] = {}

    # Suscripción -> (atributo del proveedor, atributo del modelo) en Settings.
    # FREE se enruta a modelos económicos; PREMIUM a modelos de alto razonamiento.
    _SUBSCRIPTION_ROUTING: dict[str, dict[LLMOperationType, tuple[str, str]]] = {
        SubscriptionType.free.value: {
            LLMOperationType.questions: ("free_llm_provider_questions", "free_llm_model_questions"),
            LLMOperationType.itinerary: ("free_llm_provider_itinerary", "free_llm_model_itinerary"),
        },
        SubscriptionType.premium.value: {
            LLMOperationType.questions: ("premium_llm_provider_questions", "premium_llm_model_questions"),
            LLMOperationType.itinerary: ("premium_llm_provider_itinerary", "premium_llm_model_itinerary"),
        },
    }

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

    @classmethod
    def create_for_subscription(
        cls,
        subscription_type: SubscriptionType | str,
        settings: Settings,
        operation_type: LLMOperationType | str,
    ) -> LLMProvider:
        """Enruta al proveedor/modelo según el tipo de suscripción del usuario."""
        key = (
            subscription_type.value
            if isinstance(subscription_type, SubscriptionType)
            else str(subscription_type)
        ).upper()

        operation_key = (
            operation_type.value
            if isinstance(operation_type, LLMOperationType)
            else str(operation_type)
        ).lower()

        provider_attr, model_attr = cls._SUBSCRIPTION_ROUTING.get(
            key, cls._SUBSCRIPTION_ROUTING[SubscriptionType.free.value]
        ).get(
            operation_key, cls._SUBSCRIPTION_ROUTING[SubscriptionType.free.value][LLMOperationType.questions]
        )
        provider_name = getattr(settings, provider_attr).lower()
        model = getattr(settings, model_attr)
        return cls.create(provider_name, **_provider_kwargs(provider_name, settings, model))


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
