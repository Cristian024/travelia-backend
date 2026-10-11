import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.ports.logging import LOG_DATE_FORMAT, LOG_FORMAT, LoggingAdapterPort


class LocalFileLoggingAdapter(LoggingAdapterPort):
    """Logging local: escribe en un archivo .log rotativo (y opcionalmente consola)."""

    def __init__(
        self,
        log_file: str,
        level: str = "INFO",
        max_bytes: int = 5_000_000,
        backup_count: int = 5,
        also_console: bool = True,
    ) -> None:
        self._log_file = log_file
        self._level = level.upper()
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._also_console = also_console

    def configure(self) -> None:
        root = logging.getLogger()
        root.setLevel(self._level)
        self._quiet_noisy_loggers()
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        if not self._has_file_handler(root):
            path = Path(self._log_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                path,
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

        if self._also_console and not self._has_console_handler(root):
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(formatter)
            root.addHandler(console)

    @staticmethod
    def _quiet_noisy_loggers() -> None:
        for name in ("httpx", "httpcore", "asyncpg", "urllib3"):
            logging.getLogger(name).setLevel("WARNING")

    @staticmethod
    def _has_file_handler(root: logging.Logger) -> bool:
        return any(isinstance(h, RotatingFileHandler) for h in root.handlers)

    @staticmethod
    def _has_console_handler(root: logging.Logger) -> bool:
        return any(type(h) is logging.StreamHandler for h in root.handlers)
