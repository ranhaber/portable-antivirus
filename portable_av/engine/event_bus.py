from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from portable_av.common.time import utc_now


@dataclass(frozen=True)
class EventEnvelope:
    type: str
    timestamp: datetime
    sequence: int
    payload: dict[str, Any]


@dataclass
class EventBus:
    max_queue_size: int = 100
    _sequence: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _subscribers: list[asyncio.Queue[EventEnvelope]] = field(default_factory=list, init=False)
    _latest: EventEnvelope | None = field(default=None, init=False)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> EventEnvelope:
        async with self._lock:
            self._sequence += 1
            envelope = EventEnvelope(
                type=event_type,
                timestamp=utc_now(),
                sequence=self._sequence,
                payload=payload,
            )
            self._latest = envelope

        dead: list[asyncio.Queue[EventEnvelope]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            if queue in self._subscribers:
                self._subscribers.remove(queue)
        return envelope

    async def subscribe(self) -> AsyncIterator[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=self.max_queue_size)
        self._subscribers.append(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def latest_snapshot(self) -> EventEnvelope | None:
        return self._latest
