from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta al .env (raíz del proyecto), independiente del CWD.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================
    # SECRETOS -> provistos por .env
    # =========================================================
    database_prod_url: str = ""
    database_dev_url: str = ""
    database_env: str = ""  # "prod" | "dev"
    jwt_secret_key: str = ""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openweather_api_key: str = ""

    # Wompi: secretos. NUNCA exponerlos.
    wompi_events_secret: str = ""      # firma/checksum de eventos (webhook)
    wompi_integrity_secret: str = ""   # firma de integridad (checkout/widget)
    wompi_private_key: str = ""        # autenticación server-side contra la API de Wompi

    # =========================================================
    # CONFIGURACIÓN NO SENSIBLE -> defaults en código
    # =========================================================
    # Aplicación
    app_name: str = "Travelia Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # Conexión a PostgreSQL
    db_min_size: int = 1
    db_max_size: int = 10

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Proveedor LLM por defecto (fallback): "anthropic" | "openai" | "groq" | "gemini"
    llm_provider: str = "groq"

    # Modelos de cada proveedor
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"
    groq_model: str = "openai/gpt-oss-safeguard-20b"
    gemini_model: str = "gemini-2.5-flash"

    # Enrutamiento dinámico de LLM por suscripción y operación
    free_llm_provider_questions: str = "groq"
    free_llm_model_questions: str = "qwen/qwen3.8-27b"
    free_llm_provider_itinerary: str = "gemini"
    free_llm_model_itinerary: str = "gemini-2.5-flash"
    
    premium_llm_provider_questions: str = "groq"
    premium_llm_model_questions: str = "openai/gpt-oss-safeguard-20b"
    premium_llm_provider_itinerary: str = "gemini"
    premium_llm_model_itinerary: str = "gemini-3.1-flash-lite"

    # APIs externas
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # Wompi (pasarela de pagos - Sandbox).
    wompi_pub_test_key: str = "pub_test_8LasskVBbaOZqb9XT3DfwZSszjwSQds3"
    wompi_environment: str = "sandbox"
    wompi_api_base_url: str = "https://sandbox.wompi.co/v1"
    wompi_currency: str = "COP"
    wompi_events_endpoint: str = "/api/v1/webhooks/wompi"

    # URL de retorno tras el pago (el PRECIO del plan vive en la tabla `plans`).
    wompi_redirect_url: str = "https://travelia.app/payment/result"

    # Bootstrap de administradores: estos correos se registran con rol ADMIN.
    # En producción, promover vía SQL: UPDATE users SET role='ADMIN' WHERE email='...';
    admin_emails: list[str] = []

    # Logging: LOG_TARGET="local" (archivo) | "azure" (Log Stream de App Service).
    log_target: str = ""
    log_level: str = "INFO"
    log_file: str = "logs/travelia.log"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5

    # Exportación a PDF: ruta al binario wkhtmltopdf.
    # Vacío => autodetección (PATH y ubicaciones típicas de Windows/Linux).
    wkhtmltopdf_path: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
