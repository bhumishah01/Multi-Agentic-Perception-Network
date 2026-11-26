"""Async in-process bus with deterministic replay ordering."""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from .ledger import HashChainedLedger
from .protocol import MessageEnvelope, MessageType

Handler = Callable[[MessageEnvelope], Awaitable[None]]


class AsyncMessageBus:
    def __init__(self, ledger: HashChainedLedger) -> None:
        self.ledger = ledger
        self._subscribers: dict[str, list[tuple[int, Handler]]] = defaultdict(list)
        self._sequence = len(ledger.messages())
        self._lock = asyncio.Lock()

    def subscribe(self, message_type: MessageType | str, handler: Handler, priority: int = 100) -> None:
        self._subscribers[message_type].append((priority, handler))
        self._subscribers[message_type].sort(key=lambda item: item[0])

    async def publish(
        self, message_type: MessageType, sender: str, *, ts_source: float,
        payload: dict[str, Any] | None = None, observed: dict[str, Any] | None = None,
        inferred: dict[str, Any] | None = None, assumptions: tuple[str, ...] = (),
        confidence: float | None = None, score: float | None = None,
        evidence: tuple[str, ...] = (), caused_by: str | None = None,
        ts_ingest: float | None = None,
    ) -> MessageEnvelope:
        async with self._lock:
            self._sequence += 1
            message = MessageEnvelope(
                id=f"MSG-{self._sequence:06d}", type=message_type, sender=sender,
                ts_source=ts_source, ts_ingest=time.time() if ts_ingest is None else ts_ingest,
                payload=payload or {}, observed=observed or {}, inferred=inferred or {},
                assumptions=assumptions, confidence=confidence, score=score,
                evidence=evidence, caused_by=caused_by,
            )
            message = self.ledger.append(message)
        for _, handler in self._subscribers.get(message.type, ()):
            await handler(message)
        return message

    async def replay(self, messages: list[MessageEnvelope]) -> None:
        for message in sorted(messages, key=lambda item: (item.ts_source, item.id)):
            for _, handler in self._subscribers.get(message.type, ()):
                await handler(message)
