"""Finite State Machine for EthioChatbot V2.

Implements the 12-state machine defined in STATE_MACHINE.md. Per that
document's Principle 4, the FSM is the sole authority for state
transitions: every transition is validated against a fixed transition
graph, rejected and logged if invalid (Principle 2), and logged if
applied (Principle 3). No other component may set StateManager's
current_state directly.

Transition table sources and documented gap-fills
---------------------------------------------------
The table below is built from STATE_MACHINE.md's State Transition
Diagram plus its Event Ownership table, using the authoritative event
names from EVENTS.md (ALL_USERS_LOST, IDLE_ENTERED) in place of
STATE_MACHINE.md's inconsistent NO_ACTIVE_USERS / RETURN_TO_IDLE_COMPLETE.

Two transitions have no single named event in either source document
and are filled in deliberately:

- (TIMEOUT, LANGUAGE_CONTEXT_CLEARED) -> FACE_LOST_CHECK: TIMEOUT's
  documented exit condition is only "Determine next state," with no
  named event. LANGUAGE_CONTEXT_CLEARED ("Prepare wake-word state")
  is the closest cataloged event describing this exact moment, so it
  is used as the trigger.
- (FACE_LOST_CHECK, FACE_LOST_CHECK_PASSED) -> WAITING_FOR_WAKE_WORD:
  EVENTS.md only names ALL_USERS_LOST for the "no users remain"
  outcome of FACE_LOST_CHECK; there is no cataloged event for the
  "users remain" outcome. FACE_LOST_CHECK_PASSED is introduced here
  as the event a future presence check publishes for that outcome.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Set, Tuple

from utils.event_bus import Event, EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

IDLE = "IDLE"
FACE_DETECTED = "FACE_DETECTED"
FACE_RECOGNIZED = "FACE_RECOGNIZED"
PRIORITY_SORTING = "PRIORITY_SORTING"
GREETING = "GREETING"
WAITING_FOR_WAKE_WORD = "WAITING_FOR_WAKE_WORD"
CONVERSATION_ACTIVE = "CONVERSATION_ACTIVE"
PLAYING_AUDIO = "PLAYING_AUDIO"
INTERRUPTED = "INTERRUPTED"
TIMEOUT = "TIMEOUT"
FACE_LOST_CHECK = "FACE_LOST_CHECK"
RETURN_TO_IDLE = "RETURN_TO_IDLE"

STATES: FrozenSet[str] = frozenset(
    {
        IDLE,
        FACE_DETECTED,
        FACE_RECOGNIZED,
        PRIORITY_SORTING,
        GREETING,
        WAITING_FOR_WAKE_WORD,
        CONVERSATION_ACTIVE,
        PLAYING_AUDIO,
        INTERRUPTED,
        TIMEOUT,
        FACE_LOST_CHECK,
        RETURN_TO_IDLE,
    }
)

# (current_state, triggering_event) -> next_state
_TRANSITIONS: Dict[Tuple[str, str], str] = {
    (IDLE, "FACE_DETECTED"): FACE_DETECTED,
    (FACE_DETECTED, "FACE_RECOGNIZED"): FACE_RECOGNIZED,
    (FACE_RECOGNIZED, "MULTIPLE_USERS_RECOGNIZED"): PRIORITY_SORTING,
    (PRIORITY_SORTING, "PRIORITY_LIST_READY"): GREETING,
    (GREETING, "GREETING_FINISHED"): WAITING_FOR_WAKE_WORD,
    (WAITING_FOR_WAKE_WORD, "WAKE_WORD_DETECTED"): CONVERSATION_ACTIVE,
    (WAITING_FOR_WAKE_WORD, "FACE_LOST"): FACE_LOST_CHECK,
    (WAITING_FOR_WAKE_WORD, "ALL_USERS_LOST"): FACE_LOST_CHECK,
    (CONVERSATION_ACTIVE, "SCENARIO_MATCHED"): PLAYING_AUDIO,
    (CONVERSATION_ACTIVE, "TIMEOUT_OCCURRED"): TIMEOUT,
    (PLAYING_AUDIO, "PLAYBACK_FINISHED"): CONVERSATION_ACTIVE,
    (PLAYING_AUDIO, "INTERRUPTION_DETECTED"): INTERRUPTED,
    (INTERRUPTED, "INTERRUPTION_CLEARED"): PLAYING_AUDIO,
    (TIMEOUT, "LANGUAGE_CONTEXT_CLEARED"): FACE_LOST_CHECK,
    (FACE_LOST_CHECK, "ALL_USERS_LOST"): RETURN_TO_IDLE,
    (FACE_LOST_CHECK, "FACE_LOST_CHECK_PASSED"): WAITING_FOR_WAKE_WORD,
    (RETURN_TO_IDLE, "IDLE_ENTERED"): IDLE,
}


def _build_allowed_next() -> Dict[str, Set[str]]:
    """Derive the (from_state -> {valid next states}) adjacency map."""
    allowed: Dict[str, Set[str]] = {state: set() for state in STATES}
    for (from_state, _event_name), to_state in _TRANSITIONS.items():
        allowed[from_state].add(to_state)
    return allowed


_ALLOWED_NEXT: Dict[str, Set[str]] = _build_allowed_next()


class FiniteStateMachine:
    """The authoritative controller of robot state, per STATE_MACHINE.md.

    Subscribes to every event named in the transition table and drives
    state changes on the shared StateManager accordingly. Publishes
    STATE_CHANGED after every applied transition.
    """

    def __init__(self, event_bus: EventBus, state_manager: StateManager) -> None:
        """Args:
            event_bus: Bus to subscribe transition-triggering events on
                and publish STATE_CHANGED to.
            state_manager: Shared state store this FSM owns
                current_state for. Its existing current_state (set at
                construction, normally IDLE) is used as-is and is not
                itself treated as a validated transition.
        """
        self._bus = event_bus
        self._state = state_manager

        subscribed_events = {event_name for (_from_state, event_name) in _TRANSITIONS}
        for event_name in subscribed_events:
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
        """Bus callback: apply the transition mapped to (current_state, event.name), if any."""
        target_state = _TRANSITIONS.get((self.current_state, event.name))
        if target_state is None:
            logger.debug(
                "Event %s ignored: no transition defined from state %s",
                event.name,
                self.current_state,
            )
            return
        self.request_transition(target_state, event.name)

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
            ValueError: if to_state is not one of the 12 recognized states.
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
