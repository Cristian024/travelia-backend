"""Puerto de logging (adaptador de salida).

Los adaptadores concretos configuran los handlers del sistema de logging
(archivo local o Log Stream de Azure). El resto de la app sigue usando el
módulo estándar `logging.getLogger(__name__)`; aquí solo se decide el destino.
"""
from abc import ABC, abstractmethod

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LoggingAdapterPort(ABC):
    @abstractmethod
    def configure(self) -> None:
        """Configura handlers, formato y nivel del logging. Idempotente."""
