"""Configuration loading and shared application state.

Milestone 1 added config/settings.json loading and a thread-safe container
for runtime status fields. Milestone 6 adds the validated finite state
machine from STATE_MACHINE.md: set_state() now rejects (and logs) any
transition not in VALID_TRANSITIONS instead of accepting anything.
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


def save_configuration(config: dict[str, Any], path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Persist a settings dict back to config/settings.json.

    Used by the Settings page (whisper model, sensitivities, GPU flag) and
    the Scenario Management page (wake words live under the same file).
    Currently-running services read config once at their own startup, so
    changes here take effect on next app restart, not live -- callers must
    make that clear to the user rather than implying an immediate effect.
    """
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Configuration saved to %s", path.resolve())


# All states from STATE_MACHINE.md. FACE_ENROLLMENT exists as a state but
# has no defined transitions there (it's driven by the Enrollment page,
# not the automatic conversation flow) -- it's listed here so it's
# recognized as valid, but not as a source or target of any automatic
# transition below.
VALID_STATES = {
    "IDLE",
    "FACE_ENROLLMENT",
    "FACE_DETECTED",
    "FACE_RECOGNIZED",
    "GREETING",
    "WAITING_FOR_WAKE_WORD",
    "LANGUAGE_SELECTION",
    "CONVERSATION_ACTIVE",
    "PLAYING_AUDIO",
    "INTERRUPTED",
    "TIMEOUT",
    "RETURN_TO_IDLE",
}

# STATE_MACHINE.md's "State Transition Diagram", plus PLAYING_AUDIO ->
# CONVERSATION_ACTIVE from its "Conversation Workflow" prose (the formal
# diagram section omits it, but the workflow section requires it -- a
# conversation that never returns from a played response can't continue,
# so the prose is treated as authoritative for that one edge).
VALID_TRANSITIONS: dict[str, set[str]] = {
    "IDLE": {"FACE_DETECTED"},
    "FACE_DETECTED": {"FACE_RECOGNIZED"},
    "FACE_RECOGNIZED": {"GREETING"},
    "GREETING": {"WAITING_FOR_WAKE_WORD"},
    "WAITING_FOR_WAKE_WORD": {"LANGUAGE_SELECTION"},
    "LANGUAGE_SELECTION": {"CONVERSATION_ACTIVE"},
    "CONVERSATION_ACTIVE": {"PLAYING_AUDIO", "TIMEOUT"},
    "PLAYING_AUDIO": {"INTERRUPTED", "CONVERSATION_ACTIVE"},
    "INTERRUPTED": {"PLAYING_AUDIO"},
    "TIMEOUT": {"RETURN_TO_IDLE"},
    "RETURN_TO_IDLE": {"IDLE"},
    "FACE_ENROLLMENT": set(),
}


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
    stop_event: threading.Event = field(default_factory=threading.Event)
    latest_frame: Any = None
    latest_raw_frame: Any = None

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def set_state(self, new_state: str) -> bool:
        """Attempt a state transition; returns True if applied, False if rejected.

        A request to (re-)enter the state already current is always
        accepted as a no-op confirmation (not a "transition" to validate --
        e.g. app.py confirming IDLE at startup, or a duplicate event firing
        twice). Any other transition not listed in VALID_TRANSITIONS for
        the current state is rejected and logged as a warning rather than
        applied (STATE_MACHINE.md "Invalid transitions must be rejected").
        """
        if new_state not in VALID_STATES:
            logger.warning("Rejected transition to unknown state: %r", new_state)
            return False

        with self._lock:
            previous = self.current_state
            if new_state == previous:
                allowed = True
            else:
                allowed = new_state in VALID_TRANSITIONS.get(previous, set())
            if allowed:
                self.current_state = new_state

        if not allowed:
            logger.warning("Invalid state transition rejected: %s -> %s", previous, new_state)
            return False

        if new_state != previous:
            logger.info("State transition: %s -> %s", previous, new_state)
        return True

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
