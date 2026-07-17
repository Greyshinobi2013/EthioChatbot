"""EthioChatbot V2 application entry point.

Milestone 1 establishes the project foundation only: configuration
loading, centralized logging, shared application state, and a service
registration framework that later milestones populate with the
camera, audio, Whisper, VAD, playback, and conversation services.

Per ARCHITECTURE.md's Startup Sequence, this module loads
configuration first, then initializes logging, then shared state,
then the service registry, then starts any registered services and
enters IDLE. The Event Bus and Finite State Machine are introduced in
Milestone 2 and are not wired in here.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from utils.logger import configure_logging, get_logger
from utils.state_manager import StateManager

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"

REQUIRED_CONFIG_KEYS = (
    "camera_index",
    "camera_width",
    "camera_height",
    "whisper_model",
    "recognition_interval",
    "face_confidence",
    "face_lost_timeout",
    "vad_aggressiveness",
    "conversation_timeout",
)


class ConfigurationError(Exception):
    """Raised when application configuration cannot be loaded or is invalid."""


@dataclass(frozen=True)
class AppConfig:
    """Typed view of config/settings.json.

    Attributes:
        camera_index: OpenCV device index for the webcam.
        camera_width: Capture frame width in pixels.
        camera_height: Capture frame height in pixels.
        whisper_model: Whisper model size to load (e.g. "base").
        recognition_interval: Run face recognition every Nth frame.
        face_confidence: Minimum confidence to accept a face match.
        face_lost_timeout: Seconds of absence before FACE_LOST fires.
        vad_aggressiveness: WebRTC VAD aggressiveness level (0-3).
        conversation_timeout: Seconds of inactivity before TIMEOUT fires.
    """

    camera_index: int
    camera_width: int
    camera_height: int
    whisper_model: str
    recognition_interval: int
    face_confidence: float
    face_lost_timeout: int
    vad_aggressiveness: int
    conversation_timeout: int

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        """Build an AppConfig from a validated settings dictionary."""
        return cls(**{key: data[key] for key in REQUIRED_CONFIG_KEYS})


def load_configuration(config_path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load and validate config/settings.json.

    Args:
        config_path: Path to the JSON settings file.

    Returns:
        A validated, typed AppConfig.

    Raises:
        ConfigurationError: if the file is missing, unreadable,
            malformed, or missing required keys.
    """
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            raw_config = json.load(config_file)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Configuration file is not valid JSON: {config_path}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Configuration file could not be read: {config_path}") from exc

    missing_keys = [key for key in REQUIRED_CONFIG_KEYS if key not in raw_config]
    if missing_keys:
        raise ConfigurationError(f"Configuration is missing required keys: {missing_keys}")

    try:
        return AppConfig.from_dict(raw_config)
    except (TypeError, KeyError) as exc:
        raise ConfigurationError(f"Configuration values are invalid: {exc}") from exc


@runtime_checkable
class Service(Protocol):
    """Interface every long-running robot service must implement.

    Later milestones (camera, audio, Whisper, VAD, playback,
    conversation) provide concrete implementations and register them
    with the ServiceRegistry so the application lifecycle can start
    and stop them uniformly.
    """

    name: str

    def start(self) -> None:
        """Begin the service's work, typically on a background thread."""
        ...

    def stop(self) -> None:
        """Stop the service and release any resources it holds."""
        ...


class ServiceRegistry:
    """Tracks registered services and coordinates their lifecycle."""

    def __init__(self, logger: logging.Logger) -> None:
        """Args:
            logger: Logger used to record registration and lifecycle events.
        """
        self._services: List[Service] = []
        self._logger = logger

    def register(self, service: Service) -> None:
        """Register a service to be started/stopped with the application."""
        self._services.append(service)
        self._logger.info("Service registered: %s", service.name)

    @property
    def services(self) -> List[Service]:
        """Registered services, in registration order."""
        return list(self._services)

    def start_all(self) -> None:
        """Start every registered service, in registration order.

        If a service fails to start, previously started services are
        stopped before the exception propagates, so the application
        never ends up in a half-started state.
        """
        started: List[Service] = []
        try:
            for service in self._services:
                self._logger.info("Starting service: %s", service.name)
                service.start()
                started.append(service)
        except Exception:
            self._logger.exception("Service failed to start, rolling back startup")
            for service in reversed(started):
                self._safe_stop(service)
            raise

    def stop_all(self) -> None:
        """Stop every registered service, in reverse registration order."""
        for service in reversed(self._services):
            self._safe_stop(service)

    def _safe_stop(self, service: Service) -> None:
        try:
            self._logger.info("Stopping service: %s", service.name)
            service.stop()
        except Exception:
            self._logger.exception("Error stopping service: %s", service.name)


class Application:
    """Coordinates configuration, logging, shared state, and service lifecycle."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        """Args:
            config_path: Path to config/settings.json.
        """
        self.config_path = config_path
        self.config: Optional[AppConfig] = None
        self.state: Optional[StateManager] = None
        self.registry: Optional[ServiceRegistry] = None
        self.logger: logging.Logger = get_logger(__name__)

    def startup(self) -> None:
        """Run the application startup lifecycle.

        Sequence: load configuration -> initialize logging ->
        initialize shared state -> initialize service registry ->
        start any registered services -> enter IDLE.

        Raises:
            ConfigurationError: if configuration cannot be loaded.
        """
        self.config = load_configuration(self.config_path)

        configure_logging()
        self.logger = get_logger(__name__)
        self.logger.info("SYSTEM_STARTUP: configuration loaded from %s", self.config_path)

        self.state = StateManager(initial_state="IDLE")
        self.logger.info("Shared state initialized: state=%s", self.state.current_state)

        self.registry = ServiceRegistry(self.logger)
        self.logger.info("Service registry initialized (Milestone 1: no services registered yet)")

        self.registry.start_all()

        self.logger.info("SYSTEM_STARTUP complete. Application entered IDLE state.")

    def shutdown(self) -> None:
        """Run the application shutdown lifecycle: stop services, log completion."""
        self.logger.info("SYSTEM_SHUTDOWN: beginning graceful shutdown")
        if self.registry is not None:
            self.registry.stop_all()
        self.logger.info("SYSTEM_SHUTDOWN complete.")


def main() -> int:
    """Application entry point.

    Registers SIGINT/SIGTERM handlers, runs startup, and guarantees
    shutdown runs even if an error occurs. Milestone 1 has no
    long-running services yet, so the process returns immediately
    after a successful startup/shutdown cycle; later milestones will
    block here while camera/audio/conversation services run.

    Returns:
        Process exit code: 0 on success, 1 on startup failure.
    """
    app = Application()

    def _handle_signal(signum: int, frame: Optional[types.FrameType]) -> None:
        app.logger.info("Received signal %s, initiating shutdown.", signum)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        app.startup()
    except ConfigurationError as exc:
        get_logger(__name__).error("Startup failed: %s", exc)
        return 1
    except Exception:
        get_logger(__name__).exception("Unexpected error during startup")
        return 1

    try:
        app.logger.info(
            "Application foundation ready (Milestone 1). "
            "No long-running services are registered yet."
        )
    finally:
        app.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
