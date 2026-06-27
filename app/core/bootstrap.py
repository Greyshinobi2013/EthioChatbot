"""
Heavy-resource initialization (dlib models, Whisper model, pygame
mixer, the orchestrator itself).

Streamlit reruns the whole script top-to-bottom on every interaction,
so anything expensive (loading a Whisper model, opening pygame's
mixer) must be wrapped in `st.cache_resource` at the call site in the
UI layer -- this module just provides the plain constructors that the
UI wraps. Keeping the cache decorators out of `app/core` keeps this
package importable/testable without Streamlit installed.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import APP_DIR, get_logger
from app.core.dialog_manager import DialogManager
from app.core.face_engine import FaceEngine
from app.core.orchestrator import ChatbotOrchestrator
from app.core.speech_engine import Transcriber

logger = get_logger(__name__)

DLIB_MODELS_DIR = "app/models/"


def build_face_engine() -> Optional[FaceEngine]:
    try:
        return FaceEngine(models_dir=DLIB_MODELS_DIR)
    except Exception as exc:
        logger.warning("Face engine unavailable: %s", exc)
        return None


def build_transcriber() -> Optional[Transcriber]:
    try:
        return Transcriber()
    except Exception as exc:
        logger.warning("Speech transcriber unavailable: %s", exc)
        return None


def build_orchestrator() -> ChatbotOrchestrator:
    """Build the orchestrator for a session.

    Face recognition and speech recognition are treated as optional —
    the chatbot can still run in a reduced mode (manual scenario
    triggering from the dashboard) without them. Audio playback is
    NOT optional: it's the one feature with no fallback (a chatbot
    with no audio output cannot do anything), so a missing `pygame`
    install is raised immediately with a clear, actionable message
    rather than deferred to a confusing failure later during playback.
    """
    face_engine = build_face_engine()
    transcriber = build_transcriber()
    dialog_manager = DialogManager()

    try:
        return ChatbotOrchestrator(
            face_engine=face_engine,
            dialog_manager=dialog_manager,
            transcriber=transcriber,
        )
    except ImportError as exc:
        raise ImportError(
            "Could not start the chatbot session because audio playback "
            f"is unavailable ({exc}). Install 'pygame' (see "
            "requirements.txt) and restart the app -- this dependency is "
            "required even in a reduced/no-camera/no-mic setup, since "
            "playing pre-recorded responses is the chatbot's core function."
        ) from exc
