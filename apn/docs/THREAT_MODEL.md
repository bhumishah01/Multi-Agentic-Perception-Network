# APN threat model

Protected assets include raw footage, crops, anonymous embeddings, entity
journeys, cases, agent-control state, and the decision ledger. Threat actors
include unauthorized local users, compromised camera adapters, malicious
agents, and accidental operator actions.

Controls implemented:

- localhost-only service and bearer token;
- role-based raw-video, decision, audit, and agent-management permissions;
- per-agent HMAC signing primitive and forged-message rejection;
- append-only hash chain with first-corruption reporting;
- masked and metadata-only image transforms;
- minimal-disclosure handoff messages;
- frozen, obstruction, replay-sequence, silence-ready heartbeat, and impossible-
  motion detectors;
- no external actions or cloud transmission.

Residual risks include token exposure on a shared machine, SQLite file deletion,
model evasion, weak HSV appearance descriptors, missing encrypted storage, and
the absence of hardware-backed camera attestation. Production deployment would
require secret rotation, TLS, encrypted storage, signed binaries, stronger
agent keys, retention scheduling, and independent security review.
