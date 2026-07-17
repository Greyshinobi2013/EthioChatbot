"""Thread-safe, in-process publish/subscribe event bus for EthioChatbot V2.

Per EVENTS.md, all inter-service communication happens through events
rather than direct calls between services. The bus itself is generic:
it knows nothing about EVENTS.md's specific event catalog or about the
FSM's transition table. It only routes named events to subscribers.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, DefaultDict, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Event:
    """A lightweight message published on the event bus.

    Attributes:
        name: Event type name (e.g. "FACE_DETECTED"), per EVENTS.md.
        payload: Small dict of data required by subscribers. Per
            EVENTS.md's Raspberry Pi optimization rules, this must not
            carry frames, audio buffers, or other large binary data.
        timestamp: Unix time the event was published.
    """

    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], None]


class EventBus:
    """Thread-safe, local, in-process publish/subscribe event bus.

    Services publish events describing what happened; subscribers
    (chiefly the FSM) react without direct service-to-service coupling,
    per ARCHITECTURE.md's Event Driven Processing principle. Dispatch
    is synchronous: publish() calls each subscriber on the publisher's
    own thread, so handlers must stay fast (EVENTS.md Rule 5).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: DefaultDict[str, List[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler to be invoked whenever event_name is published.

        Args:
            event_name: Exact event name to listen for, per EVENTS.md.
            handler: Callable invoked with the published Event.
        """
        with self._lock:
            self._subscribers[event_name].append(handler)
        logger.debug(
            "Handler subscribed to event %s: %s",
            event_name,
            getattr(handler, "__qualname__", repr(handler)),
        )

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered handler for event_name, if present."""
        with self._lock:
            handlers = self._subscribers.get(event_name)
            if handlers and handler in handlers:
                handlers.remove(handler)

    def publish(self, event_name: str, payload: Optional[Dict[str, Any]] = None) -> Event:
        """Publish an event, synchronously dispatching it to all subscribers.

        A failure in one subscriber is logged and does not prevent
        other subscribers from receiving the event.

        Args:
            event_name: Event name, per EVENTS.md's catalog.
            payload: Optional lightweight event data.

        Returns:
            The Event instance that was dispatched.
        """
        event = Event(name=event_name, payload=dict(payload) if payload else {})

        with self._lock:
            handlers = list(self._subscribers.get(event_name, ()))

        logger.info(
            "EVENT_PUBLISHED: %s | payload=%s | subscribers=%d",
            event.name,
            event.payload,
            len(handlers),
        )

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Error in subscriber %s handling event %s",
                    getattr(handler, "__qualname__", repr(handler)),
                    event_name,
                )

        return event

    def subscriber_count(self, event_name: str) -> int:
        """Return the number of handlers currently subscribed to event_name."""
        with self._lock:
            return len(self._subscribers.get(event_name, ()))
