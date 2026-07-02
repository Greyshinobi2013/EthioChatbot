import pygame
import threading
import time
from pathlib import Path
from typing import List, Callable, Optional

from core.config import logger


class ScenarioPlayer:
    """
    Handles sequential playback of audio clips.
    Supports interruption and stop controls.
    """

    def __init__(self, silence_gap_ms: int = 800):

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.silence_gap = silence_gap_ms / 1000.0

        self._is_interrupted = False
        self._stop_event = threading.Event()

        self._current_clip_index = 0
        self._total_clips = 0

        self._on_complete_callback: Optional[Callable] = None

    def play_scenario(
        self,
        clips: List[Path],
        on_clip_start: Optional[Callable[[int, Path], None]] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """
        Starts playback in a background thread.
        """

        self._stop_event.clear()
        self._is_interrupted = False

        self._total_clips = len(clips)
        self._on_complete_callback = on_complete

        threading.Thread(
            target=self._playback_thread,
            args=(clips, on_clip_start),
            daemon=True,
        ).start()

    def _playback_thread(
        self,
        clips: List[Path],
        on_clip_start: Optional[Callable[[int, Path], None]],
    ):
        try:
            for i, clip_path in enumerate(clips):

                if self._stop_event.is_set():
                    break

                if i > 0:
                    time.sleep(self.silence_gap)

                if self._is_interrupted:
                    return

                if not clip_path.exists():
                    logger.warning(f"Audio clip not found: {clip_path}")
                    continue

                self._current_clip_index = i

                if on_clip_start:
                    on_clip_start(i, clip_path)

                pygame.mixer.music.load(str(clip_path))
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():

                    if (
                        self._stop_event.is_set()
                        or self._is_interrupted
                    ):
                        pygame.mixer.music.stop()
                        return

                    time.sleep(0.1)

            if (
                not self._stop_event.is_set()
                and not self._is_interrupted
                and self._on_complete_callback
            ):
                self._on_complete_callback()

        except Exception:
            logger.exception("Error in ScenarioPlayer")

    def notify_speech_detected(self):
        """
        Called when VAD detects user speech.
        """

        self._is_interrupted = True
        pygame.mixer.music.stop()

    def stop(self):
        """
        Immediately stop all playback.
        """

        self._stop_event.set()
        self._is_interrupted = True

        pygame.mixer.music.stop()


class AudioEngine:
    """
    High-level audio management.
    """

    def __init__(self, auto_restart: bool = False):

        self.auto_restart = auto_restart

        self.scenario_player = ScenarioPlayer()

        self._is_playing = False
        self._lock = threading.Lock()

    def is_playing(self) -> bool:
        """
        Returns True while audio is playing.
        """

        return pygame.mixer.music.get_busy()

    def play_scenario(
        self,
        clips: List[Path],
        on_complete: Callable,
    ):
        """
        Starts scenario playback.
        """

        with self._lock:

            self._is_playing = True

            def wrapped_complete():
                self._is_playing = False

                if on_complete:
                    on_complete()

            self.scenario_player.play_scenario(
                clips,
                on_complete=wrapped_complete,
            )

    def handle_interruption(
        self,
        on_warning_clip_ready: Callable[[], None] = None,
    ):
        """
        Handles interruption requests.
        """

        logger.info(
            "AudioEngine: Interruption protocol triggered."
        )

        self.scenario_player.notify_speech_detected()

        self._is_playing = False

        return True

    def stop(self):
        """
        Stop all audio activity.
        """

        with self._lock:

            self.scenario_player.stop()

            self._is_playing = False

    def set_auto_restart(self, enabled: bool):

        self.auto_restart = enabled