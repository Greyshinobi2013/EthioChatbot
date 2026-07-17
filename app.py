"""EthioChatbot V2 application entry point.

Milestone 1 established configuration loading, centralized logging,
shared application state, and a service registration framework.
Milestone 2 adds the Event Bus and Finite State Machine backbone.
Milestones 3-10 built the individual services (face enrollment,
camera/recognition, greeting, Whisper, scenario matching, playback,
VAD/interruption, conversation orchestration). Milestone 11 adds the
Streamlit administration/monitoring pages, which need one running
instance of the full system shared across every page and every
Streamlit rerun -- start_full_system()/get_running_application()
below provide that, without changing the plain `python app.py` CLI
path's foundation-only behavior (main() still only calls startup()).

Per ARCHITECTURE.md's Startup Sequence, this module loads
configuration, initializes logging, initializes the event bus,
initializes shared state, initializes the FSM, initializes the
service registry, starts any registered services, and enters IDLE.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import types
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

import streamlit as st

from utils.camera_service import CameraService
from utils.conversation_manager import ConversationManager
from utils.event_bus import EventBus
from utils.face_recognition import FaceRecognizer
from utils.fsm import FiniteStateMachine
from utils.greeting_service import GreetingService
from utils.logger import configure_logging, get_logger
from utils.playback import PlaybackService
from utils.scenario_engine import ScenarioEngine
from utils.state_manager import StateManager
from utils.vad_handler import VADHandler
from utils.whisper_utils import WhisperService

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


def save_configuration(config: AppConfig, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Persist an AppConfig back to config/settings.json.

    Used by pages/4_Settings.py. Changes take effect the next time the
    application starts -- the running engine's services were already
    constructed from whatever configuration was in effect at startup.

    Args:
        config: The configuration to save.
        config_path: Path to write to.

    Raises:
        ConfigurationError: if the file cannot be written.
    """
    try:
        with config_path.open("w", encoding="utf-8") as config_file:
            json.dump(asdict(config), config_file, indent=2)
    except OSError as exc:
        raise ConfigurationError(f"Could not write configuration file: {config_path}") from exc


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
        self.event_bus: Optional[EventBus] = None
        self.state: Optional[StateManager] = None
        self.fsm: Optional[FiniteStateMachine] = None
        self.registry: Optional[ServiceRegistry] = None
        self.logger: logging.Logger = get_logger(__name__)

        # Populated by start_full_system() only (not by startup()/main()'s
        # CLI path), for Streamlit pages to read from directly.
        self.recognizer: Optional[FaceRecognizer] = None
        self.camera: Optional[CameraService] = None
        self.greeting: Optional[GreetingService] = None
        self.whisper: Optional[WhisperService] = None
        self.scenario_engine: Optional[ScenarioEngine] = None
        self.playback: Optional[PlaybackService] = None
        self.vad: Optional[VADHandler] = None
        self.conversation: Optional[ConversationManager] = None

    def startup(self) -> None:
        """Run the application startup lifecycle.

        Sequence (per ARCHITECTURE.md's Startup Sequence): load
        configuration -> initialize logging -> initialize event bus ->
        initialize shared state -> initialize the FSM -> initialize
        service registry -> start any registered services -> enter
        IDLE.

        Raises:
            ConfigurationError: if configuration cannot be loaded.
        """
        self.config = load_configuration(self.config_path)

        configure_logging()
        self.logger = get_logger(__name__)
        self.logger.info("SYSTEM_STARTUP: configuration loaded from %s", self.config_path)

        self.event_bus = EventBus()
        self.logger.info("Event bus initialized")

        self.state = StateManager(initial_state="IDLE")
        self.logger.info("Shared state initialized: state=%s", self.state.current_state)

        self.fsm = FiniteStateMachine(self.event_bus, self.state)
        self.logger.info("Finite State Machine initialized")

        self.registry = ServiceRegistry(self.logger)
        self.logger.info("Service registry initialized (Milestone 1/2: no services registered yet)")

        self.registry.start_all()

        self.event_bus.publish("SYSTEM_STARTUP", {"config_path": str(self.config_path)})
        self.logger.info("SYSTEM_STARTUP complete. Application entered IDLE state.")

    def shutdown(self) -> None:
        """Run the application shutdown lifecycle: stop services, log completion."""
        self.logger.info("SYSTEM_SHUTDOWN: beginning graceful shutdown")
        if self.event_bus is not None:
            self.event_bus.publish("SYSTEM_SHUTDOWN")
        if self.registry is not None:
            self.registry.stop_all()
        self.logger.info("SYSTEM_SHUTDOWN complete.")

    def start_full_system(self) -> None:
        """Build, register, and start every robot service.

        Extends startup() (foundation only: config/logging/event
        bus/state/FSM/empty registry) with the full pipeline built
        across Milestones 3-10: face recognition, camera, greeting,
        Whisper, scenario matching, playback, VAD/interruption, and
        conversation orchestration. Used by the Streamlit dashboard's
        cached singleton (see get_running_application() below); the
        plain `python app.py` CLI entry point (main()) intentionally
        stays foundation-only, so it keeps working without camera or
        microphone hardware and without paying Whisper's load cost.
        """
        self.startup()
        assert self.event_bus is not None and self.state is not None and self.registry is not None
        assert self.config is not None

        self.recognizer = FaceRecognizer()
        self.camera = CameraService(
            self.event_bus,
            self.state,
            self.recognizer,
            camera_index=self.config.camera_index,
            camera_width=self.config.camera_width,
            camera_height=self.config.camera_height,
            recognition_interval=self.config.recognition_interval,
            face_lost_timeout=self.config.face_lost_timeout,
        )
        self.greeting = GreetingService(self.event_bus, self.state)
        self.whisper = WhisperService(self.event_bus, self.state, model_size=self.config.whisper_model)
        self.scenario_engine = ScenarioEngine(self.event_bus, self.state)
        self.playback = PlaybackService(self.event_bus)
        self.vad = VADHandler(
            self.event_bus, self.state, self.playback, aggressiveness=self.config.vad_aggressiveness
        )
        self.conversation = ConversationManager(
            self.event_bus, self.state, self.playback, timeout_seconds=self.config.conversation_timeout
        )

        for service in (
            self.camera,
            self.greeting,
            self.whisper,
            self.scenario_engine,
            self.playback,
            self.vad,
            self.conversation,
        ):
            self.registry.register(service)

        self.registry.start_all()
        self.logger.info("Full system started: all services registered and running")


@st.cache_resource(show_spinner="Starting EthioChatbot V2 engine...")
def get_running_application() -> Application:
    """Return the single, process-wide running Application instance.

    Cached via Streamlit's st.cache_resource, so it is created exactly
    once per server process and reused across every page and every
    Streamlit rerun. This is the singleton pattern decided for this
    project: Streamlit reruns the whole script on each interaction,
    but background services (camera thread, greeting thread, etc.)
    must not be restarted on every rerun -- every pages/*.py module
    that needs the live engine calls this instead of constructing its
    own Application.
    """
    app = Application()
    app.start_full_system()
    return app


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
            "Application foundation ready (Milestone 1/2). "
            "No long-running services are registered yet."
        )
    finally:
        app.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
