import threading
import time
from typing import Optional, Dict, Any, Callable, List

from core.constants import BotState
from core.config import logger
from core.face_engine import FaceEngine
from core.stt_engine import STTEngine
from core.audio_engine import AudioEngine
from core.scenario_manager import ScenarioManager


class BotController:

    def __init__(self, config: Dict[str, Any] = None):

        cfg = config or {}

        self.state = BotState.IDLE

        self._stop_event = threading.Event()
        self._running = False

        self.current_user = None

        # Engines

        self.face_engine = FaceEngine(
            consecutive_frames=cfg.get("face_consecutive_frames", 5)
        )

        self.stt_engine = STTEngine(
            model_size=cfg.get("whisper_model", "medium")
        )

        self.audio_engine = AudioEngine()

        self.scenario_manager = ScenarioManager()

        # Wake words

        self._wake_words = self.scenario_manager.all_wake_words() or [
            "hello", "ሰላም"
        ]

        self.stt_engine.wake_words = self._wake_words

        # Callbacks

        self.on_state_change = None
        self.on_message = None
        self.on_face_detected = None
        self.on_transcript = None

        self._setup_callbacks()

    # ------------------------------------------------------

    def _setup_callbacks(self):

        self.stt_engine.on_transcript = self._on_transcript
        self.stt_engine.on_wake_word = self._on_wake_word

    # ------------------------------------------------------

    def start(self, camera_index=0):

        if self._running:
            return

        logger.info("Starting BotController...")

        self._stop_event.clear()
        self._running = True

        threading.Thread(
            target=self.face_engine.run_detection_loop,
            args=(self._on_face, self._stop_event, camera_index),
            daemon=True
        ).start()

        self._set_state(BotState.IDLE)

    # ------------------------------------------------------

    def stop(self):

        self._stop_event.set()
        self.audio_engine.stop()
        self._running = False
        self._set_state(BotState.IDLE)

    # ------------------------------------------------------
    # AUDIO FROM WEBRTC

    def feed_audio(self, audio_chunk):

        self.stt_engine.process_audio(audio_chunk)

    # ------------------------------------------------------

    def _set_state(self, s):

        self.state = s

        if self.on_state_change:
            self.on_state_change(s)

    # ------------------------------------------------------

    def _on_face(self, name, conf):

        if self.state != BotState.IDLE:
            return

        self.current_user = name

        if self.on_face_detected:
            self.on_face_detected(name, conf)

        self._set_state(BotState.LISTENING_WAKE_WORD)

    # ------------------------------------------------------

    def _on_transcript(self, text):

        if self.on_transcript:
            self.on_transcript(text)

    # ------------------------------------------------------

    def _on_wake_word(self, word):

        if self.on_message:
            self.on_message("assistant", f"Wake word: {word}")

        self._set_state(BotState.PLAYING_SCENARIO)