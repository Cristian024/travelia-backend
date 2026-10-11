from app.models.user import LLMOperationType
from app.config import Settings
from app.llm.client import LLMClient
from app.llm.factory import LLMProviderFactory
from app.models.user import SubscriptionType


class LLMRouter:
    """
    Selecciona el LLMClient adecuado según la suscripción del usuario.
    FREE  -> modelo económico (ej. gemini-1.5-flash / gpt-3.5-turbo).
    PREMIUM -> modelo de alto razonamiento (ej. claude-3.5-sonnet / gpt-4o).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def client_for(self, subscription_type: SubscriptionType, operation_type: LLMOperationType) -> LLMClient:
        provider = LLMProviderFactory.create_for_subscription(
            subscription_type, self._settings, operation_type
        )
        return LLMClient(provider)

    def provider_name_for(self, subscription_type: SubscriptionType, operation_type: LLMOperationType) -> str:
        return LLMProviderFactory.create_for_subscription(
            subscription_type, self._settings, operation_type
        ).provider_name
