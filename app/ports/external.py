"""
Puertos para servicios externos (adaptadores de salida).

Los casos de uso dependen de estas abstracciones; las implementaciones
concretas (OpenWeatherMap, Jinja2/pdfkit) viven en `app/adapters`.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.models.itinerary import ItineraryDocument
from app.models.weather import WeatherForecast


@dataclass
class GatewayTransactionResult:
    """Respuesta normalizada de una pasarela al crear una transacción."""

    transaction_id: str
    status: str
    reference: str
    raw: dict[str, Any] = field(default_factory=dict)


class WeatherProviderPort(ABC):
    @abstractmethod
    async def get_forecast(
        self,
        city: str,
        country: str,
        start_date: str,
        end_date: str,
    ) -> Optional[WeatherForecast]:
        """Devuelve el pronóstico para el rango de fechas, o None si no hay datos."""


class ItineraryExporterPort(ABC):
    @abstractmethod
    async def to_pdf(self, itinerary: ItineraryDocument) -> bytes:
        """Convierte un itinerario en un documento PDF (bytes)."""


class PaymentGatewayPort(ABC):
    @abstractmethod
    async def create_transaction(
        self,
        *,
        amount_in_cents: int,
        currency: str,
        customer_email: str,
        reference: str,
        payment_method: dict[str, Any],
        redirect_url: Optional[str] = None,
    ) -> GatewayTransactionResult:
        """Crea una transacción server-side en la pasarela."""
