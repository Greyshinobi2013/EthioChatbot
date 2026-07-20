"""Audio playback engine for EthioChatbot V3.

Plays prerecorded WAV/MP3 audio with pause, resume, and restart
support, per SYSTEM_ARCHITECTURE_V3.md's Playback Service
responsibilities and DEVELOPMENT_RULES_V3.md Rule 18 (this is the only
component allowed to control audio -- utils/greeting_manager.py is its
sole caller, for both greetings and dialogs).

Resume is implemented with pygame's Channel.pause()/unpause() rather
than a manual seek-and-replay. A pygame Sound is fully decoded into
memory up front, so pausing a Channel only stops its internal read
cursor -- it does not stop and restart the sound. This makes resume
sample-accurate even for WAV, where a naive seek-based approach is
unreliable across pygame/SDL_mixer versions, satisfying the Dialog
Interruption Framework's "must not restart from the beginning"
requirement. Per STATE_MACHINE_V3.md, only dialog playback is ever
paused -- greeting_manager.py never calls pause_audio() while a
greeting is playing, since PLAY_GREETINGS has no INTERRUPT_DIALOG
transition in fsm.py's transition table.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import pygame

from utils.event_bus import EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

SUPPORTED_SUFFIXES = (".wav", ".mp3")


class PlaybackError(Exception):
    """Raised for invalid playback operations (bad file, wrong state, etc.)."""


class PlaybackState(str, Enum):
    """Playback lifecycle states, tracked per Milestone 8's requirements."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"
    STOPPED = "stopped"


@dataclass(frozen=True)
class PlaybackStatus:
    """Point-in-time snapshot of playback state.

    Attributes:
        state: Current PlaybackState.
        current_file: Path of the loaded audio, or None if nothing
            has been played yet.
        position_seconds: Elapsed playback time, not counting paused
            intervals. Tracked via wall-clock bookkeeping for
            reporting; the actual resume mechanism does not depend on
            this value being exact.
        duration_seconds: Total length of the loaded audio, or None.
    """

    state: PlaybackState
    current_file: Optional[str]
    position_seconds: float
    duration_seconds: Optional[float]


class PlaybackService:
    """Plays WAV/MP3 audio with pause/resume/restart support.

    Implements app.py's Service protocol (name, start, stop).
    """

    name = "playback_service"

    def __init__(self, event_bus: Optional[EventBus] = None, state_manager: Optional[StateManager] = None) -> None:
        """Args:
            event_bus: Bus to publish PLAYBACK_STARTED/PAUSED/RESUMED/
                STOPPED/FINISHED on. Optional so this can be used
                standalone without full app wiring.
            state_manager: Shared state this service pushes its status
                into after every transition, for the dashboard's
                Playback Status display and the Restart Greetings
                button's pause detection. Optional for the same reason
                as event_bus.
        """
        self._bus = event_bus
        self._state_manager = state_manager
        self._lock = threading.RLock()

        self._sound: Optional[pygame.mixer.Sound] = None
        self._channel: Optional[pygame.mixer.Channel] = None
        self._current_file: Optional[Path] = None
        self._state: PlaybackState = PlaybackState.IDLE

        # Wall-clock position bookkeeping, for status reporting only.
        self._position_offset = 0.0
        self._segment_started_at: Optional[float] = None

        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_stop = threading.Event()

    def start(self) -> None:
        """Ensure the pygame mixer is initialized."""
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        logger.info("Playback service started")

    def stop(self) -> None:
        """Stop any active playback."""
        self.stop_audio()
        logger.info("Playback service stopped")

    def play_audio(self, path: Path) -> None:
        """Load and play an audio file from the beginning.

        Args:
            path: Path to a .wav or .mp3 file.

        Raises:
            PlaybackError: if the file doesn't exist or has an
                unsupported extension.
        """
        path = Path(path)
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise PlaybackError(f"Unsupported audio format: {path.suffix} (expected .wav or .mp3)")
        if not path.exists():
            raise PlaybackError(f"Audio file not found: {path}")

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Stop the watcher before taking the lock: the watcher itself
        # acquires this lock every poll iteration, so joining it while
        # holding the lock would deadlock.
        self._stop_watcher()

        with self._lock:
            if self._channel is not None:
                self._channel.stop()
            self._sound = pygame.mixer.Sound(str(path))
            self._current_file = path
            self._position_offset = 0.0
            self._channel = self._sound.play()
            self._segment_started_at = time.time()
            self._state = PlaybackState.PLAYING

        logger.info("PLAYBACK_STARTED: %s", path)
        self._publish("PLAYBACK_STARTED", {"audio": str(path)})
        self._sync_state()
        self._start_watcher()

    def pause_audio(self) -> None:
        """Pause playback, preserving position for resume_audio()."""
        with self._lock:
            if self._state != PlaybackState.PLAYING or self._channel is None:
                logger.warning("pause_audio() called while not playing (state=%s); ignoring", self._state)
                return
            self._channel.pause()
            self._position_offset += self._elapsed_since_segment_start()
            self._segment_started_at = None
            self._state = PlaybackState.PAUSED

        logger.info("PLAYBACK_PAUSED: %s", self._current_file)
        self._publish("PLAYBACK_PAUSED", {})
        self._sync_state()

    def resume_audio(self) -> None:
        """Resume playback from exactly where it was paused.

        Uses Channel.unpause(), so this continues from the exact
        sample position the channel was paused at -- it does not
        restart the file.
        """
        with self._lock:
            if self._state != PlaybackState.PAUSED or self._channel is None:
                logger.warning("resume_audio() called while not paused (state=%s); ignoring", self._state)
                return
            self._channel.unpause()
            self._segment_started_at = time.time()
            self._state = PlaybackState.PLAYING

        logger.info("PLAYBACK_RESUMED: %s", self._current_file)
        self._publish("PLAYBACK_RESUMED", {})
        self._sync_state()

    def restart_audio(self) -> None:
        """Replay the currently loaded audio file from the beginning.

        Raises:
            PlaybackError: if no audio has been loaded yet.
        """
        with self._lock:
            if self._sound is None or self._current_file is None:
                raise PlaybackError("restart_audio() called with no audio loaded")

        self._stop_watcher()

        with self._lock:
            if self._channel is not None:
                self._channel.stop()
            self._position_offset = 0.0
            self._channel = self._sound.play()
            self._segment_started_at = time.time()
            self._state = PlaybackState.PLAYING

        logger.info("Playback restarted: %s", self._current_file)
        self._publish("PLAYBACK_STARTED", {"audio": str(self._current_file)})
        self._sync_state()
        self._start_watcher()

    def stop_audio(self) -> None:
        """Stop playback and reset state. A manual stop, not a completion."""
        self._stop_watcher()

        with self._lock:
            if self._channel is not None:
                self._channel.stop()
            self._channel = None
            self._state = PlaybackState.STOPPED
            self._position_offset = 0.0
            self._segment_started_at = None
            stopped_file = self._current_file

        logger.info("PLAYBACK_STOPPED: %s", stopped_file)
        self._publish("PLAYBACK_STOPPED", {})
        self._sync_state()

    def get_status(self) -> PlaybackStatus:
        """Return a point-in-time snapshot of playback state and position."""
        with self._lock:
            position = self._position_offset
            if self._state == PlaybackState.PLAYING:
                position += self._elapsed_since_segment_start()
            duration = self._sound.get_length() if self._sound is not None else None
            return PlaybackStatus(
                state=self._state,
                current_file=str(self._current_file) if self._current_file else None,
                position_seconds=position,
                duration_seconds=duration,
            )

    def _elapsed_since_segment_start(self) -> float:
        if self._segment_started_at is None:
            return 0.0
        return time.time() - self._segment_started_at

    def _start_watcher(self) -> None:
        self._watcher_stop.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_for_completion, name="PlaybackWatcher", daemon=True
        )
        self._watcher_thread.start()

    def _stop_watcher(self) -> None:
        self._watcher_stop.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=2.0)
        self._watcher_thread = None

    def _watch_for_completion(self) -> None:
        """Poll the channel and publish PLAYBACK_FINISHED once it stops on its own.

        The busy-check and the state read/write happen inside the
        same lock acquisition as pause_audio()'s pause()+state-update,
        so a pause can never be misread as natural completion.
        """
        while not self._watcher_stop.is_set():
            finished_file = None
            with self._lock:
                channel = self._channel
                if channel is None:
                    return
                if self._state == PlaybackState.PLAYING and not channel.get_busy():
                    self._state = PlaybackState.FINISHED
                    finished_file = self._current_file

            if finished_file is not None:
                logger.info("PLAYBACK_FINISHED: %s", finished_file)
                self._publish("PLAYBACK_FINISHED", {})
                self._sync_state()
                return

            time.sleep(0.05)

    def _publish(self, event_name: str, payload: dict) -> None:
        if self._bus is not None:
            self._bus.publish(event_name, payload)

    def _sync_state(self) -> None:
        if self._state_manager is None:
            return
        status = self.get_status()
        self._state_manager.set_playback_status(
            {
                "state": status.state.value,
                "current_file": status.current_file,
                "position_seconds": status.position_seconds,
                "duration_seconds": status.duration_seconds,
            }
        )
