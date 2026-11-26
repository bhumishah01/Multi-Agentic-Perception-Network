# Iteration 1 — Complete Build Checkpoints

Iteration 1 is a complete local vertical slice: footage enters the perception engine, agents exchange typed messages, uncertain identities are negotiated, specialists open evidence-linked cases, security controls constrain access, and the operations workspace presents the result.

## Checkpoint 1 — Validation footage

**Status:** Complete

- Four supplied clips inspected and registered in `config/cameras.yaml`.
- CAM-02, CAM-03, and CAM-04 are consecutive source segments.
- CAM-01 is separate footage.
- Every screen and result labels the dataset as a **COMPOSED TIMELINE**, not synchronized CCTV.

Visible output: `data/inspect/` and `docs/VALIDATION_DATASET.md`.

## Checkpoint 2 — Perception

**Status:** Complete

- YOLO11n person detection and ByteTrack local tracking.
- HOG/centroid comparison baseline.
- Anonymous HSV appearance descriptors; no face recognition.
- Crops, quality measurements, zones, foot points, and non-destructive overlays.
- 664 observations produced from the four clips.

Visible output: `output/phase2_yolo/previews/`, `observations.json`, and `summary.json`.

## Checkpoint 3 — Agent communication

**Status:** Complete

- Versioned typed message envelopes.
- Explicit `observed`, `inferred`, and `assumptions` fields.
- Asynchronous publish/subscribe bus.
- Deterministic replay clock.
- SHA-256 hash-chained SQLite ledger and causal traces.

Visible output: Agent Constellation and Reasoning Replay lenses.

## Checkpoint 4 — Camera and handoff agents

**Status:** Complete

- Per-camera track memory and zone transitions.
- Exit prediction and topology-aware handoff requests.
- Minimal disclosure: descriptors and kinematics, never images in handoff messages.
- Autonomous ranking of all eligible tracks in the next camera.
- Five-part scoring: appearance, time, spatial compatibility, topology, exclusivity.
- Accepted, ambiguous, and rejected outcomes with winner margins.

Current footage evaluates 3, 6, and 9 candidates across the three transitions. All current winners remain ambiguous and require human review.

Visible output: Handoff Court lens.

## Checkpoint 5 — Intelligence specialists

**Status:** Complete

- Dwell and loiter cues.
- Queue and checkout bottleneck cues.
- Restricted-entry cues.
- Against-flow, backtracking, and running cues.
- Unattended-counter and abandoned-object cues.
- Alternative hypotheses and abstention when evidence is weak.

Visible output: Case Board lens.

## Checkpoint 6 — Evidence and cases

**Status:** Complete

- Evidence bundles select representative crops, time ranges, and paths.
- Cases include measurements, thresholds, hypotheses, contradictions, recommended review, and causal message IDs.
- “Ask why” returns stored facts and causal traces rather than invented explanations.

Visible output: Case Board and the **Ask why** inspector.

## Checkpoint 7 — Security and privacy

**Status:** Complete

- Local bearer authentication and role-based permissions.
- Raw-video restrictions for business roles.
- Masked crop delivery.
- Retention purge endpoint with audit recording.
- Signed-message validation, frozen-feed detection, replay detection, obstruction and impossible-motion health cues.

Visible output: Control Room lens and role selector.

## Checkpoint 8 — Human control and recomputation

**Status:** Complete

- Operator handoff accept/reject decisions persist in SQLite.
- Decisions recompute connected identity components instead of merely changing a label.
- Agent pause, isolate, and resume controls affect downstream confidence.
- Threshold changes and calibration updates are audited.

Visible output: Handoff Court and Control Room lenses.

## Checkpoint 9 — Operations workspace

**Status:** Complete

The workspace provides eight investigative lenses:

1. Store Twin
2. Entity Thread
3. Agent Constellation
4. Perception
5. Handoff Court
6. Case Board
7. Reasoning Replay
8. Control Room

This is an interactive operations theatre, not a conventional KPI dashboard.

## Checkpoint 10 — Evaluation and verification

**Status:** Complete

- 42 backend, security, agent, API, and real-replay tests pass.
- 3 browser interaction tests pass.
- 3 attack demonstrations are detected.
- Production workspace build passes.
- Ledger integrity passes.
- One-command verifier passes.

The current HSV baseline does not recover the two known reference identity links. APN therefore abstains instead of forcing a false merge. This limitation is recorded in `docs/EVALUATION.md` and `eval/results.json`.

## Run Iteration 1

From the `apn` folder:

```bash
./run.sh
```

Then open `http://127.0.0.1:8766` and use token `apn-local-demo`.

Recommended review order: **select camera → watch tracking/privacy overlay → ask the orchestrator → watch agent delegation → inspect the verified answer → open Decision Studio**.

## Iterations 2–5 — Business Decision Studio

**Status:** Complete

- Iteration 2: traffic heatmaps, local-track paths and within-clip comparisons.
- Iteration 3: queue intelligence, uncertainty-aware passage funnel and
  evidence-linked recommendations.
- Iteration 4: human approval and checkout/aisle what-if simulation.
- Iteration 5: operational report generation and resilience evaluation under
  camera loss, message delay and ambiguous identity.

The current interface uses a single video-first workspace. Submit an
investigation and select **Open full Decision Studio** to reveal these deeper
capabilities without navigating technical tabs.
