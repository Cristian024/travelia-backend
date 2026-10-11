"""
Puertos para servicios externos (adaptadores de salida).

Los casos de uso dependen de estas abstracciones; las implementaciones
concretas (OpenWeatherMap, Jinja2/pdfkit) viven en `app/adapters`.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.models.itinerary import ItineraryDocument
from app.models.weather import WeatherForecast


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
