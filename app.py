"""Streamlit entry point and application bootstrap.

This file owns startup only (ARCHITECTURE.md "Startup Sequence") and a
minimal landing page. Milestone 1 added configuration loading, logging,
shared application state, and the service-thread bootstrap structure.
Milestone 2 plugged in the camera service and the automatic greeting
workflow. Milestone 3 plugged in the continuous microphone service
(Whisper-based wake-word detection) and language selection. Milestone 4
added the scenario engine. Milestone 5 plugged in the VAD
interruption-monitoring service. Milestone 6 wired live conversation
transcription into the scenario engine and added the timeout-monitoring
service plus a validated finite state machine (utils/state_manager.py).
Milestone 7 moves the full monitoring view into pages/1_Dashboard.py and
adds pages/2_Enroll_Face.py, pages/3_Manage_Scenarios.py, and
pages/4_Settings.py -- all UI-only, reading/writing through utils/*
functions rather than containing business logic themselves (CLAUDE.md
"Streamlit is NOT the robot").

pages/*.py import get_app_state from this module to reach the same
cached AppState singleton; st.cache_resource is keyed by function
identity, not by which script called it, so this is safe and does not
re-run bootstrap. Guarding main() with `if __name__ == "__main__"` (below)
is what makes that safe: a page importing this module runs its
definitions but not main()/bootstrap again.
"""
from __future__ import annotations

import threading

import streamlit as st

from utils import audio_service, camera_service, conversation_manager, vad_handler
from utils.logger import get_logger
from utils.state_manager import AppState, load_configuration

logger = get_logger("app")


def bootstrap_services(state: AppState) -> None:
    """Register background service threads on shared state."""
    conversation_manager.register_handlers(state)

    state.services["camera"] = threading.Thread(
        target=camera_service.run_camera_service,
        args=(state, state.stop_event),
        name="camera_service",
        daemon=True,
    )
    state.services["audio"] = threading.Thread(
        target=audio_service.run_audio_service,
        args=(state, state.stop_event),
        name="audio_service",
        daemon=True,
    )
    state.services["vad"] = threading.Thread(
        target=vad_handler.monitor_interruptions,
        args=(state, state.stop_event),
        name="vad_handler",
        daemon=True,
    )
    state.services["timeout"] = threading.Thread(
        target=conversation_manager.monitor_timeout,
        args=(state, state.stop_event),
        name="timeout_monitor",
        daemon=True,
    )

    logger.info("Service bootstrap: %d service(s) registered", len(state.services))


def start_registered_services(state: AppState) -> None:
    """Start every thread currently registered in state.services."""
    for name, thread in state.services.items():
        if not thread.is_alive():
            thread.start()
            logger.info("Service thread started: %s", name)
    if not state.services:
        logger.info("No service threads to start")


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


def render_landing(state: AppState) -> None:
    st.set_page_config(page_title="Offline Conversational Robot", page_icon="🤖")
    st.title("Offline Multimodal Conversational Robot")
    st.caption("Offline, event-driven conversational robot -- see the pages in the sidebar.")

    snapshot = state.snapshot()
    col1, col2, col3 = st.columns(3)
    col1.metric("System Status", snapshot["system_status"])
    col2.metric("Current State", snapshot["current_state"])
    col3.metric("Recognized User", snapshot["recognized_user"] or "-")

    st.markdown(
        "Use the sidebar to navigate:\n"
        "- **Dashboard** -- live camera feed, status, and logs\n"
        "- **Enroll Face** -- register a new user\n"
        "- **Manage Scenarios** -- wake words and conversation dialogs\n"
        "- **Settings** -- recognition/VAD/Whisper/GPU configuration"
    )


def main() -> None:
    state = get_app_state()
    render_landing(state)


if __name__ == "__main__":
    main()
