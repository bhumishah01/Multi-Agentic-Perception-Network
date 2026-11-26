# APN agent protocol

Every message separates `observed`, `inferred`, and `assumptions`. Inference
requires evidence or a causal parent. Messages include source and ingest time,
visibility roles, evidence references, `caused_by`, previous hash, and hash.
Canonical JSON plus the previous digest forms the SHA-256 chain. `trace(id)`
walks causal parents to the originating observation.

Handoffs disclose only an anonymous embedding reference, final kinematics,
exit direction, candidate cameras, and expiry. Crops and raw image bytes are
forbidden. Offers contain appearance, temporal, spatial, topology, and
exclusivity component scores. Scores are not probabilities. The Identity Agent
accepts, rejects, or retains a fork as ambiguous. Human rejection generates an
`identity.unlink`, splits the entity, and marks dependent conclusions for
recomputation.

This is a protocol-design candidate pending prior-art review; no novelty or
patent claim is made.
