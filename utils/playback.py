"""Prerecorded audio playback with pause/resume/restart and a separate
notification channel for interruption audio.

Milestone 2 added blocking play_audio() for one-shot clips (the greeting).
Milestone 5 adds pause/resume/restart with position tracking and
notify_user(), which plays a short clip (e.g. please_wait.wav) on its own
channel without disturbing a paused response -- required for the
interruption workflow (CLAUDE.md "INTERRUPTION RULE").

Uses pygame.mixer.Channel objects rather than pygame.mixer.music: music is
a single global stream, but the interruption workflow needs the main
response paused on one channel while a short notice plays independently on
another, without losing the response's paused position.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

import pygame

from utils.logger import get_logger

logger = get_logger("playback")

RESPONSE_CHANNEL_ID = 0
NOTIFICATION_CHANNEL_ID = 1

_mixer_ready = False
_mixer_lock = threading.Lock()
_response_channel: Optional["pygame.mixer.Channel"] = None

_current_path: Optional[Path] = None
_current_sound: Optional["pygame.mixer.Sound"] = None
_state = "IDLE"  # IDLE | PLAYING | PAUSED

_segment_started_at: Optional[float] = None  # monotonic seconds; None while paused/stopped
_elapsed_before_segment: float = 0.0


def _ensure_mixer() -> None:
    global _mixer_ready, _response_channel
    with _mixer_lock:
        if not _mixer_ready:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(max(8, NOTIFICATION_CHANNEL_ID + 1))
            _response_channel = pygame.mixer.Channel(RESPONSE_CHANNEL_ID)
            _mixer_ready = True
            logger.info("Audio mixer initialized")


def play_audio(path: Path, wait: bool = True) -> None:
    """Play a prerecorded WAV/MP3 file on the dedicated response channel.

    Blocking (wait=True) is correct for the response/greeting workflow:
    the caller's thread stays blocked here for the whole pause/resume
    interruption cycle too, since a paused channel stays "busy" until it
    actually finishes -- a concurrent VAD thread can pause/resume this
    same channel without this call needing to do anything special.
    """
    global _current_path, _current_sound, _state, _segment_started_at, _elapsed_before_segment

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    _ensure_mixer()
    sound = pygame.mixer.Sound(str(path))

    _current_path = path
    _current_sound = sound
    _elapsed_before_segment = 0.0
    _segment_started_at = time.monotonic()
    _state = "PLAYING"

    logger.info("Playing audio: %s", path)
    _response_channel.play(sound)

    if wait:
        while _response_channel.get_busy():
            pygame.time.wait(50)
        # Fold the final segment's elapsed time in before clearing it, so
        # get_position_seconds() reflects the full duration played instead
        # of freezing at the last pause point (it may never have been
        # paused at all).
        if _segment_started_at is not None:
            _elapsed_before_segment += time.monotonic() - _segment_started_at
        _state = "IDLE"
        _segment_started_at = None
        logger.info("Finished playing audio: %s", path)


def pause_audio() -> None:
    """Pause the response channel, preserving its exact playback position."""
    global _state, _segment_started_at, _elapsed_before_segment

    _ensure_mixer()
    if _response_channel is None or not _response_channel.get_busy() or _state != "PLAYING":
        return

    _response_channel.pause()
    if _segment_started_at is not None:
        _elapsed_before_segment += time.monotonic() - _segment_started_at
    _segment_started_at = None
    _state = "PAUSED"
    logger.info("Playback paused: %s (position=%.1fs)", _current_path, _elapsed_before_segment)


def resume_audio() -> None:
    """Resume the response channel from its exact paused position."""
    global _state, _segment_started_at

    _ensure_mixer()
    if _response_channel is None or _state != "PAUSED":
        return

    _response_channel.unpause()
    _segment_started_at = time.monotonic()
    _state = "PLAYING"
    logger.info("Playback resumed: %s", _current_path)


def restart_audio() -> None:
    """Restart the currently loaded response from the beginning."""
    global _state, _segment_started_at, _elapsed_before_segment

    _ensure_mixer()
    if _current_sound is None:
        raise RuntimeError("No audio has been loaded to restart")

    logger.info("Restarting audio: %s", _current_path)
    _response_channel.play(_current_sound)
    _elapsed_before_segment = 0.0
    _segment_started_at = time.monotonic()
    _state = "PLAYING"


def notify_user(path: Path, wait: bool = True) -> None:
    """Play a short notification clip on a separate channel.

    Runs independently of the response channel, so it never disturbs a
    paused response's position (used for please_wait.wav during
    interruptions).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    _ensure_mixer()
    sound = pygame.mixer.Sound(str(path))
    notification_channel = pygame.mixer.Channel(NOTIFICATION_CHANNEL_ID)

    logger.info("Playing notification audio: %s", path)
    notification_channel.play(sound)

    if wait:
        while notification_channel.get_busy():
            pygame.time.wait(50)
        logger.info("Finished notification audio: %s", path)


def get_state() -> str:
    """Return the response channel's tracked state: IDLE, PLAYING, or PAUSED."""
    return _state


def get_position_seconds() -> float:
    """Return elapsed playback time of the current response, excluding paused time."""
    elapsed = _elapsed_before_segment
    if _segment_started_at is not None:
        elapsed += time.monotonic() - _segment_started_at
    return elapsed
