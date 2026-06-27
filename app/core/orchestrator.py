"""
Chatbot Orchestrator.

This is the glue layer the Streamlit UI talks to. It owns a single
coherent session state machine:

    IDLE (watching for a face)
      -> FACE_RECOGNIZED (plays greeting)
      -> LISTENING_FOR_WAKE_WORD
      -> DIALOG_ACTIVE (playing scenario audio; VAD monitors for
         interruption in the background)
      -> back to IDLE (or LISTENING_FOR_WAKE_WORD) when scenario ends

The VAD monitor and the audio player each run on their own thread (see
core.audio_player / core.speech_engine), so "speech recognition and
audio playback run simultaneously" is satisfied at this layer: while
`AudioPlayer` plays a clip on pygame's mixer thread, the
`VoiceActivityMonitor` is independently polling the microphone on its
own thread and can call back into this orchestrator at any time to
trigger `_handle_interruption()`.

This module is intentionally Streamlit-agnostic (no `st.` calls) so it
can be unit-tested or reused behind a different UI; the Streamlit page
only reads `orchestrator.status_snapshot()` and calls its public
methods.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.audio_player import AudioPlayer
from app.core.config import SETTINGS, get_logger, resolve_audio_path
from app.core.dialog_manager import DialogManager
from app.core.face_engine import FaceEngine, FaceMatch
from app.core.speech_engine import (
    Transcriber,
    VoiceActivityMonitor,
    WakeWordListener,
)

logger = get_logger(__name__)


class SessionState(Enum):
    IDLE = "idle"
    FACE_RECOGNIZED = "face_recognized"
    LISTENING_FOR_WAKE_WORD = "listening_for_wake_word"
    DIALOG_ACTIVE = "dialog_active"
    PAUSED_FOR_INTERRUPTION = "paused_for_interruption"
    SCENARIO_COMPLETE = "scenario_complete"


@dataclass
class StatusSnapshot:
    session_state: SessionState
    recognized_user: Optional[str]
    language: Optional[str]
    scenario_id: Optional[str]
    step_id: Optional[str]
    last_message: str = ""


class ChatbotOrchestrator:
    def __init__(
        self,
        face_engine: Optional[FaceEngine],
        dialog_manager: DialogManager,
        transcriber: Optional[Transcriber] = None,
    ):
        self.face_engine = face_engine
        self.dialog_manager = dialog_manager
        self.transcriber = transcriber

        self.audio_player = AudioPlayer()
        self.wake_word_listener = (
            WakeWordListener(transcriber, dialog_manager.available_languages())
            if transcriber is not None
            else None
        )
        self.vad_monitor = VoiceActivityMonitor(on_speech_detected=self._handle_interruption)

        self.session_state = SessionState.IDLE
        self._last_message = ""
        self._recognized_user: Optional[str] = None
        self._lock = threading.RLock()

        # consecutive-frame confirmation for face recognition, so a
        # single flickering misdetection doesn't fire a greeting
        self._candidate_user: Optional[str] = None
        self._candidate_count = 0

    # ------------------------------------------------------------------
    # Face recognition loop (called once per webcam frame from the UI)
    # ------------------------------------------------------------------

    def process_frame(self, frame_bgr) -> list[FaceMatch]:
        """Call this once per webcam frame. Returns the raw matches so
        the UI can draw boxes; internally also drives the
        IDLE -> FACE_RECOGNIZED transition once a match is confirmed
        across several frames."""
        if self.face_engine is None:
            return []

        matches = self.face_engine.identify(frame_bgr)

        if self.session_state != SessionState.IDLE:
            return matches  # only auto-trigger greeting from IDLE

        best = next((m for m in matches if m.user_id), None)
        with self._lock:
            if best is None:
                self._candidate_user = None
                self._candidate_count = 0
                return matches

            if best.user_id == self._candidate_user:
                self._candidate_count += 1
            else:
                self._candidate_user = best.user_id
                self._candidate_count = 1

            if self._candidate_count >= SETTINGS.face_min_detections_to_confirm:
                self._on_face_confirmed(best.user_id)
                self._candidate_count = 0

        return matches

    def _on_face_confirmed(self, user_id: str) -> None:
        logger.info("Face confirmed: %s", user_id)
        self._recognized_user = user_id
        self.dialog_manager.set_user(user_id)
        self.session_state = SessionState.FACE_RECOGNIZED
        self._last_message = f"Welcome, {user_id}! Please say a wake word to begin (e.g. 'Hello' / 'ሰላም')."
        self.session_state = SessionState.LISTENING_FOR_WAKE_WORD

    # ------------------------------------------------------------------
    # Wake word detection (blocking call; run from a UI button or thread)
    # ------------------------------------------------------------------

    def listen_for_wake_word(self) -> bool:
        """Records a short clip and checks it for a configured wake
        word. On success, sets the language and starts the default
        scenario's audio. Returns True if a wake word was matched.
        """
        if self.wake_word_listener is None:
            self._last_message = "Speech recognition is not available (Whisper not loaded)."
            return False

        self._last_message = "Listening for wake word..."
        result = self.wake_word_listener.listen_once()

        if not result.matched:
            self._last_message = f"No wake word detected (heard: '{result.transcript}')."
            return False

        logger.info("Wake word matched. Language=%s transcript='%s'", result.language, result.transcript)
        self.dialog_manager.set_language(result.language)
        self._play_greeting_then_start_scenario()
        return True

    def _play_greeting_then_start_scenario(self) -> None:
        greeting_relative = self.dialog_manager.get_greeting_audio()
        if greeting_relative:
            self._play_clip(resolve_audio_path(greeting_relative), on_finished=self._start_default_scenario)
        else:
            self._start_default_scenario()

    def _start_default_scenario(self) -> None:
        relative_path = self.dialog_manager.start_scenario()
        self.session_state = SessionState.DIALOG_ACTIVE
        self._last_message = f"Starting scenario '{self.dialog_manager.state.scenario_id}'."
        if relative_path:
            self._play_clip(resolve_audio_path(relative_path), on_finished=self._on_step_finished)
        self.vad_monitor.start()

    # ------------------------------------------------------------------
    # Scenario stepping / playback orchestration
    # ------------------------------------------------------------------

    def _play_clip(self, absolute_path, on_finished=None) -> None:
        # Suppress VAD briefly around playback start to avoid the
        # system's own audio bleeding into the mic and self-triggering
        # an interruption (most relevant on devices without a headset).
        self.vad_monitor.suppress()
        self.audio_player.play(absolute_path, on_finished=self._wrap_finished(on_finished))
        threading.Timer(0.5, self.vad_monitor.resume_monitoring).start()

    def _wrap_finished(self, callback):
        def _inner():
            self.vad_monitor.resume_monitoring()
            if callback:
                callback()
        return _inner

    def _on_step_finished(self) -> None:
        if self.session_state == SessionState.PAUSED_FOR_INTERRUPTION:
            return  # don't auto-advance if we're actually paused

        relative_path = self.dialog_manager.advance()
        if relative_path is None:
            self.session_state = SessionState.SCENARIO_COMPLETE
            self._last_message = "Scenario complete. Say a wake word to start again."
            self.vad_monitor.stop()
            self.session_state = SessionState.LISTENING_FOR_WAKE_WORD
            return

        self._play_clip(resolve_audio_path(relative_path), on_finished=self._on_step_finished)

    def trigger_scenario(self, scenario_id: str) -> None:
        """Manually branch into a different scenario (e.g. from a
        Streamlit dashboard button), bypassing wake-word detection.
        Requires a language to already be set."""
        if self.dialog_manager.state.language is None:
            raise RuntimeError("Set a language before triggering a scenario.")
        relative_path = self.dialog_manager.jump_to_scenario(scenario_id)
        self.session_state = SessionState.DIALOG_ACTIVE
        if relative_path:
            self._play_clip(resolve_audio_path(relative_path), on_finished=self._on_step_finished)
        if not self.vad_monitor.is_running():
            self.vad_monitor.start()

    # ------------------------------------------------------------------
    # Interruption handling
    # ------------------------------------------------------------------

    def _handle_interruption(self) -> None:
        """Called from the VAD monitor's background thread the instant
        sustained speech is detected during playback."""
        with self._lock:
            if not self.audio_player.is_busy():
                return
            if not self.dialog_manager.current_step_is_interruptible():
                logger.info("Speech detected but current step is not interruptible; ignoring.")
                return

            logger.info("User interruption detected; pausing playback.")
            self.audio_player.pause_for_interruption()
            self.session_state = SessionState.PAUSED_FOR_INTERRUPTION
            self._last_message = "Please wait, I'll continue in a moment..."

            threading.Thread(target=self._resume_after_interruption, daemon=True).start()

    def _resume_after_interruption(self, wait_seconds: float = 2.5) -> None:
        """Give the user a moment to finish speaking, then resume or
        restart the paused clip, as configured."""
        time.sleep(wait_seconds)
        with self._lock:
            if self.session_state != SessionState.PAUSED_FOR_INTERRUPTION:
                return
            self.audio_player.resume_or_restart(mode=SETTINGS.audio_resume_mode)
            self.session_state = SessionState.DIALOG_ACTIVE
            self._last_message = "Continuing..."

    # ------------------------------------------------------------------
    # Status / teardown
    # ------------------------------------------------------------------

    def status_snapshot(self) -> StatusSnapshot:
        return StatusSnapshot(
            session_state=self.session_state,
            recognized_user=self._recognized_user,
            language=self.dialog_manager.state.language,
            scenario_id=self.dialog_manager.state.scenario_id,
            step_id=self.dialog_manager.state.step_id,
            last_message=self._last_message,
        )

    def reset(self) -> None:
        self.audio_player.stop()
        self.vad_monitor.stop()
        self.session_state = SessionState.IDLE
        self._recognized_user = None
        self._candidate_user = None
        self._candidate_count = 0
        self._last_message = "Session reset."

    def shutdown(self) -> None:
        self.audio_player.stop()
        self.vad_monitor.stop()
