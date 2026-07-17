"""Thread-safe shared application state for EthioChatbot V2.

Per ARCHITECTURE.md's Core Layer, all services communicate state
through a single StateManager instance rather than holding private
copies, so the FSM, dashboard, and every service observe a consistent
view of the robot's runtime status. All mutations are guarded by a
lock because camera, audio, playback, VAD, and conversation services
each run on their own thread.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ActiveUser:
    """Snapshot of a currently recognized user's presence.

    Attributes:
        user_id: Enrolled user identifier.
        priority: Lower number means higher greeting priority.
        preferred_language: Fallback language when no wake word
            language is available.
        last_seen: Unix timestamp of the most recent recognition.
    """

    user_id: str
    priority: int
    preferred_language: str
    last_seen: float


class StateManager:
    """Centralized, thread-safe store for runtime application state.

    Stores exactly the fields ARCHITECTURE.md designates as shared
    state: current_state, current_language, active_users,
    camera_status, playback_status, and wake_word_status. Kept
    intentionally lightweight per the Raspberry Pi optimization rules.
    """

    def __init__(self, initial_state: str = "IDLE") -> None:
        """Initialize shared state with the robot at rest.

        Args:
            initial_state: The FSM state to report before the state
                machine (Milestone 2) takes ownership of transitions.
        """
        self._lock = threading.RLock()
        self._current_state: str = initial_state
        self._current_language: Optional[str] = None
        self._active_users: Dict[str, ActiveUser] = {}
        self._camera_status: str = "stopped"
        self._playback_status: str = "idle"
        self._wake_word_status: str = "inactive"

    @property
    def current_state(self) -> str:
        """Current FSM state name."""
        with self._lock:
            return self._current_state

    def set_current_state(self, state: str) -> None:
        """Overwrite the current FSM state name.

        Only the FSM (Milestone 2) should call this in the running
        system; other services must go through events instead of
        setting state directly.
        """
        with self._lock:
            self._current_state = state

    @property
    def current_language(self) -> Optional[str]:
        """Active conversation language, or None outside a session."""
        with self._lock:
            return self._current_language

    def set_current_language(self, language: Optional[str]) -> None:
        """Set or clear (``None``) the active conversation language."""
        with self._lock:
            self._current_language = language

    def upsert_active_user(self, user_id: str, priority: int, preferred_language: str) -> None:
        """Add a newly recognized user or refresh an existing one's last_seen.

        Args:
            user_id: Enrolled user identifier.
            priority: Lower number means higher greeting priority.
            preferred_language: The user's enrolled fallback language.
        """
        with self._lock:
            self._active_users[user_id] = ActiveUser(
                user_id=user_id,
                priority=priority,
                preferred_language=preferred_language,
                last_seen=time.time(),
            )

    def remove_active_user(self, user_id: str) -> None:
        """Remove a user after FACE_LOST, if present."""
        with self._lock:
            self._active_users.pop(user_id, None)

    def get_active_users(self) -> Dict[str, ActiveUser]:
        """Return a shallow copy of currently active users, keyed by user_id."""
        with self._lock:
            return dict(self._active_users)

    def clear_active_users(self) -> None:
        """Remove all active users, e.g. during RETURN_TO_IDLE cleanup."""
        with self._lock:
            self._active_users.clear()

    @property
    def camera_status(self) -> str:
        """Camera service status string (e.g. 'stopped', 'running')."""
        with self._lock:
            return self._camera_status

    def set_camera_status(self, status: str) -> None:
        with self._lock:
            self._camera_status = status

    @property
    def playback_status(self) -> str:
        """Playback service status string (e.g. 'idle', 'playing', 'paused')."""
        with self._lock:
            return self._playback_status

    def set_playback_status(self, status: str) -> None:
        with self._lock:
            self._playback_status = status

    @property
    def wake_word_status(self) -> str:
        """Wake word listening status string (e.g. 'inactive', 'listening')."""
        with self._lock:
            return self._wake_word_status

    def set_wake_word_status(self, status: str) -> None:
        with self._lock:
            self._wake_word_status = status

    def snapshot(self) -> dict:
        """Return a point-in-time copy of all shared state.

        Intended for the dashboard and logging, where a consistent
        read across multiple fields is needed without holding the
        lock for the duration of the caller's work.
        """
        with self._lock:
            return {
                "current_state": self._current_state,
                "current_language": self._current_language,
                "active_users": {
                    user_id: {
                        "user_id": user.user_id,
                        "priority": user.priority,
                        "preferred_language": user.preferred_language,
                        "last_seen": user.last_seen,
                    }
                    for user_id, user in self._active_users.items()
                },
                "camera_status": self._camera_status,
                "playback_status": self._playback_status,
                "wake_word_status": self._wake_word_status,
            }
