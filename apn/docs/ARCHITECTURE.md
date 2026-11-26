# APN architecture

APN is a local-only, event-driven perception network. Four configured camera
agents consume versioned perception observations. All inter-agent conclusions
use the typed protocol and enter the append-only SHA-256 ledger. Camera agents
maintain ten seconds of track memory and publish zone and exit events. The
handoff and identity agents exchange minimal anonymous appearance descriptors
and kinematics, retain ambiguous forks, and preserve link provenance.

Specialists convert measurements into hypotheses and findings. The orchestrator
deduplicates those findings into cases, while the evidence and causal-trace
paths preserve exactly which observations produced each conclusion. The
FastAPI layer enforces local tokens and role permissions. The React workspace
is a projection of API/ledger state; it is not a second source of truth.

```text
Videos → YOLO/ByteTrack → observations → hash-chained bus
                                          ├─ camera agents
                                          ├─ handoff/identity
                                          ├─ specialists
                                          └─ orchestrator → cases/evidence
                                                            ↓
                                                FastAPI → workspace
```

The current floor map uses normalized approximate positions because real-world
floor correspondences are unavailable. The calibration tool records homography
residual error when real points are supplied.
