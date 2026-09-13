from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    Contrato mínimo que todo proveedor de LLM debe cumplir.
    Solo expone la capacidad de completar texto; la lógica de parseo,
    prompts y dominio queda exclusivamente en LLMClient.
    """

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 2048) -> str:
        """
        Envía un mensaje al LLM y retorna el texto de la respuesta.

        Args:
            system: Instrucción de sistema (rol/personalidad del asistente).
            user:   Mensaje del usuario / prompt.
            max_tokens: Límite de tokens en la respuesta.

        Returns:
            Texto plano de la respuesta del LLM.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identificador legible del proveedor (ej: 'anthropic', 'openai')."""
