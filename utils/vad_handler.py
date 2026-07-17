"""Voice Activity Detection and interruption handling for EthioChatbot V2.

Uses WebRTC VAD to detect speech and silence in the microphone stream,
per ARCHITECTURE.md's VAD Service responsibilities. When speech is
detected while a response is playing, drives the full interruption
workflow from README.md: pause the response (utils/playback.py), play
please_wait.wav to completion, then wait for sustained silence before
resuming the original response from its exact paused position --
never restarting it.

please_wait.wav is played with a small, separate blocking player
(mirroring utils/greeting_service.py's approach) rather than through
the PlaybackService instance that owns the paused original response:
that service tracks exactly one "current" sound, and reusing it for
please_wait.wav would overwrite the paused response's channel
reference needed to resume it correctly.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Dict, Optional

import pygame
import webrtcvad

from utils.event_bus import EventBus
from utils.fsm import PLAYING_AUDIO
from utils.logger import get_logger
from utils.playback import PlaybackService
from utils.state_manager import StateManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# WebRTC VAD only accepts 8000/16000/32000/48000 Hz and 10/20/30 ms frames.
VAD_SAMPLE_RATE = 16000
VAD_FRAME_DURATION_MS = 30
VAD_FRAME_BYTES = int(VAD_SAMPLE_RATE * (VAD_FRAME_DURATION_MS / 1000.0)) * 2  # 16-bit mono PCM

DEFAULT_AGGRESSIVENESS = 2  # matches config/settings.json's vad_aggressiveness default
DEFAULT_SILENCE_DURATION_MS = 600

DEFAULT_PLEASE_WAIT_AUDIO: Dict[str, Path] = {
    "english": PROJECT_ROOT / "audio" / "english" / "please_wait.wav",
    "amharic": PROJECT_ROOT / "audio" / "amharic" / "please_wait.wav",
    "arabic": PROJECT_ROOT / "audio" / "arabic" / "please_wait.wav",
}


def _play_wav_blocking(path: Path) -> None:
    """Play a WAV file to completion, blocking the calling thread.

    Minimal playback used only for please_wait.wav, which is never
    itself paused/resumed/interrupted. See module docstring for why
    this doesn't go through utils/playback.py's PlaybackService.
    """
    if not path.exists():
        logger.error("please_wait audio file not found: %s", path)
        return

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    sound = pygame.mixer.Sound(str(path))
    channel = sound.play()
    while channel is not None and channel.get_busy():
        time.sleep(0.02)


class VADHandler:
    """Detects speech/silence and drives the full interruption workflow.

    Implements app.py's Service protocol (name, start, stop). Owns no
    microphone capture thread; a future audio capture service feeds
    raw PCM frames to process_frame().
    """

    name = "vad_handler"

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        state_manager: Optional[StateManager] = None,
        playback_service: Optional[PlaybackService] = None,
        aggressiveness: int = DEFAULT_AGGRESSIVENESS,
        please_wait_audio: Optional[Dict[str, Path]] = None,
        silence_duration_ms: int = DEFAULT_SILENCE_DURATION_MS,
    ) -> None:
        """Args:
            event_bus: Bus to publish INTERRUPTION_DETECTED/
                INTERRUPTION_AUDIO_STARTED/INTERRUPTION_AUDIO_FINISHED/
                INTERRUPTION_CLEARED on. Optional so process_frame()
                can be exercised without full app wiring.
            state_manager: Shared state read to check current_state
                (only interrupt during PLAYING_AUDIO) and
                current_language (to pick the right please_wait.wav).
            playback_service: The PlaybackService whose response is
                paused/resumed around the interruption.
            aggressiveness: WebRTC VAD aggressiveness (0-3); higher
                filters out more non-speech.
            please_wait_audio: Per-language please_wait.wav paths;
                defaults to DEFAULT_PLEASE_WAIT_AUDIO.
            silence_duration_ms: How much continuous silence (after
                please_wait.wav finishes) is required before resuming.
        """
        self._bus = event_bus
        self._state = state_manager
        self._playback = playback_service
        self._aggressiveness = aggressiveness
        self._vad = webrtcvad.Vad(aggressiveness)
        self._please_wait_audio: Dict[str, Path] = {
            language: Path(path) for language, path in (please_wait_audio or DEFAULT_PLEASE_WAIT_AUDIO).items()
        }

        self._silent_frames_required = max(1, round(silence_duration_ms / VAD_FRAME_DURATION_MS))
        self._consecutive_silent_frames = 0
        self._interrupted = False
        self._please_wait_finished = False

        self._lock = threading.RLock()
        self._please_wait_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Lifecycle hook for ServiceRegistry compatibility."""
        logger.info("VAD handler started (aggressiveness=%d)", self._aggressiveness)

    def stop(self) -> None:
        """Lifecycle hook for ServiceRegistry compatibility."""
        logger.info("VAD handler stopped")

    def is_speech(self, frame: bytes) -> bool:
        """Return True if frame contains speech.

        Args:
            frame: 16-bit mono PCM bytes, VAD_FRAME_DURATION_MS long at
                VAD_SAMPLE_RATE (exactly VAD_FRAME_BYTES bytes).
        """
        return self._vad.is_speech(frame, VAD_SAMPLE_RATE)

    @property
    def is_interrupted(self) -> bool:
        """Whether an interruption cycle is currently in progress."""
        with self._lock:
            return self._interrupted

    def process_frame(self, frame: bytes) -> None:
        """Feed one audio frame through VAD and drive the interruption workflow.

        Args:
            frame: 16-bit mono PCM bytes, exactly VAD_FRAME_BYTES long.
        """
        speech = self.is_speech(frame)

        with self._lock:
            if not self._interrupted:
                if speech and self._should_interrupt_now():
                    self._begin_interruption()
                return

            if not self._please_wait_finished:
                # Still playing the acknowledgement cue; per README's
                # workflow, silence isn't monitored until it completes.
                return

            if speech:
                self._consecutive_silent_frames = 0
            else:
                self._consecutive_silent_frames += 1
                if self._consecutive_silent_frames >= self._silent_frames_required:
                    self._clear_interruption()

    def _should_interrupt_now(self) -> bool:
        """Only interrupt while a response is actually playing."""
        return self._state is not None and self._state.current_state == PLAYING_AUDIO

    def _begin_interruption(self) -> None:
        """Pause playback, publish INTERRUPTION_DETECTED, play please_wait.wav."""
        self._interrupted = True
        self._please_wait_finished = False
        self._consecutive_silent_frames = 0

        logger.info("Speech detected during playback: beginning interruption")
        self._publish("INTERRUPTION_DETECTED", {})

        if self._playback is not None:
            self._playback.pause_audio()

        language = (self._state.current_language if self._state is not None else None) or "english"
        please_wait_path = self._please_wait_audio.get(language, self._please_wait_audio["english"])

        self._please_wait_thread = threading.Thread(
            target=self._play_please_wait, args=(please_wait_path,), name="PleaseWaitThread", daemon=True
        )
        self._please_wait_thread.start()

    def _play_please_wait(self, path: Path) -> None:
        self._publish("INTERRUPTION_AUDIO_STARTED", {})
        logger.info("Playing interruption audio: %s", path)
        _play_wav_blocking(path)
        self._publish("INTERRUPTION_AUDIO_FINISHED", {})
        with self._lock:
            self._please_wait_finished = True

    def _clear_interruption(self) -> None:
        """Publish INTERRUPTION_CLEARED and resume the original response."""
        logger.info("Sustained silence detected: clearing interruption")
        self._interrupted = False
        self._please_wait_finished = False
        self._consecutive_silent_frames = 0

        self._publish("INTERRUPTION_CLEARED", {})

        if self._playback is not None:
            self._playback.resume_audio()

    def _publish(self, event_name: str, payload: dict) -> None:
        if self._bus is not None:
            self._bus.publish(event_name, payload)
