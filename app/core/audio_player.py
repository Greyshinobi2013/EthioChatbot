"""
Audio playback for pre-recorded dialog responses.

Uses pygame.mixer because (unlike `playsound`) it supports pause/unpause
and querying playback position/busy-state natively and without
blocking the calling thread -- both are required for the
interruption-handling feature.

Concurrency model
------------------
`AudioPlayer.play()` is non-blocking: it starts playback on pygame's
own mixer thread and returns immediately. The chatbot's main
orchestration loop (see core.orchestrator) polls `is_busy()` /
reacts to the VAD callback to decide when to pause. This keeps audio
playback and speech monitoring running "simultaneously" as required,
without us needing to hand-roll a separate audio thread.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import get_logger

logger = get_logger(__name__)

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None


class PlaybackState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class PlaybackStatus:
    state: PlaybackState
    current_file: Optional[Path]
    paused_due_to_interruption: bool = False


class AudioPlayer:
    """Thin, thread-safe wrapper around pygame.mixer.music.

    Only one clip plays at a time (matches the single-speaker dialog
    model of this chatbot); calling `play()` while something else is
    playing stops the previous clip first.
    """

    def __init__(self):
        if pygame is None:
            raise ImportError("pygame is required for audio playback.")
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self._lock = threading.Lock()
        self._current_file: Optional[Path] = None
        self._state = PlaybackState.IDLE
        self._paused_due_to_interruption = False
        self._on_finished_callback = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_watcher = threading.Event()

    # -- public API -----------------------------------------------------------

    def play(self, filepath: Path, on_finished=None) -> None:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        with self._lock:
            pygame.mixer.music.load(str(filepath))
            pygame.mixer.music.play()
            self._current_file = filepath
            self._state = PlaybackState.PLAYING
            self._paused_due_to_interruption = False
            self._on_finished_callback = on_finished

        self._start_watcher()
        logger.info("Playing audio: %s", filepath.name)

    def pause_for_interruption(self) -> None:
        """Pause playback because the user started talking. Distinct
        from a generic `pause()` so the UI/orchestrator can tell *why*
        playback stopped and show the right message."""
        with self._lock:
            if self._state == PlaybackState.PLAYING:
                pygame.mixer.music.pause()
                self._state = PlaybackState.PAUSED
                self._paused_due_to_interruption = True
                logger.info("Playback paused due to user interruption.")

    def resume_or_restart(self, mode: str = "restart") -> None:
        """Continue playback after an interruption.

        mode="resume": continues from where pygame paused (pygame
                        preserves position across pause/unpause for the
                        currently loaded track).
        mode="restart": re-plays the current file from the beginning,
                        which is often clearer for short dialog clips
                        since the user likely missed the start anyway.
        """
        with self._lock:
            if self._state != PlaybackState.PAUSED or self._current_file is None:
                return

            if mode == "resume":
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.play()

            self._state = PlaybackState.PLAYING
            self._paused_due_to_interruption = False
            logger.info("Playback %s: %s", "resumed" if mode == "resume" else "restarted", self._current_file.name)

    def stop(self) -> None:
        with self._lock:
            pygame.mixer.music.stop()
            self._state = PlaybackState.IDLE
            self._paused_due_to_interruption = False
        self._stop_watcher_thread()

    def is_busy(self) -> bool:
        return self._state == PlaybackState.PLAYING

    def status(self) -> PlaybackStatus:
        return PlaybackStatus(
            state=self._state,
            current_file=self._current_file,
            paused_due_to_interruption=self._paused_due_to_interruption,
        )

    # -- internals: end-of-track detection -------------------------------------
    #
    # pygame.mixer.music has no native "on finished" event, so we poll
    # `pygame.mixer.music.get_busy()` on a small watcher thread and fire
    # the callback once it goes false while we're still in PLAYING
    # state (i.e. it wasn't *us* who stopped it via pause/stop).

    def _start_watcher(self) -> None:
        self._stop_watcher_thread()
        self._stop_watcher.clear()
        self._watcher_thread = threading.Thread(target=self._watch_for_end, daemon=True)
        self._watcher_thread.start()

    def _stop_watcher_thread(self) -> None:
        self._stop_watcher.set()
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=1)

    def _watch_for_end(self) -> None:
        while not self._stop_watcher.is_set():
            time.sleep(0.1)
            with self._lock:
                still_playing_state = self._state == PlaybackState.PLAYING
                mixer_busy = pygame.mixer.music.get_busy()
                if still_playing_state and not mixer_busy:
                    self._state = PlaybackState.FINISHED
                    callback = self._on_finished_callback
                else:
                    callback = None
            if callback:
                try:
                    callback()
                except Exception:
                    logger.exception("Error in on_finished callback")
                return
            if not still_playing_state:
                return
