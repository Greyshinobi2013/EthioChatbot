"""Conversation lifecycle orchestration for EthioChatbot V2.

Coordinates the CONVERSATION_ACTIVE workflow across the services built
in Milestones 6-9: establishes and clears language context around
wake-word activation and timeout (ARCHITECTURE.md's Language Context
Architecture), bridges utils/scenario_engine.py's match results to
utils/playback.py (neither of those two modules talks to the other
directly), and enforces the 30-second conversation timeout from
README.md.

Speech recognition, VAD, scenario matching, and playback are each
already event-driven and self-contained (Milestones 6-9); this module
does not duplicate their logic, only coordinates the handoffs between
them and owns the timeout clock, matching this milestone's explicit
scope: language context, scenario matching coordination, playback
coordination, timeout handling. Greeting logic stays owned by
utils/greeting_service.py (Milestone 5).

Continuous microphone capture and the "detect end of a spoken
question, then transcribe it" loop that would publish TRANSCRIPTION_READY
during a live conversation are not built by any scheduled milestone
(README's utils/audio_service.py is never assigned its own milestone);
this module reacts correctly to TRANSCRIPTION_READY whenever it is
published, but does not itself produce it.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional

from utils.event_bus import Event, EventBus
from utils.fsm import CONVERSATION_ACTIVE
from utils.logger import get_logger
from utils.playback import PlaybackService
from utils.state_manager import StateManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TIMEOUT_SECONDS = 30  # matches config/settings.json's conversation_timeout
DEFAULT_POLL_INTERVAL_SECONDS = 0.2


class ConversationManager:
    """Orchestrates conversation language context, response playback, and timeout.

    Implements app.py's Service protocol (name, start, stop).
    """

    name = "conversation_manager"

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        playback_service: PlaybackService,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        """Args:
            event_bus: Bus this manager reacts to and publishes on.
            state_manager: Shared state for current_language,
                current_state, and active_users (used for the
                preferred-language fallback tier).
            playback_service: Used to play matched/fallback scenario
                response audio.
            timeout_seconds: Seconds of inactivity before
                TIMEOUT_OCCURRED fires. README recommends 30.
            poll_interval_seconds: How often the timeout watcher
                checks elapsed inactivity.
        """
        self._bus = event_bus
        self._state = state_manager
        self._playback = playback_service
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds

        self._lock = threading.RLock()
        self._active = False
        self._last_activity_at: Optional[float] = None

        self._watcher_stop = threading.Event()
        self._watcher_thread: Optional[threading.Thread] = None

        self._bus.subscribe("WAKE_WORD_DETECTED", self._on_wake_word_detected)
        self._bus.subscribe("SCENARIO_MATCHED", self._on_scenario_matched)
        self._bus.subscribe("FALLBACK_SCENARIO_SELECTED", self._on_fallback_selected)
        # PLAYBACK_FINISHED marks the end of one conversational turn,
        # giving a fresh timeout window for the user's next question
        # rather than letting the clock drain during response playback.
        for event_name in ("TRANSCRIPTION_READY", "INTERRUPTION_DETECTED", "PLAYBACK_FINISHED"):
            self._bus.subscribe(event_name, self._on_activity)

    def start(self) -> None:
        """Start the timeout watcher thread."""
        self._watcher_stop.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_for_timeout, name="ConversationTimeoutThread", daemon=True
        )
        self._watcher_thread.start()
        logger.info("Conversation manager started (timeout=%ds)", self._timeout_seconds)

    def stop(self) -> None:
        """Stop the timeout watcher thread."""
        self._watcher_stop.set()
        if self._watcher_thread is not None:
            self._watcher_thread.join(timeout=5.0)
            self._watcher_thread = None
        logger.info("Conversation manager stopped")

    @property
    def is_active(self) -> bool:
        """Whether a conversation session is currently in progress."""
        with self._lock:
            return self._active

    def _on_wake_word_detected(self, event: Event) -> None:
        """Establish language context and start a conversation session.

        Language priority, per README's Language Selection Rule:
        1. Wake word language (from the event payload; always present
           in practice, since WhisperService only publishes this event
           after a definitive wake-word match in a specific language).
        2. The highest-priority active user's preferred_language.
        3. English.
        """
        wake_word_language = event.payload.get("language")
        language = wake_word_language or self._preferred_language_fallback() or "english"

        self._state.set_current_language(language)
        self._bus.publish("LANGUAGE_CONTEXT_SET", {"language": language})

        with self._lock:
            self._active = True
            self._last_activity_at = time.time()

        logger.info("Conversation started: language=%s", language)
        self._bus.publish("CONVERSATION_STARTED", {"language": language})

    def _preferred_language_fallback(self) -> Optional[str]:
        """Return the highest-priority active user's preferred_language, if any."""
        active_users = self._state.get_active_users()
        if not active_users:
            return None
        top_user = min(active_users.values(), key=lambda user: user.priority)
        return top_user.preferred_language

    def _on_activity(self, event: Event) -> None:
        """Reset the inactivity clock on any sign of ongoing conversation."""
        with self._lock:
            if self._active:
                self._last_activity_at = time.time()

    def _on_scenario_matched(self, event: Event) -> None:
        self._on_activity(event)
        audio_file = event.payload.get("audio_file")
        if audio_file:
            self._play_response(audio_file)

    def _on_fallback_selected(self, event: Event) -> None:
        self._on_activity(event)
        audio_file = event.payload.get("audio_file")
        if audio_file:
            self._play_response(audio_file)

    def _play_response(self, relative_audio_path: str) -> None:
        """Play a scenario response, bridging scenario_engine.py's output to playback.py."""
        audio_path = PROJECT_ROOT / relative_audio_path
        try:
            self._playback.play_audio(audio_path)
        except Exception:
            logger.exception("Failed to play scenario response audio: %s", audio_path)

    def _watch_for_timeout(self) -> None:
        """Poll elapsed inactivity and fire the timeout once it exceeds the threshold.

        Gated on the FSM currently being in CONVERSATION_ACTIVE (read
        via state_manager.current_state, which the FSM owns): if a
        response is still playing (PLAYING_AUDIO/INTERRUPTED) when the
        threshold is reached, this waits until control genuinely
        returns to CONVERSATION_ACTIVE before firing, matching
        STATE_MACHINE.md's Timeout Workflow, which only exits
        CONVERSATION_ACTIVE.
        """
        while not self._watcher_stop.is_set():
            with self._lock:
                active = self._active
                last_activity = self._last_activity_at

            if active and last_activity is not None:
                elapsed = time.time() - last_activity
                if elapsed >= self._timeout_seconds and self._state.current_state == CONVERSATION_ACTIVE:
                    self._handle_timeout()

            time.sleep(self._poll_interval_seconds)

    def _handle_timeout(self) -> None:
        """Fire TIMEOUT_OCCURRED, then clear language context."""
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._last_activity_at = None

        logger.info("Conversation timeout after %ds of inactivity", self._timeout_seconds)
        self._bus.publish("TIMEOUT_OCCURRED", {"timeout_seconds": self._timeout_seconds})

        self._state.set_current_language(None)
        self._bus.publish("LANGUAGE_CONTEXT_CLEARED", {})

        self._bus.publish("CONVERSATION_ENDED", {})
