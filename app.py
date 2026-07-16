"""Streamlit entry point and application bootstrap.

Milestone 1 scope: configuration loading, logging, shared application
state, and the service-thread bootstrap structure (see ARCHITECTURE.md
"Startup Sequence"). Camera, microphone, face recognition, Whisper, VAD,
playback, and the full state machine are added in later milestones and
plug into bootstrap_services() below without changing this file's shape.
"""
from __future__ import annotations

import platform
import threading
from datetime import datetime, timezone

import streamlit as st

from utils.logger import LOG_FILE, get_logger
from utils.state_manager import AppState, load_configuration

logger = get_logger("app")


def bootstrap_services(state: AppState) -> None:
    """Register background service threads on shared state.

    Milestone 1 has no services to register: camera_service, audio_service,
    whisper_utils, vad_handler, and playback are added in Milestones 2-5 and
    will do `state.services["camera"] = threading.Thread(...)` etc. here.
    This is the wiring point those milestones extend, not a stand-in for
    logic that belongs in Milestone 1.
    """
    logger.info("Service bootstrap: %d service(s) registered", len(state.services))


def start_registered_services(state: AppState) -> None:
    """Start every thread currently registered in state.services."""
    for name, thread in state.services.items():
        if not thread.is_alive():
            thread.start()
            logger.info("Service thread started: %s", name)
    if not state.services:
        logger.info("No service threads to start (Milestone 1)")


def bootstrap_app() -> AppState:
    """Run the application startup sequence and return shared state.

    Sequence (ARCHITECTURE.md): load configuration -> initialize shared
    state -> bootstrap service threads -> enter IDLE.
    """
    logger.info("SYSTEM_STARTUP begin")

    config = load_configuration()
    logger.info(
        "Configuration loaded: whisper_model=%s, camera_index=%s, vad_aggressiveness=%s",
        config["whisper_model"], config["camera_index"], config["vad_aggressiveness"],
    )

    state = AppState(config=config)
    logger.info("Shared application state initialized")

    bootstrap_services(state)
    start_registered_services(state)

    state.system_status = "RUNNING"
    state.set_state("IDLE")

    logger.info("SYSTEM_STARTUP complete")
    return state


@st.cache_resource(show_spinner=False)
def get_app_state() -> AppState:
    """Streamlit-cached singleton so bootstrap runs once per process, not per rerun."""
    return bootstrap_app()


def render_dashboard(state: AppState) -> None:
    st.set_page_config(page_title="Offline Conversational Robot", page_icon="🤖")
    st.title("Offline Multimodal Conversational Robot")
    st.caption(
        "Milestone 1: Project Setup — configuration, logging, shared state, service bootstrap"
    )

    snapshot = state.snapshot()

    col1, col2, col3 = st.columns(3)
    col1.metric("System Status", snapshot["system_status"])
    col2.metric("Current State", snapshot["current_state"])
    col3.metric("Registered Services", len(snapshot["registered_services"]))

    st.subheader("Configuration")
    st.json(state.config)

    st.subheader("Runtime State")
    st.json(snapshot)

    st.subheader("Logging")
    st.write(f"Log file: `{LOG_FILE.resolve()}`")

    st.subheader("Host Environment")
    st.json(
        {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "active_threads": threading.active_count(),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def main() -> None:
    state = get_app_state()
    render_dashboard(state)


main()
