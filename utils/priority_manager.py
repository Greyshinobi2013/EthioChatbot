"""Priority ordering for EthioChatbot V3.

Per PROJECT_SPECIFICATION_V3.md section 8: lower priority number means
higher greeting priority. This module has a single responsibility
(DEVELOPMENT_RULES_V3.md Rule 3) -- sorting -- and holds no state of
its own.
"""
from __future__ import annotations

from typing import Dict, List

from utils.state_manager import ActiveUser


def sort_by_priority(active_users: Dict[str, ActiveUser]) -> List[ActiveUser]:
    """Sort active users by priority, lower number first.

    Args:
        active_users: Mapping of user_id -> ActiveUser, as returned by
            StateManager.get_active_users().

    Returns:
        Users ordered ascending by priority. Ties are broken by
        user_id for a deterministic, repeatable order.
    """
    return sorted(active_users.values(), key=lambda user: (user.priority, user.user_id))
