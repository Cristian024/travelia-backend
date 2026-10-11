import logging
import sys

from app.ports.logging import LOG_DATE_FORMAT, LOG_FORMAT, LoggingAdapterPort


class AzureLogStreamLoggingAdapter(LoggingAdapterPort):
    """Logging para Azure App Service.

    Escribe a stdout; Azure captura la salida y la muestra en el "Log Stream"
    del portal (Diagnostic logs / App Service logs). No requiere SDK.
    """

    def __init__(self, level: str = "INFO") -> None:
        self._level = level.upper()

    def configure(self) -> None:
        root = logging.getLogger()
        root.setLevel(self._level)

        for name in ("httpx", "httpcore", "asyncpg", "urllib3"):
            logging.getLogger(name).setLevel("WARNING")

        if self._has_stream_handler(root):
            return

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root.addHandler(handler)

    @staticmethod
    def _has_stream_handler(root: logging.Logger) -> bool:
        return any(type(h) is logging.StreamHandler for h in root.handlers)
