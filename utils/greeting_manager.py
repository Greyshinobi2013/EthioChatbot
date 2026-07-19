"""Greeting and dialog playback orchestration for EthioChatbot V3.

Per SYSTEM_ARCHITECTURE_V3.md's Greeting Manager responsibilities:
greeting queue generation, greeting ordering, interaction mode
handling, and greeting persistence. This module is the sole caller of
utils/playback.py (DEVELOPMENT_RULES_V3.md Rule 18: PlaybackService is
the only component allowed to control audio) and drives every FSM
transition from PRIORITY_SORTING through MONITORING by reacting to
STATE_CHANGED and PLAYBACK_FINISHED events -- it contains no state
transition logic of its own (fsm.py owns validating/applying
transitions; this module only decides *when* to publish the event
that requests one).

Mode A vs Mode B ordering: PROJECT_SPECIFICATION_V3.md's illustrative
Mode B diagrams show each user's greeting immediately followed by
their own dialog (interleaved). STATE_MACHINE_V3.md -- authoritative
for FSM behavior per DEVELOPMENT_RULES_V3.md Rule 19/CLAUDE.md's FSM
Rules -- instead defines PLAY_GREETINGS and PLAY_USER_DIALOGS as two
separate, sequential states, with PLAY_GREETINGS's own description
covering "all users in queue". This module follows the state machine
literally: every queued user's greeting plays first (priority order),
then every queued user's dialog plays (same order), rather than
interleaving -- both orders produce every user hearing their greeting
and their dialog exactly once, in priority order, so nothing in
ACCEPTANCE_TESTS_V3.md distinguishes between them.

Greeting persistence needs no explicit "already greeted" clearing on
FACE_LOST: utils/face_presence_manager.py removes the ActiveUser
entry entirely on FACE_LOST, so a later re-sighting creates a fresh
entry with greeted=False by construction (see utils/state_manager.py).
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import List, Optional

from utils.event_bus import Event, EventBus
from utils.fsm import (
    GREETING_QUEUE,
    PAUSED_DIALOG,
    PLAY_COMMON_DIALOG,
    PLAY_GREETINGS,
    PLAY_USER_DIALOGS,
    PRIORITY_SORTING,
)
from utils.logger import get_logger
from utils.playback import PlaybackError, PlaybackService
from utils.priority_manager import sort_by_priority
from utils.state_manager import ActiveUser, StateManager

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIO_ROOT = PROJECT_ROOT / "audio"

_PHASE_GREETING = "greeting"
_PHASE_USER_DIALOG = "user_dialog"
_PHASE_COMMON_DIALOG = "common_dialog"


class GreetingManager:
    """Builds the greeting queue and drives greeting/dialog playback."""

    def __init__(
        self, event_bus: EventBus, state_manager: StateManager, playback_service: PlaybackService
    ) -> None:
        """Args:
            event_bus: Bus this manager subscribes to (STATE_CHANGED,
                PLAYBACK_FINISHED) and publishes control events on
                (SORTING_COMPLETE, QUEUE_READY, ALL_GREETINGS_FINISHED,
                COMMON_DIALOG_FINISHED, USER_DIALOGS_FINISHED).
            state_manager: Shared state read for active users and
                written for the greeting queue / greeted flags.
            playback_service: The sole audio playback controller.
        """
        self._bus = event_bus
        self._state = state_manager
        self._playback = playback_service

        self._sorted_users: List[ActiveUser] = []
        self._queue: List[ActiveUser] = []
        self._play_index = 0
        self._phase: Optional[str] = None

        self._bus.subscribe("STATE_CHANGED", self._on_state_changed)
        self._bus.subscribe("PLAYBACK_FINISHED", self._on_playback_finished)

    # -- FSM-driven orchestration ---------------------------------------

    def _on_state_changed(self, event: Event) -> None:
        to_state = event.payload.get("to")
        trigger_event = event.payload.get("event")

        if to_state == PRIORITY_SORTING:
            self._handle_priority_sorting()
        elif to_state == GREETING_QUEUE:
            self._handle_greeting_queue()
        elif to_state == PLAY_GREETINGS:
            self._start_greetings()
        elif to_state == PLAY_COMMON_DIALOG:
            if trigger_event == "RESUME_DIALOG":
                self._playback.resume_audio()
            else:
                self._start_common_dialog()
        elif to_state == PLAY_USER_DIALOGS:
            if trigger_event == "RESUME_DIALOG":
                self._playback.resume_audio()
            else:
                self._start_user_dialogs()
        elif to_state == PAUSED_DIALOG:
            self._playback.pause_audio()

    def _on_playback_finished(self, event: Event) -> None:
        # PlaybackService's watcher thread publishes this event on its
        # own background thread and then exits. Calling play_audio()
        # again inline here would make that same thread join itself
        # inside PlaybackService's internal watcher-stop logic
        # (harmless but a needless multi-second stall each time), so
        # the continuation is handed off to a fresh thread instead.
        threading.Thread(target=self._advance_after_playback, daemon=True).start()

    def _advance_after_playback(self) -> None:
        if self._phase == _PHASE_GREETING:
            if not self._advance_greeting():
                self._phase = None
                self._bus.publish("ALL_GREETINGS_FINISHED", {})
        elif self._phase == _PHASE_USER_DIALOG:
            if not self._advance_user_dialog():
                self._phase = None
                self._bus.publish("USER_DIALOGS_FINISHED", {})
        elif self._phase == _PHASE_COMMON_DIALOG:
            self._phase = None
            self._bus.publish("COMMON_DIALOG_FINISHED", {})

    # -- Queue construction -----------------------------------------------

    def _handle_priority_sorting(self) -> None:
        active_users = self._state.get_active_users()
        self._sorted_users = sort_by_priority(active_users)
        logger.info("PRIORITY_SORTING complete: %s", [user.user_id for user in self._sorted_users])
        self._bus.publish("SORTING_COMPLETE", {"order": [user.user_id for user in self._sorted_users]})

    def _handle_greeting_queue(self) -> None:
        # Greeting persistence: only users not already greeted this
        # presence session are queued.
        queue = [user for user in self._sorted_users if not user.greeted]
        for user in queue:
            self._state.mark_greeted(user.user_id)

        self._queue = queue
        self._state.set_greeting_queue([user.user_id for user in queue])
        logger.info("GREETING_QUEUE built: %s", [user.user_id for user in queue])
        self._bus.publish("QUEUE_READY", {"queue": [user.user_id for user in queue]})

    # -- Greeting playback --------------------------------------------------

    def _start_greetings(self) -> None:
        self._play_index = 0
        self._phase = _PHASE_GREETING
        if not self._advance_greeting():
            self._phase = None
            self._bus.publish("ALL_GREETINGS_FINISHED", {})

    def _advance_greeting(self) -> bool:
        while self._play_index < len(self._queue):
            user = self._queue[self._play_index]
            self._play_index += 1
            path = AUDIO_ROOT / user.preferred_language / "greetings" / f"{user.user_id}.wav"
            if self._try_play(path):
                return True
            logger.error("Missing or unplayable greeting audio for %s: %s", user.user_id, path)
        return False

    # -- Mode B: per-user dialogs --------------------------------------------

    def _start_user_dialogs(self) -> None:
        self._play_index = 0
        self._phase = _PHASE_USER_DIALOG
        if not self._advance_user_dialog():
            self._phase = None
            self._bus.publish("USER_DIALOGS_FINISHED", {})

    def _advance_user_dialog(self) -> bool:
        while self._play_index < len(self._queue):
            user = self._queue[self._play_index]
            self._play_index += 1
            path = AUDIO_ROOT / user.preferred_language / "dialogs" / f"{user.user_id}.wav"
            if self._try_play(path):
                return True
            logger.error("Missing or unplayable dialog audio for %s: %s", user.user_id, path)
        return False

    # -- Mode A: common dialog -----------------------------------------------

    def _start_common_dialog(self) -> None:
        self._phase = _PHASE_COMMON_DIALOG
        # No single language applies to a mixed-language queue; the
        # highest-priority queued user's language is used for the one
        # shared dialog. Falls back to English if the queue is somehow
        # empty (e.g. a fresh pipeline run whose sole new arrival left
        # again before greetings started).
        language = self._queue[0].preferred_language if self._queue else "english"
        path = AUDIO_ROOT / language / "dialogs" / "common_dialog.wav"
        if not self._try_play(path):
            logger.error("Missing or unplayable common dialog audio: %s", path)
            self._phase = None
            self._bus.publish("COMMON_DIALOG_FINISHED", {})

    # -- Shared playback helper -----------------------------------------------

    def _try_play(self, path: Path) -> bool:
        """Attempt to play path, logging and returning False on any failure.

        Per AUDIO_STRUCTURE_V3.md's Missing Audio Behavior: a missing
        or unplayable file must never crash the system.
        """
        try:
            self._playback.play_audio(path)
            return True
        except PlaybackError as exc:
            logger.error("Playback error for %s: %s", path, exc)
            return False
