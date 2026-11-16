# Agentic Perception Network — uncertainty-aware foundation 0.2

A runnable starting point for the proposed three-layer system. This is an event-driven baseline, not a finished autonomous multi-camera product.

## Run the current Operational Theatre

From the `apn` folder:

```bash
./run_apn.sh
```

The first run prepares the local computer-vision environment and builds evidence from the supplied videos. When the terminal prints the session token, open `http://127.0.0.1:8765`, paste the token, and select **Load real evidence**. Keep the terminal open while using the application. Stop it with `Control-C`.

## Run (macOS / Linux / Windows with Python 3.10+)

1. Extract this folder and open a terminal inside it.
2. Run `python3 server.py` (Windows: `python server.py`). No dependencies required for the synthetic demo.
3. Open http://127.0.0.1:8765 and paste the session token printed by the server.
4. Load the synthetic four-camera queue scenario, then ask about congestion, waiting, or handoffs.
5. Disable CAM-4 and investigate again. Inspect the changed coverage, evidence, and verifier warning.
6. Export the latest investigation as JSON.

The server intentionally binds to localhost. Do not expose it as a production service. Tokens stay in page memory. Database persists events, investigation results, tasks, and audit entries in apn.sqlite3. Camera toggles are runtime-only. Restarting invalidates automatically generated session tokens.

## Real recorded-video baseline (optional)

Install `python3 -m pip install opencv-python`. Set `APN_TOKEN` and `APN_INGEST_SECRET` to your own random secrets in the terminals running both server and adapter, then restart the server. Run `python3 video_adapter.py /absolute/path/video.mp4 --camera CAM-1`.

This live adapter provides a basic HOG person detector and greedy local centroid association. Expect missed detections and identity switches. Confidence 0.5 is a fixed placeholder, not a calibrated probability. Zones are image quadrants, not calibrated physical zones. Its events use processing timestamps; use `replay_pipeline.py` when source-video timestamps matter. Only ingest footage you are permitted to process.

## Real multi-camera replay

The checked-in test footage under `data/realistic_store_v1/videos/` contains four extracted camera views. Run the offline perception baseline with source-video timestamps:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-cv.txt
.venv/bin/python replay_pipeline.py --every 8
```

Outputs are written to `output/realistic_store_v1/`: one annotated MP4 per camera, `replay_evidence.json` with frame-level boxes and local-track observations, and `replay_summary.json` with camera-level counts. The present HOG detector is a dependency-light baseline and its scores are not calibrated probabilities. The extracted CAM-02 to CAM-04 clips are sequential source segments rather than synchronized recordings, so they support pipeline integration but not a valid multi-camera tracking benchmark.

After generating the replay, start `server.py`, open the workspace, and click **Load real replay evidence**. This imports the frame observations and appearance-based cross-camera candidates into SQLite. The four annotated videos remain playable in the workspace, and investigations operate on the imported real observations rather than the synthetic scenario.

## What changed in 0.2

- Handoff hypotheses carry component evidence, score, runner-up margin, provenance, and an accepted / ambiguous / rejected state.
- Accepted handoffs merge local tracks. Ambiguous handoffs produce identity-count bounds instead of a false single count.
- Questions select typed Flow, Dwell, or Movement specialists; the Verifier always runs.
- Agent requests and structured results are persisted as inspectable messages.
- Evidence quality degrades when a view is offline or a handoff remains ambiguous, forcing operator review.

The scores are deterministic research heuristics, not calibrated probabilities. The synthetic scenario deliberately includes ambiguity so the propagation path can be tested.

## Three layers

- Intelligence Engine: structured events, explicit handoff decisions, identity bounds, typed specialists, evidence-linked results.
- Agentic Workspace: floor zones, local-track markers, camera controls, handoff trail, agent messages, evidence grade and export.
- Security Layer: bearer-authenticated API, HMAC-signed external ingestion, ingestion timestamp window, payload validation, localhost binding, audit records and CSP.

## Implemented versus planned

Implemented: persistent SQLite event store, synthetic multi-camera scenario, uncertainty-aware handoffs, question-based typed planning, concurrent specialists, no-evidence handling, camera coverage control, browser workspace, JSON export, signed ingestion, optional baseline video adapter.

Planned: strong detector/tracker, calibrated zones, synchronized playback, learned/calibrated handoff evidence, bounded adaptive planning, queue membership and service-time estimation, fine-grained agent identities and RBAC, retention enforcement, encryption at rest, distributed deployment, replay protection beyond timestamp windows, benchmark evaluation, and browser interaction QA.

The current agents are deterministic specialist workers. Natural-language questions are recorded, but do not change the fixed investigation plan. Cross-camera global identities are not inferred. Observed spans are window-censored, not complete visits. The UI shows recent event samples, not live video positions. No autonomous staffing changes or external messages occur. The current shared token and HMAC secret are prototype controls, not complete multi-agent security.

## Verify

`python3 -m unittest discover -s tests -v`

Checks: synthetic evidence and identity bounds, handoff policy, typed planning, missing-evidence abstention, camera-loss coverage, and invalid-event rejection. JavaScript syntax checked separately using `node --check web/app.js`.

## Project direction

Keep the core a decentralized spatial intelligence network. First vertical: queue and service operations in a controlled commercial-space scenario. Candidate niches to validate: diagnostic-centre registration/sample queues, campus service counters, and multi-stage vehicle service reception. These are hypotheses, not proven demand. Automate counting, continuity, bottleneck investigation and escalation first; operational staff decisions need appropriate validation and oversight.

Milestones:
1. Select 2–3 synchronized camera views and acquire labelled data with suitable access rights.
2. Replace HOG with a benchmarked detector and local tracker; measure IDF1/ID switches.
3. Calibrate zones and preserve capture timestamps.
4. Implement candidate handoff messages with accept/reject/ambiguous states and provenance.
5. Compare centralized association against peer handoffs under delay, camera loss and ambiguous matches.
6. Propagate association uncertainty into analytics and abstention decisions.
7. Add bounded planner selecting typed analytics tools; compare with this deterministic baseline.
8. Make workspace evidence selection, timeline replay and agent interventions interactive.
9. Add per-agent authorization, retention and replay protection; run security tests.
10. Evaluate accuracy, communication, task success, cost and operator understanding. Investigate prior work before making novelty or patent claims.
