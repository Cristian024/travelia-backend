from app.adapters.logging_azure import AzureLogStreamLoggingAdapter
from app.adapters.logging_local import LocalFileLoggingAdapter
from app.config import Settings
from app.ports.logging import LoggingAdapterPort

_AZURE_TARGETS = {"azure", "azure_log_stream", "logstream", "cloud", "prod"}


def build_logging_adapter(settings: Settings) -> LoggingAdapterPort:
    """Selecciona el adaptador de logging según LOG_TARGET (local | azure)."""
    target = (settings.log_target or "local").strip().lower()
    if target in _AZURE_TARGETS:
        return AzureLogStreamLoggingAdapter(level=settings.log_level)
    return LocalFileLoggingAdapter(
        log_file=settings.log_file,
        level=settings.log_level,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )
