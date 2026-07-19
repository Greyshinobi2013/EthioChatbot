"""Face presence tracking for EthioChatbot V3.

Per SYSTEM_ARCHITECTURE_V3.md's Face Presence Manager responsibilities:
active users, presence sessions, last-seen timestamps, and face-loss
tracking. Owns presence only -- not greeting persistence (that's
utils/greeting_manager.py's responsibility, per the same document) and
not FSM transitions (utils/fsm.py owns those; this module only
publishes the raw FACE_LOST/ALL_USERS_LOST events the FSM reacts to).

The active-user map itself lives in utils/state_manager.py (Rule 20:
state must not be duplicated); this module adds the face_lost_timeout
countdown and event publishing on top of it.
"""
from __future__ import annotations

import time

from utils.event_bus import EventBus
from utils.logger import get_logger
from utils.state_manager import StateManager

logger = get_logger(__name__)

DEFAULT_FACE_LOST_TIMEOUT_SECONDS = 5.0


class FacePresenceManager:
    """Tracks which enrolled users are currently present and detects departures."""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        face_lost_timeout: float = DEFAULT_FACE_LOST_TIMEOUT_SECONDS,
    ) -> None:
        """Args:
            event_bus: Bus to publish FACE_LOST/ALL_USERS_LOST on.
            state_manager: Shared active-user store this manager updates.
            face_lost_timeout: Seconds a recognized user may go unseen
                before FACE_LOST fires for them.
        """
        self._bus = event_bus
        self._state = state_manager
        self._face_lost_timeout = face_lost_timeout

    def record_sighting(self, user_id: str, priority: int, preferred_language: str) -> bool:
        """Record that user_id was matched in the current frame.

        Args:
            user_id: Enrolled user identifier.
            priority: Lower number means higher greeting priority.
            preferred_language: The user's enrolled language.

        Returns:
            True if user_id was not already in the active list (a new
            arrival, or a returning user whose previous session ended
            in FACE_LOST); False if they were already active (their
            last_seen timestamp was simply refreshed).
        """
        return self._state.upsert_active_user(user_id, priority, preferred_language)

    def check_timeouts(self) -> None:
        """Evaluate active users against face_lost_timeout and publish FACE_LOST/ALL_USERS_LOST.

        Temporary disappearance (return before the timeout elapses)
        never triggers FACE_LOST, per STATE_MACHINE_V3.md's Face
        Presence Workflow: this only fires once elapsed time since
        last_seen exceeds face_lost_timeout.
        """
        now = time.time()
        active_users_before = self._state.get_active_users()

        for user_id, user in active_users_before.items():
            elapsed = now - user.last_seen
            if elapsed > self._face_lost_timeout:
                self._state.remove_active_user(user_id)
                self._bus.publish("FACE_LOST", {"user_id": user_id})
                logger.info("FACE_LOST: user_id=%s (not seen for %.1fs)", user_id, elapsed)

        if active_users_before and not self._state.get_active_users():
            self._bus.publish("ALL_USERS_LOST", {})
            logger.info("ALL_USERS_LOST: no recognized users remain visible")

    def get_active_users(self):
        """The current active-user map (see StateManager.get_active_users())."""
        return self._state.get_active_users()

    def has_active_users(self) -> bool:
        """Whether any enrolled user is currently tracked as present."""
        return bool(self._state.get_active_users())
