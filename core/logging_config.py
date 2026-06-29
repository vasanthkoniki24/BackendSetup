# core/logging_config.py
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    - Development : INFO to stdout with full format
    - Production  : WARNING+ to stdout, INFO+ to rotating file
    Both modes suppress noisy third-party loggers.
    """

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # ─── Formatters ──────────────────────────────────────────────────────────
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ─── Handlers ────────────────────────────────────────────────────────────
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(detailed_formatter)

    handlers: list[logging.Handler] = [stdout_handler]

    # Rotating file handler — only in non-debug / production
    if not settings.DEBUG:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,   # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        handlers.append(file_handler)

    # ─── Root Logger ─────────────────────────────────────────────────────────
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,   # override any existing config (important for uvicorn reload)
    )

    # ─── Suppress Noisy Third-party Loggers ──────────────────────────────────
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("passlib").setLevel(logging.WARNING)
    logging.getLogger("jose").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        f"Logging configured | env={settings.ENVIRONMENT} | debug={settings.DEBUG}"
    )