# Agentic Perception Network

APN is a local, software-only multi-agent perception system for understanding movement across camera views without face recognition. It converts video observations into anonymous local tracks, negotiates uncertain cross-camera handoffs, runs business and security specialists, preserves causal evidence, and exposes the result through an interactive operations workspace.

The current supermarket clips form a **COMPOSED validation timeline**. They test the system end to end, but they are synthetic and are not a synchronized CCTV benchmark.

## Footage setup

Source surveillance is deliberately excluded from Git. By default, `run.sh`
discovers supported video files in:

```text
/Volumes/One Touch/SURVELLIANCE /SUPERMARKET FINAL
```

`tools/sync_supermarket_media.py` inventories the folder, ignores macOS sidecar
files, maps reviewed clips into Entrance, Grocery, Promotions/Assistance and
Checkout camera roles, builds local replay reels, and records source provenance.
The original videos are never modified. Restart `run.sh` after adding footage;
the perception pipeline reruns only when the media fingerprint changes.

## Run everything

From this `apn` folder:

```bash
./run.sh
```

This verifies the backend, generates or reuses perception evidence, builds the scenario and evaluation, compiles the workspace, runs the security demonstration, and starts APN at `http://127.0.0.1:8766`.

The default local token is `apn-local-demo`. Keep the terminal open; press `Control-C` to stop.

## Implemented system

- YOLO11n + ByteTrack perception with a HOG/centroid baseline
- anonymous appearance embeddings, crops, quality signals, zones, and floor points
- typed asynchronous messages, deterministic replay, causal traces, and a SHA-256 hash-chained ledger
- camera memory, exit prediction, minimal-disclosure handoffs, candidate ranking, and accepted/ambiguous/rejected decisions
- autonomous ranking of every eligible next-camera track; downstream demo targets are not manually selected
- dwell, loiter, queue, restricted-entry, bottleneck, motion, unattended-counter, and abandoned-object specialists
- evidence bundles, alternative hypotheses, explainable cases, and human-review states
- persistent operator decisions that recompute identity components after accept/reject
- local bearer authentication, role-based access, masking, retention purge, health checks, and attack demonstrations
- FastAPI REST/WebSocket service and React Agentic Operations Theatre with eight investigative lenses
- API homography calibration and explicit approximate-floor fallback
- honest evaluation and a full real-observation replay test

## Decision Studio iterations

The video-first workspace now expands into a progressive Decision Studio after
an investigation. It implements the major-project business layer without
turning the landing screen back into a tabbed dashboard:

- image-plane traffic heatmaps and anonymous local-track paths;
- first-half versus second-half time-window comparisons;
- checkout occupancy, pressure thresholds and visible-duration measures;
- an uncertainty-aware Entrance → Aisle → Service → Checkout passage funnel;
- human-controlled operational recommendations with no automatic external action;
- checkout-capacity and aisle-capacity what-if simulations;
- generated, audit-recorded operational reports under `output/reports/`;
- centralised-versus-agentic resilience experiments for camera loss, message
  delay and ambiguous identity.

These outputs remain evidence-bound. Passage indices are not sales conversion,
visible track duration is not validated waiting time, and simulations are
sensitivity scenarios rather than forecasts.

## Guided closed-loop showcase

After the first orchestrator response, select **Launch complete investigation**.
The Investigation Theatre explains the project as one six-step story:

1. **Observe** — measured CAM-04 occupancy evidence.
2. **Remember** — the anonymous spatial-memory timeline.
3. **Investigate** — orchestrator delegation and specialist results.
4. **Explain** — competing hypotheses, contradictions and verifier conclusion.
5. **Simulate** — current versus additional-checkout capacity.
6. **Verify** — human approval and a staged before/after outcome.

The staged disruption switch is deliberately explicit. With it enabled, a
controlled “Counter 2 inactive” operations input demonstrates causal reasoning
and intervention verification. With it disabled, the same system reports that
the footage alone is insufficient to prove the root cause. No external action
is performed by the showcase.

## Major-project System Laboratory

The landing experience now exposes executable technical systems rather than
additional summary cards:

- a cross-camera trajectory graph built from all local tracks and uncertain
  handoffs;
- a query compiler that generates a different agent execution DAG for each
  question;
- an automatically selected, privacy-masked evidence wall and causal ledger;
- an incident laboratory for camera loss, message delay, identity ambiguity,
  queue surge and forged messages;
- per-edge-camera processing, latency, message share and confidence state;
- a controllable minute-by-minute queue digital twin;
- a centralised-versus-agentic benchmark laboratory.

The local web build disables browser caching so frontend changes are visible
after a normal refresh during development.

## Current truth boundary

The current 14-clip validation pack produced 4,057 YOLO observations and 114
camera-local tracks. APN ranked 23, 28, and 17 eligible candidates in the three
successive handoff stages. All three links remain ambiguous because the clips
are independently generated and not synchronized ground truth. That correctly
triggers human review instead of forcing a false identity merge. Scores are
deterministic decision cues, not calibrated identity probabilities.

Dense identity ground truth is unavailable, so IDF1 and ID-switch counts are deliberately not claimed. See `eval/results.json` and `docs/EVALUATION.md`.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/attack_demo.py
.venv/bin/python tools/verify_build.py
cd web2 && npm run test:ui
```

## Structure

- `apn/core` — protocol, bus, replay clock, ledger
- `apn/perception` — detection, tracking, embeddings, zones, floor projection
- `apn/agents` — camera, handoff, identity, specialists, evidence, orchestration
- `apn/security` — authorization, masking, health, retention
- `apn/api` — local service and workspace API
- `web2` — interactive operations theatre
- `tools` — inspection, processing, scenario, calibration, attack, and verification tools
- `docs` — architecture, protocol, threat model, evaluation, and validation boundaries

Ultralytics is distributed under AGPL-3.0. Review its licence before distributing or commercialising this build. The prototype is local-only and should not be exposed as a production surveillance service.
