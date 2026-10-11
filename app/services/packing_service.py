from app.models.user import LLMOperationType
from app.core.exceptions import ForbiddenError, NotFoundError
from app.llm.router import LLMRouter
from app.models.packing import PackingList
from app.models.weather import WeatherForecast
from app.ports.external import WeatherProviderPort
from app.ports.repositories import (
    ItineraryRepositoryPort,
    PackingListRepositoryPort,
    UserRepositoryPort,
)


class PackingListService:
    """Genera y persiste el checklist de equipaje con IA a partir del itinerario
    (destino, fechas/clima y propósito del viaje)."""

    def __init__(
        self,
        itinerary_repo: ItineraryRepositoryPort,
        user_repo: UserRepositoryPort,
        packing_repo: PackingListRepositoryPort,
        llm_router: LLMRouter,
        weather: WeatherProviderPort | None = None,
    ) -> None:
        self._repo = itinerary_repo
        self._user_repo = user_repo
        self._packing_repo = packing_repo
        self._llm_router = llm_router
        self._weather = weather

    async def get(self, user_id: str, itinerary_id: str) -> PackingList:
        """Devuelve el checklist ya guardado (sin volver a llamar al LLM)."""
        await self._get_owned_itinerary(user_id, itinerary_id)
        stored = await self._packing_repo.find_by_itinerary(itinerary_id)
        if not stored:
            raise NotFoundError("Packing list")
        return stored

    async def generate(
        self, user_id: str, itinerary_id: str, regenerate: bool = False
    ) -> PackingList:
        """Genera el checklist con IA y lo guarda.

        Si ya existe uno guardado y `regenerate=False`, devuelve el guardado
        sin gastar una llamada al LLM.
        """
        user = await self._user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User")

        itinerary = await self._get_owned_itinerary(user_id, itinerary_id)

        if not regenerate:
            existing = await self._packing_repo.find_by_itinerary(itinerary_id)
            if existing:
                return existing

        weather_summary = await self._weather_summary(itinerary)
        llm = self._llm_router.client_for(user.subscription_type, LLMOperationType.itinerary)
        packing_list = llm.generate_packing_list(
            itinerary,
            weather_summary=weather_summary,
            is_premium=user.is_premium,
        )

        list_id = await self._packing_repo.upsert(packing_list)
        packing_list.id = list_id
        return packing_list

    async def set_item_checked(
        self, user_id: str, itinerary_id: str, position: int, checked: bool
    ) -> PackingList:
        """Marca/desmarca un item del checklist y devuelve la lista actualizada."""
        await self._get_owned_itinerary(user_id, itinerary_id)

        updated = await self._packing_repo.set_item_checked(itinerary_id, position, checked)
        if not updated:
            raise NotFoundError("Packing item")

        stored = await self._packing_repo.find_by_itinerary(itinerary_id)
        if not stored:
            raise NotFoundError("Packing list")
        return stored

    async def _get_owned_itinerary(self, user_id: str, itinerary_id: str):
        itinerary = await self._repo.find_by_id(itinerary_id)
        if not itinerary:
            raise NotFoundError("Itinerary")
        if itinerary.user_id != user_id:
            raise ForbiddenError()
        return itinerary

    async def _weather_summary(self, itinerary) -> str:
        if not self._weather or not itinerary.destinations:
            return ""
        first = itinerary.destinations[0]
        try:
            forecast: WeatherForecast | None = await self._weather.get_forecast(
                first.city, first.country, itinerary.arrival_date, itinerary.departure_date
            )
        except Exception:
            return ""
        if not forecast:
            return ""
        lines = [f"{forecast.city}, {forecast.country}: {forecast.summary}".strip()]
        for day in forecast.days:
            lines.append(
                f"  {day.date}: {day.description}, {day.temp_min:.0f}°-{day.temp_max:.0f}°C"
            )
        return "\n".join(lines)
