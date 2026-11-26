"""Append-only SQLite hash-chain ledger."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .protocol import MessageEnvelope


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class HashChainedLedger:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS message_ledger(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                envelope TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE
            )
        """)

    @staticmethod
    def calculate_hash(previous_hash: str, envelope_without_hash: dict) -> str:
        return hashlib.sha256((previous_hash + canonical_json(envelope_without_hash)).encode()).hexdigest()

    def append(self, message: MessageEnvelope) -> MessageEnvelope:
        row = self.connection.execute(
            "SELECT hash FROM message_ledger ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = row["hash"] if row else "GENESIS"
        chained = message.model_copy(update={"prev_hash": previous_hash, "hash": ""})
        digest = self.calculate_hash(previous_hash, chained.without_chain_fields())
        chained = chained.model_copy(update={"hash": digest})
        with self.connection:
            self.connection.execute(
                "INSERT INTO message_ledger(message_id,envelope,prev_hash,hash) VALUES(?,?,?,?)",
                (chained.id, canonical_json(chained.model_dump(mode="json")), previous_hash, digest),
            )
        return chained

    def get(self, message_id: str) -> MessageEnvelope | None:
        row = self.connection.execute(
            "SELECT envelope FROM message_ledger WHERE message_id=?", (message_id,)
        ).fetchone()
        return MessageEnvelope.model_validate_json(row["envelope"]) if row else None

    def messages(self) -> list[MessageEnvelope]:
        rows = self.connection.execute("SELECT envelope FROM message_ledger ORDER BY sequence").fetchall()
        return [MessageEnvelope.model_validate_json(row["envelope"]) for row in rows]

    def verify_chain(self) -> tuple[bool, str | None]:
        previous_hash = "GENESIS"
        rows = self.connection.execute(
            "SELECT message_id,envelope,prev_hash,hash FROM message_ledger ORDER BY sequence"
        ).fetchall()
        for row in rows:
            try:
                message = MessageEnvelope.model_validate_json(row["envelope"])
            except Exception:
                return False, row["message_id"]
            expected = self.calculate_hash(previous_hash, message.model_copy(update={"hash": ""}).without_chain_fields())
            if row["prev_hash"] != previous_hash or message.prev_hash != previous_hash:
                return False, row["message_id"]
            if row["hash"] != expected or message.hash != expected:
                return False, row["message_id"]
            previous_hash = expected
        return True, None

    def trace(self, message_id: str) -> list[MessageEnvelope]:
        trace: list[MessageEnvelope] = []
        seen: set[str] = set()
        current = self.get(message_id)
        while current is not None:
            if current.id in seen:
                raise ValueError("causal cycle detected")
            seen.add(current.id)
            trace.append(current)
            current = self.get(current.caused_by) if current.caused_by else None
        return list(reversed(trace))

    def close(self) -> None:
        self.connection.close()
