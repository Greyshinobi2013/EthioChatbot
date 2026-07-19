"""Shared state store for EthioChatbot V3.

Per SYSTEM_ARCHITECTURE_V3.md's State Manager responsibilities, this is
the single place current system state is stored: FSM state, camera
status, detected/active users, the greeting queue, and playback status.
No other module may hold its own copy of this data (DEVELOPMENT_RULES_V3.md
Rule 20). All access is protected by a single lock so services running
on different threads (camera loop, playback watcher, Streamlit page
reruns) see a consistent snapshot.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ActiveUser:
    """A currently-visible, recognized enrolled user.

    Attributes:
        user_id: Enrolled user identifier.
        priority: Lower number means higher greeting priority.
        preferred_language: One of the supported languages.
        last_seen: Unix timestamp this user was last matched in a frame.
        greeted: Whether this presence session's greeting has already
            been played (greeting persistence, cleared on FACE_LOST).
    """

    user_id: str
    priority: int
    preferred_language: str
    last_seen: float = field(default_factory=time.time)
    greeted: bool = False


class StateManager:
    """Thread-safe store for all system state read by the FSM, services, and dashboard."""

    def __init__(self, initial_state: str = "FACE_DETECTION_MODE") -> None:
        """Args:
            initial_state: The FSM state to start in.
        """
        self._lock = threading.RLock()
        self._current_state = initial_state
        self._camera_status = "stopped"
        self._playback_status: Dict[str, object] = {"state": "idle", "current_file": None}
        self._interaction_mode = "common_dialog"
        self._detected_users: List[str] = []
        self._active_users: Dict[str, ActiveUser] = {}
        self._greeting_queue: List[str] = []

    # -- FSM state -----------------------------------------------------

    @property
    def current_state(self) -> str:
        """The FSM's current state."""
        with self._lock:
            return self._current_state

    def set_current_state(self, state: str) -> None:
        """Set the current FSM state. Only fsm.py should call this (Rule 19)."""
        with self._lock:
            self._current_state = state

    # -- Camera ----------------------------------------------------------

    def set_camera_status(self, status: str) -> None:
        """Record the camera's lifecycle status (e.g. "running", "stopped", "error")."""
        with self._lock:
            self._camera_status = status

    def get_camera_status(self) -> str:
        """Current camera lifecycle status."""
        with self._lock:
            return self._camera_status

    # -- Detected users (raw, unrecognized-or-not, this frame) ----------

    def set_detected_users(self, user_ids: List[str]) -> None:
        """Record which enrolled users were matched in the most recent recognition pass."""
        with self._lock:
            self._detected_users = list(user_ids)

    def get_detected_users(self) -> List[str]:
        """User IDs matched in the most recent recognition pass."""
        with self._lock:
            return list(self._detected_users)

    # -- Active users (recognized and currently present) -----------------

    def upsert_active_user(self, user_id: str, priority: int, preferred_language: str) -> bool:
        """Record a sighting of user_id, creating or refreshing its entry.

        Returns:
            True if this user_id was not already active (a new arrival),
            False if it was already active (last_seen was simply refreshed).
        """
        with self._lock:
            existing = self._active_users.get(user_id)
            if existing is None:
                self._active_users[user_id] = ActiveUser(
                    user_id=user_id, priority=priority, preferred_language=preferred_language
                )
                return True
            existing.last_seen = time.time()
            existing.priority = priority
            existing.preferred_language = preferred_language
            return False

    def remove_active_user(self, user_id: str) -> None:
        """Remove a user from the active list (on FACE_LOST)."""
        with self._lock:
            self._active_users.pop(user_id, None)

    def get_active_users(self) -> Dict[str, ActiveUser]:
        """A shallow copy of the current active-user map, keyed by user_id."""
        with self._lock:
            return dict(self._active_users)

    def mark_greeted(self, user_id: str) -> None:
        """Mark user_id as greeted for its current presence session.

        Re-greeting after a real departure needs no separate "clear"
        step: remove_active_user() deletes the entry entirely on
        FACE_LOST, so a later upsert_active_user() for the same user
        creates a brand new ActiveUser with greeted defaulting back to
        False, exactly matching STATE_MACHINE_V3.md's Re-Greeting
        Conditions.
        """
        with self._lock:
            user = self._active_users.get(user_id)
            if user is not None:
                user.greeted = True

    def clear_all_greeted(self) -> None:
        """Reset greeted=False for every currently active user.

        Used by the Restart Greetings operator action (RESTART_GREETINGS
        event) to force a full replay for everyone still visible,
        without touching presence tracking, enrollment, priority, or
        language data -- only the greeted flag is affected.
        """
        with self._lock:
            for user in self._active_users.values():
                user.greeted = False

    # -- Greeting queue (for dashboard display) --------------------------

    def set_greeting_queue(self, queue: List[str]) -> None:
        """Record the ordered greeting queue (user_ids, in playback order) for display."""
        with self._lock:
            self._greeting_queue = list(queue)

    def get_greeting_queue(self) -> List[str]:
        """The most recently built greeting queue."""
        with self._lock:
            return list(self._greeting_queue)

    # -- Playback status --------------------------------------------------

    def set_playback_status(self, status: Dict[str, object]) -> None:
        """Record the latest PlaybackService.get_status() snapshot, as a plain dict."""
        with self._lock:
            self._playback_status = dict(status)

    def get_playback_status(self) -> Dict[str, object]:
        """The most recently recorded playback status snapshot."""
        with self._lock:
            return dict(self._playback_status)

    # -- Interaction mode ---------------------------------------------------

    def set_interaction_mode(self, mode: str) -> None:
        """Record the active interaction mode ("common_dialog" or "user_specific_dialog")."""
        with self._lock:
            self._interaction_mode = mode

    def get_interaction_mode(self) -> str:
        """The active interaction mode."""
        with self._lock:
            return self._interaction_mode

    # -- Snapshot ----------------------------------------------------------

    def snapshot(self) -> Dict[str, object]:
        """A single consistent point-in-time view of all state, for the dashboard."""
        with self._lock:
            return {
                "current_state": self._current_state,
                "camera_status": self._camera_status,
                "playback_status": dict(self._playback_status),
                "interaction_mode": self._interaction_mode,
                "detected_users": list(self._detected_users),
                "active_users": {
                    user_id: {
                        "priority": user.priority,
                        "preferred_language": user.preferred_language,
                        "last_seen": user.last_seen,
                        "greeted": user.greeted,
                    }
                    for user_id, user in self._active_users.items()
                },
                "greeting_queue": list(self._greeting_queue),
            }
