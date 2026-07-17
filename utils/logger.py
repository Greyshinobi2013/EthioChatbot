"""Centralized logging configuration for EthioChatbot V2.

All services and the application entry point obtain loggers through
this module so that startup, shutdown, state transitions, and errors
are recorded consistently to both the console and a rotating log file.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE_NAME = "ethiochatbot.log"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

_configured = False


def configure_logging(log_dir: Path | str = DEFAULT_LOG_DIR, level: int = logging.INFO) -> None:
    """Configure the root logger with console and rotating file handlers.

    Idempotent: calling this more than once will not attach duplicate
    handlers, so every module can safely call it before logging.

    Args:
        log_dir: Directory where the log file is written. Created if
            it does not already exist.
        level: Minimum severity level captured by the root logger.

    Raises:
        OSError: if the log directory cannot be created.
    """
    global _configured
    if _configured:
        return

    log_path = Path(log_dir)
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Could not create log directory: {log_path}") from exc

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_path / _LOG_FILE_NAME,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger.

    Args:
        name: Typically the caller's ``__name__``.

    Returns:
        A standard library logger. If ``configure_logging`` has not
        been called yet, log records are handled by logging's default
        last-resort handler until it is.
    """
    return logging.getLogger(name)
