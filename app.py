"""EthioChatbot V3 application entry point.

Per SYSTEM_ARCHITECTURE_V3.md's Startup Sequence, this module loads
configuration, initializes logging, initializes the event bus,
initializes shared state, initializes the FSM, then builds and starts
the full face-recognition/greeting/playback pipeline: FaceRecognizer,
FacePresenceManager, CameraService, PlaybackService, and
GreetingManager.

Mirrors this project's established pattern of a foundation-only CLI
path (main() calls startup() only) plus a cached, fully-started
singleton for the Streamlit dashboard (get_running_application()),
since Streamlit reruns this whole script on every page interaction but
the camera thread and other background services must not restart each
time.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import types
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

import streamlit as st

from utils.camera_service import CameraService
from utils.event_bus import EventBus
from utils.face_presence_manager import FacePresenceManager
from utils.face_recognition import FaceRecognizer
from utils.fsm import FACE_DETECTION_MODE, FiniteStateMachine
from utils.greeting_manager import GreetingManager
from utils.head_motion_controller import HeadMotionController
from utils.logger import configure_logging, get_logger
from utils.playback import PlaybackService
from utils.state_manager import StateManager

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.json"
DEFAULT_INTERACTION_MODE_PATH = PROJECT_ROOT / "config" / "interaction_modes.json"

REQUIRED_CONFIG_KEYS = (
    "camera_index",
    "camera_width",
    "camera_height",
    "recognition_interval",
    "face_confidence",
    "face_lost_timeout",
    "yaw_servo_pin",
    "pitch_servo_pin",
)

INTERACTION_MODES = ("common_dialog", "user_specific_dialog")
DEFAULT_INTERACTION_MODE = "common_dialog"


class ConfigurationError(Exception):
    """Raised when application configuration cannot be loaded or is invalid."""


@dataclass(frozen=True)
class AppConfig:
    """Typed view of config/settings.json.

    Attributes:
        camera_index: OpenCV device index for the webcam.
        camera_width: Capture frame width in pixels.
        camera_height: Capture frame height in pixels.
        recognition_interval: Run full ArcFace recognition on
            already-tracked faces every Nth frame; new tracks are
            always recognized immediately.
        face_confidence: Minimum ArcFace cosine similarity accepted as
            a match (higher = stricter). Note: this key held the
            opposite semantics (a max dlib L2 distance) before V3.
        face_lost_timeout: Seconds of absence before FACE_LOST fires.
        yaw_servo_pin: GPIO pin the yaw (horizontal) neck servo is
            wired to.
        pitch_servo_pin: GPIO pin the pitch (vertical) neck servo is
            wired to.
    """

    camera_index: int
    camera_width: int
    camera_height: int
    recognition_interval: int
    face_confidence: float
    face_lost_timeout: int
    yaw_servo_pin: int
    pitch_servo_pin: int

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        """Build an AppConfig from a validated settings dictionary."""
        return cls(**{key: data[key] for key in REQUIRED_CONFIG_KEYS})


def load_configuration(config_path: Path = DEFAULT_SETTINGS_PATH) -> AppConfig:
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


def save_configuration(config: AppConfig, config_path: Path = DEFAULT_SETTINGS_PATH) -> None:
    """Persist an AppConfig back to config/settings.json.

    Used by pages/3_Settings.py. Changes take effect the next time the
    application starts.

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


def load_interaction_mode(config_path: Path = DEFAULT_INTERACTION_MODE_PATH) -> str:
    """Load the configured interaction mode from config/interaction_modes.json.

    Falls back to DEFAULT_INTERACTION_MODE if the file is missing,
    empty, malformed, or names an unrecognized mode -- per
    DEVELOPMENT_RULES_V3.md's rule that configuration problems must
    never crash the system.

    Args:
        config_path: Path to the JSON interaction-mode file.

    Returns:
        "common_dialog" or "user_specific_dialog".
    """
    if not config_path.exists():
        return DEFAULT_INTERACTION_MODE
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            raw_config = json.load(config_file)
    except (json.JSONDecodeError, OSError):
        return DEFAULT_INTERACTION_MODE

    mode = raw_config.get("interaction_mode", DEFAULT_INTERACTION_MODE)
    return mode if mode in INTERACTION_MODES else DEFAULT_INTERACTION_MODE


def save_interaction_mode(mode: str, config_path: Path = DEFAULT_INTERACTION_MODE_PATH) -> None:
    """Persist the interaction mode to config/interaction_modes.json.

    Args:
        mode: One of INTERACTION_MODES.
        config_path: Path to write to.

    Raises:
        ConfigurationError: if mode is unrecognized or the file cannot be written.
    """
    if mode not in INTERACTION_MODES:
        raise ConfigurationError(f"Unknown interaction mode: {mode}. Must be one of {INTERACTION_MODES}.")
    try:
        with config_path.open("w", encoding="utf-8") as config_file:
            json.dump({"interaction_mode": mode}, config_file, indent=2)
    except OSError as exc:
        raise ConfigurationError(f"Could not write interaction mode file: {config_path}") from exc


@runtime_checkable
class Service(Protocol):
    """Interface every long-running service must implement."""

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

    def __init__(self, config_path: Path = DEFAULT_SETTINGS_PATH) -> None:
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
        self.presence: Optional[FacePresenceManager] = None
        self.camera: Optional[CameraService] = None
        self.playback: Optional[PlaybackService] = None
        self.greeting: Optional[GreetingManager] = None
        self.head_motion: Optional[HeadMotionController] = None

    def startup(self) -> None:
        """Run the application startup lifecycle.

        Sequence (per SYSTEM_ARCHITECTURE_V3.md's Startup Sequence):
        load configuration -> initialize logging -> initialize event
        bus -> initialize shared state -> initialize the FSM ->
        initialize service registry -> start any registered services.

        Raises:
            ConfigurationError: if configuration cannot be loaded.
        """
        self.config = load_configuration(self.config_path)

        configure_logging()
        self.logger = get_logger(__name__)
        self.logger.info("SYSTEM_STARTUP: configuration loaded from %s", self.config_path)

        self.event_bus = EventBus()
        self.logger.info("Event bus initialized")

        self.state = StateManager(initial_state=FACE_DETECTION_MODE)
        self.state.set_interaction_mode(load_interaction_mode())
        self.logger.info(
            "Shared state initialized: state=%s interaction_mode=%s",
            self.state.current_state,
            self.state.get_interaction_mode(),
        )

        self.fsm = FiniteStateMachine(self.event_bus, self.state)
        self.logger.info("Finite State Machine initialized")

        self.registry = ServiceRegistry(self.logger)
        self.registry.start_all()

        self.event_bus.publish("SYSTEM_STARTUP", {"config_path": str(self.config_path)})
        self.logger.info("SYSTEM_STARTUP complete. Application entered %s.", self.state.current_state)

    def shutdown(self) -> None:
        """Run the application shutdown lifecycle: stop services, log completion."""
        self.logger.info("SYSTEM_SHUTDOWN: beginning graceful shutdown")
        if self.event_bus is not None:
            self.event_bus.publish("SYSTEM_SHUTDOWN")
        if self.registry is not None:
            self.registry.stop_all()
        self.logger.info("SYSTEM_SHUTDOWN complete.")

    def start_full_system(self) -> None:
        """Build, register, and start the full V3 face/greeting/playback pipeline.

        Extends startup() (foundation only: config/logging/event
        bus/state/FSM/empty registry) with FaceRecognizer,
        FacePresenceManager, CameraService, PlaybackService,
        HeadMotionController, and GreetingManager. Used by the
        Streamlit dashboard's cached singleton (see
        get_running_application() below); the plain `python app.py`
        CLI entry point (main()) intentionally stays foundation-only,
        so it keeps working without camera or servo hardware.
        """
        self.startup()
        assert self.event_bus is not None and self.state is not None and self.registry is not None
        assert self.config is not None

        self.recognizer = FaceRecognizer(similarity_threshold=self.config.face_confidence)
        self.presence = FacePresenceManager(
            self.event_bus, self.state, face_lost_timeout=self.config.face_lost_timeout
        )
        self.playback = PlaybackService(self.event_bus, self.state)
        self.head_motion = HeadMotionController(
            self.event_bus,
            self.state,
            yaw_pin=self.config.yaw_servo_pin,
            pitch_pin=self.config.pitch_servo_pin,
        )
        self.greeting = GreetingManager(self.event_bus, self.state, self.playback, self.head_motion)
        self.camera = CameraService(
            self.event_bus,
            self.state,
            self.recognizer,
            self.presence,
            camera_index=self.config.camera_index,
            camera_width=self.config.camera_width,
            camera_height=self.config.camera_height,
            recognition_interval=self.config.recognition_interval,
            head_motion=self.head_motion,
        )

        for service in (self.playback, self.head_motion, self.camera):
            self.registry.register(service)

        self.registry.start_all()
        self.logger.info("Full system started: all services registered and running")


@st.cache_resource(show_spinner="Starting EthioChatbot V3 engine...")
def get_running_application() -> Application:
    """Return the single, process-wide running Application instance.

    Cached via Streamlit's st.cache_resource, so it is created exactly
    once per server process and reused across every page and every
    Streamlit rerun -- background services (camera thread, playback
    watcher, etc.) must not be restarted on every rerun.
    """
    app = Application()
    app.start_full_system()
    return app


def main() -> int:
    """Application entry point.

    Registers SIGINT/SIGTERM handlers when safe to do so, runs
    startup, and guarantees shutdown runs even if an error occurs.
    This foundation-only path has no long-running services registered
    (see start_full_system() for the full pipeline used by the
    Streamlit dashboard); it returns immediately after a successful
    startup/shutdown cycle.

    Signal registration only works on the main thread of the main
    interpreter -- calling signal.signal() anywhere else raises
    ValueError. Streamlit's ScriptRunner executes this module via
    exec() on a worker thread while still setting __name__ to
    "__main__", so this checks first and skips registration when unsafe.

    Returns:
        Process exit code: 0 on success, 1 on startup failure.
    """
    app = Application()

    def _handle_signal(signum: int, frame: Optional[types.FrameType]) -> None:
        app.logger.info("Received signal %s, initiating shutdown.", signum)
        raise KeyboardInterrupt

    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)
    else:
        get_logger(__name__).info(
            "main() is not running on the main thread (e.g. under `streamlit run app.py`); "
            "skipping SIGINT/SIGTERM handler registration. Graceful shutdown via "
            "try/finally is unaffected."
        )

    try:
        app.startup()
    except ConfigurationError as exc:
        get_logger(__name__).error("Startup failed: %s", exc)
        return 1
    except Exception:
        get_logger(__name__).exception("Unexpected error during startup")
        return 1

    try:
        app.logger.info("Application foundation ready. No long-running services are registered yet.")
    finally:
        app.shutdown()

    return 0


if __name__ == "__main__" and threading.current_thread() is threading.main_thread():
    # The extra main-thread check (beyond the usual __name__ guard) is
    # required because Streamlit's ScriptRunner executes this module via
    # exec() on a worker thread while still setting __name__ to
    # "__main__", which would otherwise call main() there too --
    # main()'s sys.exit() raises SystemExit, which Streamlit's own
    # script-execution wrapper does not catch. Streamlit pages always
    # use get_running_application() instead, so skipping main() entirely
    # under Streamlit loses no functionality.
    sys.exit(main())
