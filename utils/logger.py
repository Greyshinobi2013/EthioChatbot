"""Central logging configuration for the offline conversational robot.

All modules obtain loggers via get_logger() so every log line shares one
format and one pair of handlers (console + rotating file), regardless of
which service or Streamlit page emits it.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"
ROOT_LOGGER_NAME = "robot"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configured = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root application logger with console and file handlers.

    Idempotent: Streamlit reruns the whole script on every interaction, so
    this must be safe to call repeatedly without attaching duplicate
    handlers (which would duplicate every log line).
    """
    global _configured
    root = logging.getLogger(ROOT_LOGGER_NAME)

    if _configured:
        return root

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root.setLevel(level)
    root.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True
    root.info("Logging initialized. Log file: %s", LOG_FILE.resolve())
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger that feeds into the root application logger."""
    setup_logging()
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def read_recent_logs(n: int = 200) -> list[str]:
    """Return the last n lines of the application log file, for the Dashboard page."""
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return [line.rstrip("\n") for line in lines[-n:]]
