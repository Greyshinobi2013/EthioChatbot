"""Finite State Machine for EthioChatbot V3.

Implements the 10-state machine defined in STATE_MACHINE_V3.md exactly:
no states are skipped, merged, or invented. Per that document's State
Transition Rules, the FSM is the sole authority for state transitions
-- every transition is validated against a fixed transition graph,
rejected and logged if invalid, applied and logged (plus a published
STATE_CHANGED event) if valid. No other component may set
StateManager's current_state directly (DEVELOPMENT_RULES_V3.md Rule 19).

Three transitions are not simple (state, event) -> state lookups, per
STATE_MACHINE_V3.md itself:

- PLAY_GREETINGS + ALL_GREETINGS_FINISHED branches on the configured
  interaction_mode (read from StateManager): PLAY_COMMON_DIALOG for
  "common_dialog" (Mode A), PLAY_USER_DIALOGS for "user_specific_dialog"
  (Mode B).
- PAUSED_DIALOG + RESUME_DIALOG returns to whichever dialog state the
  system was interrupted from. The FSM remembers this as
  ``_paused_from``, set whenever INTERRUPT_DIALOG is applied.
- PLAY_USER_DIALOGS + USER_DIALOGS_FINISHED branches on the triggering
  event's own payload (``more_users_remaining``): Mode B processes its
  queue one user at a time -- greeting+nod, then that same user's
  dialog, only then the next user's greeting -- by cycling back to
  PLAY_GREETINGS instead of going to MONITORING once every queued user
  has been through both states. greeting_manager.py (the only
  publisher of this event) sets the flag; the FSM only reads it.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Set, Tuple

from utils.event_bus import Event, EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

FACE_DETECTION_MODE = "FACE_DETECTION_MODE"
FACE_DETECTED = "FACE_DETECTED"
FACE_RECOGNIZED = "FACE_RECOGNIZED"
PRIORITY_SORTING = "PRIORITY_SORTING"
GREETING_QUEUE = "GREETING_QUEUE"
PLAY_GREETINGS = "PLAY_GREETINGS"
PLAY_COMMON_DIALOG = "PLAY_COMMON_DIALOG"
PLAY_USER_DIALOGS = "PLAY_USER_DIALOGS"
PAUSED_DIALOG = "PAUSED_DIALOG"
MONITORING = "MONITORING"

STATES: FrozenSet[str] = frozenset(
    {
        FACE_DETECTION_MODE,
        FACE_DETECTED,
        FACE_RECOGNIZED,
        PRIORITY_SORTING,
        GREETING_QUEUE,
        PLAY_GREETINGS,
        PLAY_COMMON_DIALOG,
        PLAY_USER_DIALOGS,
        PAUSED_DIALOG,
        MONITORING,
    }
)

# (current_state, triggering_event) -> next_state, for every transition
# that has a single fixed target. The two conditional transitions
# (ALL_GREETINGS_FINISHED, RESUME_DIALOG) are resolved dynamically in
# _on_event/_resolve instead of appearing here.
_TRANSITIONS: Dict[Tuple[str, str], str] = {
    (FACE_DETECTION_MODE, "FACE_DETECTED"): FACE_DETECTED,
    (FACE_DETECTED, "FACE_RECOGNIZED"): FACE_RECOGNIZED,
    (FACE_DETECTED, "NO_FACE_FOUND"): FACE_DETECTION_MODE,
    (FACE_RECOGNIZED, "RECOGNITION_COMPLETE"): PRIORITY_SORTING,
    (PRIORITY_SORTING, "SORTING_COMPLETE"): GREETING_QUEUE,
    (GREETING_QUEUE, "QUEUE_READY"): PLAY_GREETINGS,
    (PLAY_COMMON_DIALOG, "COMMON_DIALOG_FINISHED"): MONITORING,
    (PLAY_COMMON_DIALOG, "INTERRUPT_DIALOG"): PAUSED_DIALOG,
    (PLAY_USER_DIALOGS, "INTERRUPT_DIALOG"): PAUSED_DIALOG,
    (MONITORING, "NEW_USER_DETECTED"): FACE_RECOGNIZED,
    (MONITORING, "FACE_LOST"): MONITORING,
    (MONITORING, "ALL_USERS_LOST"): FACE_DETECTION_MODE,
    # Operator-triggered replay (Dashboard's "Restart Greetings" button).
    # Per STATE_MACHINE_V3.md's MONITORING and PAUSED_DIALOG "Allowed
    # Events" sections, this is valid from exactly these two states and
    # goes directly to GREETING_QUEUE (skipping PRIORITY_SORTING as a
    # distinct FSM state): greeting_manager.py detects this trigger
    # event on arrival at GREETING_QUEUE, stops whatever dialog audio is
    # currently playing or paused, clears greeted flags for currently-
    # active users, and re-sorts them by priority itself before building
    # the queue, so the normal GREETING_QUEUE -> PLAY_GREETINGS -> dialog
    # -> MONITORING pipeline replays for everyone still visible.
    (MONITORING, "RESTART_GREETINGS"): GREETING_QUEUE,
    (PAUSED_DIALOG, "RESTART_GREETINGS"): GREETING_QUEUE,
}

# Extra (from_state -> possible next states) entries for the three
# conditionally-resolved transitions, unioned into the adjacency map
# used to validate requested transitions.
_CONDITIONAL_TARGETS: Dict[str, Set[str]] = {
    PLAY_GREETINGS: {PLAY_COMMON_DIALOG, PLAY_USER_DIALOGS},
    PAUSED_DIALOG: {PLAY_COMMON_DIALOG, PLAY_USER_DIALOGS},
    PLAY_USER_DIALOGS: {PLAY_GREETINGS, MONITORING},
}


def _build_allowed_next() -> Dict[str, Set[str]]:
    """Derive the (from_state -> {valid next states}) adjacency map."""
    allowed: Dict[str, Set[str]] = {state: set() for state in STATES}
    for (from_state, _event_name), to_state in _TRANSITIONS.items():
        allowed[from_state].add(to_state)
    for from_state, targets in _CONDITIONAL_TARGETS.items():
        allowed[from_state].update(targets)
    return allowed


_ALLOWED_NEXT: Dict[str, Set[str]] = _build_allowed_next()

_SUBSCRIBED_EVENTS: Set[str] = {event_name for (_from_state, event_name) in _TRANSITIONS} | {
    "ALL_GREETINGS_FINISHED",
    "RESUME_DIALOG",
    "USER_DIALOGS_FINISHED",
}


class FiniteStateMachine:
    """The authoritative controller of system state, per STATE_MACHINE_V3.md.

    Subscribes to every event named in the transition table and drives
    state changes on the shared StateManager accordingly. Publishes
    STATE_CHANGED after every applied transition. Performs no
    recognition, playback, UI, or camera logic itself.
    """

    def __init__(self, event_bus: EventBus, state_manager: StateManager) -> None:
        """Args:
            event_bus: Bus to subscribe transition-triggering events on
                and publish STATE_CHANGED to.
            state_manager: Shared state store this FSM owns
                current_state for, and reads interaction_mode from to
                resolve the Mode A/B branch.
        """
        self._bus = event_bus
        self._state = state_manager
        self._paused_from: Optional[str] = None

        for event_name in _SUBSCRIBED_EVENTS:
            self._bus.subscribe(event_name, self._on_event)

        logger.info(
            "FSM initialized: current_state=%s, %d states, %d transitions",
            self.current_state,
            len(STATES),
            len(_TRANSITIONS),
        )

    @property
    def current_state(self) -> str:
        """The FSM's current state, read from the shared StateManager."""
        return self._state.current_state

    def _on_event(self, event: Event) -> None:
        """Bus callback: resolve and apply the transition for this event, if any."""
        target_state = self._resolve(event)
        if target_state is None:
            logger.debug(
                "Event %s ignored: no transition defined from state %s",
                event.name,
                self.current_state,
            )
            return

        if event.name == "INTERRUPT_DIALOG":
            # Remember where to return to on RESUME_DIALOG.
            self._paused_from = self.current_state
        elif event.name == "RESTART_GREETINGS":
            # A restart discards whatever pause was in effect -- RESUME_DIALOG
            # must not resurrect a dialog that's about to be replayed from
            # scratch.
            self._paused_from = None

        self.request_transition(target_state, event.name)

    def _resolve(self, event: Event) -> Optional[str]:
        """Resolve event against the current state, handling the three conditional branches."""
        event_name = event.name

        if event_name == "ALL_GREETINGS_FINISHED":
            if self.current_state != PLAY_GREETINGS:
                return None
            mode = self._state.get_interaction_mode()
            return PLAY_USER_DIALOGS if mode == "user_specific_dialog" else PLAY_COMMON_DIALOG

        if event_name == "RESUME_DIALOG":
            if self.current_state != PAUSED_DIALOG:
                return None
            return self._paused_from or PLAY_COMMON_DIALOG

        if event_name == "USER_DIALOGS_FINISHED":
            if self.current_state != PLAY_USER_DIALOGS:
                return None
            return PLAY_GREETINGS if event.payload.get("more_users_remaining") else MONITORING

        return _TRANSITIONS.get((self.current_state, event_name))

    def request_transition(self, to_state: str, event_name: str = "MANUAL") -> bool:
        """Attempt to transition to to_state, validating against the FSM graph.

        Args:
            to_state: Desired next state.
            event_name: Name of the event or reason driving this
                request, recorded in the log and on STATE_CHANGED.

        Returns:
            True if the transition was valid and applied, False if it
            was rejected as invalid.

        Raises:
            ValueError: if to_state is not one of the 10 recognized states.
        """
        if to_state not in STATES:
            raise ValueError(f"Unknown state: {to_state}")

        from_state = self.current_state

        if to_state not in _ALLOWED_NEXT.get(from_state, set()):
            logger.warning(
                "STATE_TRANSITION_REJECTED: %s -> %s (event=%s) is not a valid transition",
                from_state,
                to_state,
                event_name,
            )
            return False

        self._state.set_current_state(to_state)
        logger.info(
            "STATE_TRANSITION: %s -> %s (event=%s)",
            from_state,
            to_state,
            event_name,
        )
        self._bus.publish("STATE_CHANGED", {"from": from_state, "to": to_state, "event": event_name})
        return True
