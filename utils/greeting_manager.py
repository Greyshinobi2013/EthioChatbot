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

Mode B ordering is strictly per-user: (Greeting + Nod + Dialog) for
one user, completing in full, before the next user's greeting begins
-- never "all greetings, then all dialogs". PLAY_GREETINGS and
PLAY_USER_DIALOGS remain exactly the two FSM states STATE_MACHINE_V3.md
defines (no new states are introduced); Mode B simply revisits them
once per queued user instead of passing through each of them only
once. Each visit to PLAY_GREETINGS plays exactly one user's greeting
(_advance_greeting() is called without resetting _play_index between
users), then ALL_GREETINGS_FINISHED hands off to PLAY_USER_DIALOGS for
that same user's dialog; on completion, USER_DIALOGS_FINISHED carries a
"more_users_remaining" flag (see fsm.py's conditional resolution of
that event) that sends the FSM back to PLAY_GREETINGS for the next
user, or on to MONITORING once the queue is exhausted. Mode A is
unaffected: PLAY_GREETINGS still plays every queued user's greeting in
one visit before ALL_GREETINGS_FINISHED hands off to the single
PLAY_COMMON_DIALOG.

Greeting persistence needs no explicit "already greeted" clearing on
FACE_LOST: utils/face_presence_manager.py removes the ActiveUser
entry entirely on FACE_LOST, so a later re-sighting creates a fresh
entry with greeted=False by construction (see utils/state_manager.py).
The one deliberate exception is the operator-triggered RESTART_GREETINGS
event (Dashboard's "Restart Greetings" button, fsm.py's
(MONITORING, "RESTART_GREETINGS") and (PAUSED_DIALOG,
"RESTART_GREETINGS") -> GREETING_QUEUE transitions): _on_state_changed()
below explicitly clears every active user's greeted flag and re-sorts
them by priority first, so the full pipeline replays for everyone
still visible without requiring them to leave and return.

Per HEAD_MOTION_SPECIFICATION_V3.md, every greeting must be
accompanied by exactly one pitch-nod sequence. This module owns no
servo logic itself (utils/head_motion_controller.py does); it only
calls head_motion.greet_nod() alongside each greeting's play_audio(),
mirroring how it is the sole caller of utils/playback.py.
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
from utils.head_motion_controller import HeadMotionController
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
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        playback_service: PlaybackService,
        head_motion: Optional[HeadMotionController] = None,
    ) -> None:
        """Args:
            event_bus: Bus this manager subscribes to (STATE_CHANGED,
                PLAYBACK_FINISHED) and publishes control events on
                (SORTING_COMPLETE, QUEUE_READY, ALL_GREETINGS_FINISHED,
                COMMON_DIALOG_FINISHED, USER_DIALOGS_FINISHED).
            state_manager: Shared state read for active users and
                written for the greeting queue / greeted flags.
            playback_service: The sole audio playback controller.
            head_motion: Controller whose greet_nod() is called
                alongside each greeting's audio. Optional so this
                manager remains usable without head-motion hardware
                wired up.
        """
        self._bus = event_bus
        self._state = state_manager
        self._playback = playback_service
        self._head_motion = head_motion

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
            if trigger_event == "RESTART_GREETINGS":
                # Operator-triggered replay, fired from MONITORING or
                # PAUSED_DIALOG (fsm.py's only two valid source states,
                # per STATE_MACHINE_V3.md): stop whatever audio is
                # currently loaded first -- a manual stop_audio(), not
                # a natural finish, so it does not publish
                # PLAYBACK_FINISHED and cannot race with
                # _on_playback_finished below. _phase is cleared too, so
                # a PLAYBACK_FINISHED that was already in flight before
                # the stop lands is a no-op instead of double-advancing.
                self._playback.stop_audio()
                self._phase = None
                # Force every currently active user back through the
                # pipeline by clearing their greeted flag, rather than
                # touching face presence/recognition state at all, then
                # re-sort them by priority -- this transition bypasses
                # PRIORITY_SORTING as a distinct FSM state, so sorting
                # has to happen here instead of _handle_priority_sorting().
                self._state.clear_all_greeted()
                active_users = self._state.get_active_users()
                self._sorted_users = sort_by_priority(active_users)
                logger.info(
                    "RESTART_GREETINGS: playback stopped, greeted flags cleared, queue rebuilt: %s",
                    [user.user_id for user in self._sorted_users],
                )
            self._handle_greeting_queue()
        elif to_state == PLAY_GREETINGS:
            if trigger_event == "USER_DIALOGS_FINISHED":
                # Mode B: moving on to the next queued user's greeting.
                # _play_index already points at them (left there by the
                # previous cycle's _advance_greeting() call) -- do not
                # reset it, unlike a fresh _start_greetings().
                self._play_current_greeting()
            else:
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
            if self._state.get_interaction_mode() == "user_specific_dialog":
                # Mode B: exactly one greeting per PLAY_GREETINGS visit
                # -- hand off to that same user's dialog now, rather
                # than playing the next queued user's greeting here.
                self._phase = None
                self._bus.publish("ALL_GREETINGS_FINISHED", {})
            elif not self._advance_greeting():
                self._phase = None
                self._bus.publish("ALL_GREETINGS_FINISHED", {})
        elif self._phase == _PHASE_USER_DIALOG:
            self._finish_user_dialog_phase()
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
        self._play_current_greeting()

    def _play_current_greeting(self) -> None:
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
                # Per HEAD_MOTION_SPECIFICATION_V3.md: one nod sequence
                # per greeting, starting together with the greeting
                # audio. greet_nod() runs on its own thread and does
                # not block this one.
                if self._head_motion is not None:
                    self._head_motion.greet_nod()
                return True
            logger.error("Missing or unplayable greeting audio for %s: %s", user.user_id, path)
        return False

    # -- Mode B: per-user dialogs --------------------------------------------

    def _start_user_dialogs(self) -> None:
        """Play the dialog for whichever user's greeting just played.

        _play_index already points one past that user -- it was
        advanced by _advance_greeting() during the PLAY_GREETINGS visit
        that immediately preceded this one, and Mode B never resets it
        between phases (each visit to PLAY_GREETINGS/PLAY_USER_DIALOGS
        here covers exactly one user).
        """
        self._phase = _PHASE_USER_DIALOG
        if not self._advance_user_dialog():
            self._finish_user_dialog_phase()

    def _advance_user_dialog(self) -> bool:
        if not (0 < self._play_index <= len(self._queue)):
            return False
        user = self._queue[self._play_index - 1]
        path = AUDIO_ROOT / user.preferred_language / "dialogs" / f"{user.user_id}.wav"
        if self._try_play(path):
            return True
        logger.error("Missing or unplayable dialog audio for %s: %s", user.user_id, path)
        return False

    def _finish_user_dialog_phase(self) -> None:
        self._phase = None
        more_users_remaining = self._play_index < len(self._queue)
        self._bus.publish("USER_DIALOGS_FINISHED", {"more_users_remaining": more_users_remaining})

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
