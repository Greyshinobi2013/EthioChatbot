"""Configuration loading and shared application state.

Milestone 1 scope: this module loads config/settings.json and exposes a
thread-safe container for runtime status fields that the Streamlit
dashboard (and later milestones' services) read and update. The full
finite-state-machine transition table from STATE_MACHINE.md is a
Milestone 6 deliverable; `current_state` here is a plain, logged field
rather than a validated FSM.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("state_manager")

DEFAULT_CONFIG_PATH = Path("config/settings.json")

REQUIRED_CONFIG_KEYS = (
    "whisper_model",
    "face_confidence",
    "vad_aggressiveness",
    "conversation_timeout",
    "wake_words",
)

# Keys required by later milestones (Settings page, camera service) that
# may be absent from an older settings.json. Backfilled, not invented.
CONFIG_DEFAULTS: dict[str, Any] = {
    "camera_index": 0,
    "gpu_acceleration": False,
}


class ConfigurationError(RuntimeError):
    """Raised when config/settings.json is missing, malformed, or incomplete."""


def load_configuration(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load, validate, and return application settings.

    Missing optional keys (CONFIG_DEFAULTS) are backfilled in memory and
    persisted back to disk so the settings file stays complete for later
    milestones. Missing required keys (REQUIRED_CONFIG_KEYS) raise
    ConfigurationError rather than silently defaulting, since those values
    directly affect recognition/VAD/timeout behaviour.
    """
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")

    try:
        config: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Configuration file is not valid JSON: {path}") from exc

    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        raise ConfigurationError(f"Configuration is missing required keys: {missing}")

    backfilled = False
    for key, default_value in CONFIG_DEFAULTS.items():
        if key not in config:
            config[key] = default_value
            backfilled = True
            logger.warning("Configuration key '%s' missing; defaulting to %r", key, default_value)

    if backfilled:
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Configuration file backfilled with default keys: %s", path.resolve())

    logger.info("Configuration loaded from %s", path.resolve())
    return config


@dataclass
class AppState:
    """Thread-safe shared runtime state, read by the Streamlit dashboard."""

    config: dict[str, Any]
    system_status: str = "STARTING"
    current_state: str = "IDLE"
    current_language: str | None = None
    recognized_user: str | None = None
    camera_status: str = "NOT_STARTED"
    microphone_status: str = "NOT_STARTED"
    wake_word_status: str = "NOT_STARTED"
    vad_status: str = "NOT_STARTED"
    playback_status: str = "IDLE"
    conversation_status: str = "IDLE"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    services: dict[str, threading.Thread] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def set_state(self, new_state: str) -> None:
        """Update the current high-level state and log the transition."""
        with self._lock:
            previous = self.current_state
            self.current_state = new_state
        logger.info("State transition: %s -> %s", previous, new_state)

    def set_status(self, field_name: str, value: str) -> None:
        """Update a single status field (camera_status, vad_status, ...) and log it."""
        with self._lock:
            if not hasattr(self, field_name):
                raise AttributeError(f"AppState has no field '{field_name}'")
            setattr(self, field_name, value)
        logger.info("Status update: %s -> %s", field_name, value)

    def snapshot(self) -> dict[str, Any]:
        """Return a plain-dict copy of the current state for dashboard rendering."""
        with self._lock:
            return {
                "system_status": self.system_status,
                "current_state": self.current_state,
                "current_language": self.current_language,
                "recognized_user": self.recognized_user,
                "camera_status": self.camera_status,
                "microphone_status": self.microphone_status,
                "wake_word_status": self.wake_word_status,
                "vad_status": self.vad_status,
                "playback_status": self.playback_status,
                "conversation_status": self.conversation_status,
                "started_at": self.started_at,
                "registered_services": list(self.services.keys()),
            }
