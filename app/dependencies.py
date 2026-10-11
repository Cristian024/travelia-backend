from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.database import get_database
from app.core.exceptions import ForbiddenError
from app.core.security import decode_token
from app.models.user import UserDocument
from app.adapters.pdf_exporter import PdfKitItineraryExporter
from app.adapters.weather_openweather import OpenWeatherMapProvider
from app.adapters.wompi_api import WompiApiClient
from app.llm.client import LLMClient
from app.llm.factory import LLMProviderFactory
from app.llm.interfaces import LLMProvider
from app.llm.router import LLMRouter
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.packing_repository import PackingListRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.expense_service import ExpenseService
from app.services.itinerary_service import ItineraryService
from app.services.packing_service import PackingListService
from app.services.payment_service import PaymentService, WompiParams
from app.services.plan_service import PlanService
from app.services.planning_service import PlanningService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService

_bearer = HTTPBearer()
_settings = get_settings()

# --- Repository factories ---

def get_user_repo() -> UserRepository:
    return UserRepository(get_database())

def get_planning_repo() -> PlanningRepository:
    return PlanningRepository(get_database())

def get_itinerary_repo() -> ItineraryRepository:
    return ItineraryRepository(get_database())

def get_expense_repo() -> ExpenseRepository:
    return ExpenseRepository(get_database())

def get_packing_repo() -> PackingListRepository:
    return PackingListRepository(get_database())

def get_payment_repo() -> PaymentRepository:
    return PaymentRepository(get_database())

def get_plan_repo() -> PlanRepository:
    return PlanRepository(get_database())

# --- LLM provider & client ---

def get_llm_provider(provider_name: str | None = None):
    """
    Closure que retorna una dependencia FastAPI para el proveedor indicado.

    Sin argumento → usa LLM_PROVIDER del .env (comportamiento por defecto).
    Con argumento → fuerza ese proveedor sin importar la config.

    Uso:
        Depends(get_llm_provider())             # desde .env
        Depends(get_llm_provider("openai"))     # fuerza OpenAI
        Depends(get_llm_provider("anthropic"))  # fuerza Anthropic
        Depends(get_llm_provider("groq"))       # fuerza Groq
        Depends(get_llm_provider("gemini"))     # fuerza Gemini
    """
    def _dependency() -> LLMProvider:
        name = (provider_name or _settings.llm_provider).lower()

        if name == "anthropic":
            kwargs = {"api_key": _settings.anthropic_api_key, "model": _settings.anthropic_model}
        elif name == "openai":
            kwargs = {"api_key": _settings.openai_api_key, "model": _settings.openai_model}
        elif name == "groq":
            kwargs = {"api_key": _settings.groq_api_key, "model": _settings.groq_model}
        elif name == "gemini":
            kwargs = {"api_key": _settings.gemini_api_key, "model": _settings.gemini_model}
        else:
            kwargs = {}

        return LLMProviderFactory.create(name, **kwargs)

    return _dependency


def get_llm_client(provider_name: str | None = None):
    """
    Closure que retorna una dependencia FastAPI para LLMClient.

    Acepta el mismo argumento que get_llm_provider().

    Uso:
        Depends(get_llm_client())            # proveedor desde .env
        Depends(get_llm_client("openai"))    # fuerza OpenAI
    """
    def _dependency(
        provider: Annotated[LLMProvider, Depends(get_llm_provider(provider_name))],
    ) -> LLMClient:
        return LLMClient(provider)

    return _dependency


def get_llm_router() -> LLMRouter:
    """Router que elige el modelo LLM según la suscripción del usuario."""
    return LLMRouter(_settings)


# --- External adapters ---

def get_weather_provider() -> OpenWeatherMapProvider:
    return OpenWeatherMapProvider(
        api_key=_settings.openweather_api_key,
        base_url=_settings.openweather_base_url,
    )


def get_itinerary_exporter() -> PdfKitItineraryExporter:
    return PdfKitItineraryExporter(wkhtmltopdf_path=_settings.wkhtmltopdf_path or None)


# --- Service factories ---

def get_auth_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> AuthService:
    return AuthService(repo, _settings.admin_emails)

def get_plan_service(
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
) -> PlanService:
    return PlanService(plan_repo)

def get_user_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> UserService:
    return UserService(repo)

def get_planning_service(
    repo: Annotated[PlanningRepository, Depends(get_planning_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    llm_router: Annotated[LLMRouter, Depends(get_llm_router)],
) -> PlanningService:
    return PlanningService(repo, user_repo, llm_router)

def get_itinerary_service(
    i_repo: Annotated[ItineraryRepository, Depends(get_itinerary_repo)],
    p_repo: Annotated[PlanningRepository, Depends(get_planning_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    llm_router: Annotated[LLMRouter, Depends(get_llm_router)],
    weather: Annotated[OpenWeatherMapProvider, Depends(get_weather_provider)],
    exporter: Annotated[PdfKitItineraryExporter, Depends(get_itinerary_exporter)],
) -> ItineraryService:
    return ItineraryService(i_repo, p_repo, user_repo, llm_router, weather, exporter)

def get_expense_service(
    expense_repo: Annotated[ExpenseRepository, Depends(get_expense_repo)],
    itinerary_repo: Annotated[ItineraryRepository, Depends(get_itinerary_repo)],
) -> ExpenseService:
    return ExpenseService(expense_repo, itinerary_repo)

def get_packing_service(
    itinerary_repo: Annotated[ItineraryRepository, Depends(get_itinerary_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    packing_repo: Annotated[PackingListRepository, Depends(get_packing_repo)],
    llm_router: Annotated[LLMRouter, Depends(get_llm_router)],
    weather: Annotated[OpenWeatherMapProvider, Depends(get_weather_provider)],
) -> PackingListService:
    return PackingListService(itinerary_repo, user_repo, packing_repo, llm_router, weather)

def get_subscription_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    planning_repo: Annotated[PlanningRepository, Depends(get_planning_repo)],
) -> SubscriptionService:
    return SubscriptionService(user_repo, planning_repo)

def get_payment_gateway() -> WompiApiClient:
    return WompiApiClient(
        private_key=_settings.wompi_private_key,
        base_url=_settings.wompi_api_base_url,
    )

def get_wompi_params() -> WompiParams:
    return WompiParams(
        events_secret=_settings.wompi_events_secret,
        integrity_secret=_settings.wompi_integrity_secret,
        public_key=_settings.wompi_pub_test_key,
        redirect_url=_settings.wompi_redirect_url,
    )

def get_payment_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    payment_repo: Annotated[PaymentRepository, Depends(get_payment_repo)],
    plan_repo: Annotated[PlanRepository, Depends(get_plan_repo)],
    gateway: Annotated[WompiApiClient, Depends(get_payment_gateway)],
    params: Annotated[WompiParams, Depends(get_wompi_params)],
) -> PaymentService:
    """Servicio de pagos (checkout, transacción server-side y webhook)."""
    return PaymentService(user_repo, payment_repo, plan_repo, gateway, params)

# --- Auth dependency ---

async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> str:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await user_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return user_id

CurrentUser = Annotated[str, Depends(get_current_user_id)]


async def get_current_user(
    user_id: CurrentUser,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserDocument:
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


async def require_admin(
    user: Annotated[UserDocument, Depends(get_current_user)],
) -> UserDocument:
    if not user.is_admin:
        raise ForbiddenError("Admin privileges required")
    return user


CurrentAdmin = Annotated[UserDocument, Depends(require_admin)]
