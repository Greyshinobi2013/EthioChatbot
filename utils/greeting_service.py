"""Priority-based sequential greeting service for EthioChatbot V2.

Implements the Milestone 5 workflow: Recognize Users -> Sort By
Priority -> Greeting Queue -> Sequential Playback -> WAITING_FOR_WAKE_WORD.

Reacts to the FSM entering PRIORITY_SORTING (reached via
camera_service's MULTIPLE_USERS_RECOGNIZED event, per the Milestone 2
transition table): sorts the currently active users by priority,
publishes PRIORITY_LIST_READY (which the FSM's own subscription
advances to GREETING), plays each user's personalized greeting
sequentially, then publishes GREETING_FINISHED (which the FSM
advances to WAITING_FOR_WAKE_WORD).

Per README.md and ARCHITECTURE.md, greetings are always English and
are never interrupted (STATE_MACHINE.md marks GREETING -> INTERRUPTED
as an invalid transition), so this module uses a minimal blocking WAV
player rather than the full interruptible/resumable playback engine
that utils/playback.py (Milestone 8) will provide for scenario
responses.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

import pygame

from utils.event_bus import Event, EventBus
from utils.logger import get_logger
from utils.state_manager import ActiveUser, StateManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GREETINGS_DIR = PROJECT_ROOT / "audio" / "english" / "greetings"
DEFAULT_FALLBACK_AUDIO_PATH = PROJECT_ROOT / "audio" / "english" / "greeting.wav"


def _play_wav_blocking(path: Path) -> None:
    """Play a WAV file to completion, blocking the calling thread.

    Minimal playback used only for greetings, which are never
    interrupted. The full interruptible, position-tracking playback
    engine for scenario responses is utils/playback.py (Milestone 8).

    Args:
        path: Path to a WAV file. If it does not exist, this logs an
            error and returns without playing anything, so a missing
            asset cannot hang the greeting sequence.
    """
    if not path.exists():
        logger.error("Greeting audio file not found: %s", path)
        return

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    sound = pygame.mixer.Sound(str(path))
    channel = sound.play()
    while channel is not None and channel.get_busy():
        time.sleep(0.02)


class GreetingService:
    """Sorts active users by priority and plays their greetings sequentially.

    Implements app.py's Service protocol (name, start, stop). Greeting
    playback runs on its own dedicated thread so the (synchronous)
    event dispatch that triggers it -- typically running on the
    camera thread -- never blocks on audio playback, per EVENTS.md's
    "events should complete quickly" rule.
    """

    name = "greeting_service"

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        greetings_dir: Path = DEFAULT_GREETINGS_DIR,
        fallback_audio_path: Path = DEFAULT_FALLBACK_AUDIO_PATH,
    ) -> None:
        """Args:
            event_bus: Bus to react to STATE_CHANGED on and publish
                PRIORITY_LIST_READY/GREETING_STARTED/USER_GREETING_STARTED/
                USER_GREETING_FINISHED/GREETING_FINISHED to.
            state_manager: Shared state to read active_users from.
            greetings_dir: Directory containing personalized greeting
                WAV files named "<user_id>.wav".
            fallback_audio_path: Greeting WAV used when a user has no
                personalized file (missing or a 0-byte placeholder).
        """
        self._bus = event_bus
        self._state = state_manager
        self._greetings_dir = Path(greetings_dir)
        self._fallback_audio_path = Path(fallback_audio_path)

        self._trigger = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._bus.subscribe("STATE_CHANGED", self._on_state_changed)

    def start(self) -> None:
        """Start the dedicated greeting thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="GreetingThread", daemon=True)
        self._thread.start()
        logger.info("Greeting service started")

    def stop(self) -> None:
        """Stop the greeting thread, letting any in-progress cycle finish its current file."""
        self._stop_event.set()
        self._trigger.set()
        if self._thread is not None:
            self._thread.join(timeout=10.0)
            self._thread = None
        logger.info("Greeting service stopped")

    def _on_state_changed(self, event: Event) -> None:
        """Wake the greeting thread whenever the FSM enters PRIORITY_SORTING."""
        if event.payload.get("to") == "PRIORITY_SORTING":
            self._trigger.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            woke = self._trigger.wait(timeout=0.5)
            if not woke:
                continue
            self._trigger.clear()
            if self._stop_event.is_set():
                break
            self.run_greeting_cycle()

    def run_greeting_cycle(self) -> None:
        """Sort active users by priority and play their greetings sequentially.

        Exposed as a public method, separate from the trigger loop, so
        it can be exercised directly in tests without waiting on
        STATE_CHANGED events.
        """
        active_users = self._state.get_active_users()
        if not active_users:
            logger.warning("Entered PRIORITY_SORTING with no active users; nothing to greet")
            return

        queue = sorted(active_users.values(), key=lambda user: user.priority)
        logger.info("Greeting queue built (priority order): %s", [user.user_id for user in queue])

        self._bus.publish(
            "PRIORITY_LIST_READY",
            {"users": [{"user_id": user.user_id, "priority": user.priority} for user in queue]},
        )

        self._bus.publish("GREETING_STARTED", {})
        for user in queue:
            if self._stop_event.is_set():
                break
            self._greet_user(user)

        self._bus.publish("GREETING_FINISHED", {})

    def _greet_user(self, user: ActiveUser) -> None:
        audio_path = self._resolve_greeting_audio(user.user_id)
        self._bus.publish("USER_GREETING_STARTED", {"user_id": user.user_id})
        logger.info("Greeting %s with %s", user.user_id, audio_path)
        _play_wav_blocking(audio_path)
        self._bus.publish("USER_GREETING_FINISHED", {"user_id": user.user_id})

    def _resolve_greeting_audio(self, user_id: str) -> Path:
        """Return the personalized greeting for user_id, or the fallback.

        A candidate file that is missing or a 0-byte placeholder (as
        audio/english/greetings/*.wav currently are, pending real
        recordings) is treated as absent.
        """
        candidate = self._greetings_dir / f"{user_id}.wav"
        if candidate.exists() and candidate.stat().st_size > 0:
            return candidate
        logger.warning(
            "No personalized greeting audio for %s at %s; using fallback %s",
            user_id,
            candidate,
            self._fallback_audio_path,
        )
        return self._fallback_audio_path
