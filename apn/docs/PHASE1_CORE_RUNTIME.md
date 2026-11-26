# Phase 1 — Core runtime and protocol

## Delivered

- Strict Pydantic message envelope with typed message kinds.
- Separate `observed`, `inferred`, and `assumptions` fields.
- Evidence and `caused_by` validation for inferred claims.
- Async publish/subscribe bus with stable priority ordering.
- Deterministic source-time replay ordering.
- Append-only SQLite message ledger.
- SHA-256 hash chain over canonical JSON.
- Chain verification and tamper-location reporting.
- Causal ancestor tracing from any message to its first observation.
- Replay clock with play, pause, seek, speed, and deterministic advance.

## Acceptance evidence

Automated tests cover valid chaining, deliberate row tampering, causal trace,
deterministic replay, and clock controls.

## Known gap retained intentionally

The old `server.py` API remains operational for the experimental interface, but
its legacy specialist functions have not been made the new production API. The
new core is isolated under `apn/core`; server replacement belongs with the
FastAPI work and should consume this ledger instead of duplicating reasoning.
No dashboard work was performed.
