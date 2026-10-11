import logging
from collections import Counter, OrderedDict
from typing import Optional

import httpx

from app.models.weather import DailyForecast, WeatherForecast
from app.ports.external import WeatherProviderPort

logger = logging.getLogger(__name__)


class OpenWeatherMapProvider(WeatherProviderPort):
    """Adaptador del puerto WeatherProviderPort sobre OpenWeatherMap (endpoint /forecast)."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def get_forecast(
        self,
        city: str,
        country: str,
        start_date: str,
        end_date: str,
    ) -> Optional[WeatherForecast]:
        if not self._api_key:
            logger.debug("OpenWeather: API key no configurada; se omite el pronóstico")
            return None

        params = {
            "q": f"{city},{country}" if country else city,
            "appid": self._api_key,
            "units": "metric",
            "lang": "es",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self._base_url}/forecast", params=params)
                if response.status_code != 200:
                    logger.warning(
                        "OpenWeather respondió %s para '%s,%s'", response.status_code, city, country
                    )
                    return None
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("OpenWeather: error de red para '%s,%s': %s", city, country, exc)
            return None

        forecast = self._parse(data, start_date, end_date)
        if forecast:
            logger.debug(
                "OpenWeather: pronóstico para %s (%s días)", forecast.city, len(forecast.days)
            )
        else:
            logger.debug("OpenWeather: sin datos para el rango %s..%s", start_date, end_date)
        return forecast

    @staticmethod
    def _parse(data: dict, start_date: str, end_date: str) -> Optional[WeatherForecast]:
        entries = data.get("list", [])
        if not entries:
            return None

        # Agrupa las predicciones (cada 3h) por fecha.
        buckets: "OrderedDict[str, list[dict]]" = OrderedDict()
        for entry in entries:
            day = entry.get("dt_txt", "").split(" ")[0]
            if not day:
                continue
            buckets.setdefault(day, []).append(entry)

        days: list[DailyForecast] = []
        for day, day_entries in buckets.items():
            if day < start_date or day > end_date:
                continue
            temps_min = [e["main"]["temp_min"] for e in day_entries if "main" in e]
            temps_max = [e["main"]["temp_max"] for e in day_entries if "main" in e]
            descriptions = [
                e["weather"][0]["description"]
                for e in day_entries
                if e.get("weather")
            ]
            days.append(
                DailyForecast(
                    date=day,
                    temp_min=min(temps_min) if temps_min else 0.0,
                    temp_max=max(temps_max) if temps_max else 0.0,
                    description=Counter(descriptions).most_common(1)[0][0] if descriptions else "",
                )
            )

        if not days:
            return None

        summary = Counter(d.description for d in days).most_common(1)[0][0]
        city_name = data.get("city", {}).get("name", "")
        country_name = data.get("city", {}).get("country", "")
        return WeatherForecast(
            city=city_name,
            country=country_name,
            days=days,
            summary=summary,
        )
