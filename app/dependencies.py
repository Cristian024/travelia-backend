from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.core.database import get_database
from app.core.security import decode_token
from app.llm.client import LLMClient
from app.llm.factory import LLMProviderFactory
from app.llm.interfaces import LLMProvider
from app.repositories.itinerary_repository import ItineraryRepository
from app.repositories.planning_repository import PlanningRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.itinerary_service import ItineraryService
from app.services.planning_service import PlanningService
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


# --- Service factories ---

def get_auth_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> AuthService:
    return AuthService(repo)

def get_user_service(repo: Annotated[UserRepository, Depends(get_user_repo)]) -> UserService:
    return UserService(repo)

def get_planning_service(
    repo: Annotated[PlanningRepository, Depends(get_planning_repo)],
    llm: Annotated[LLMClient, Depends(get_llm_client("groq"))],
) -> PlanningService:
    return PlanningService(repo, llm)

def get_itinerary_service(
    i_repo: Annotated[ItineraryRepository, Depends(get_itinerary_repo)],
    p_repo: Annotated[PlanningRepository, Depends(get_planning_repo)],
    llm: Annotated[LLMClient, Depends(get_llm_client("gemini"))],
) -> ItineraryService:
    return ItineraryService(i_repo, p_repo, llm)

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
