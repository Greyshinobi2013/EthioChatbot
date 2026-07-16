"""In-process, thread-safe publish/subscribe event bus.

All service-to-service communication goes through this bus
(ARCHITECTURE.md "Service Communication Rules") instead of direct calls.
Each handler runs in its own short-lived daemon thread so a slow or
blocking handler (e.g. audio playback) never stalls the thread that
published the event, such as the camera service's capture loop.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from utils.logger import get_logger

logger = get_logger("event_bus")

EventHandler = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(handler)
        logger.info("Handler subscribed to event: %s", event_type)

    def publish(self, event_type: str, **data: Any) -> None:
        event: dict[str, Any] = {"type": event_type, **data}
        with self._lock:
            handlers = list(self._subscribers.get(event_type, ()))

        logger.info("Event published: %s %s", event_type, data)

        for handler in handlers:
            threading.Thread(
                target=_dispatch,
                args=(handler, event),
                name=f"event-{event_type}",
                daemon=True,
            ).start()


def _dispatch(handler: EventHandler, event: dict[str, Any]) -> None:
    try:
        handler(event)
    except Exception:
        logger.exception("Event handler raised for event '%s'", event.get("type"))


_event_bus = EventBus()


def publish(event_type: str, **data: Any) -> None:
    _event_bus.publish(event_type, **data)


def subscribe(event_type: str, handler: EventHandler) -> None:
    _event_bus.subscribe(event_type, handler)
