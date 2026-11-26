# APN BUILD SPECIFICATION — Multi-Agentic Perception Network

> Paste this entire document to a coding LLM (Claude Code recommended) running inside the project folder.
> Prefix your first message with: **"Read this spec fully. Start with Phase 0 only. Do not skip ahead. Report after each phase."**

---

## 0. ROLE AND OPERATING RULES (for the LLM)

You are the lead engineer building APN, a final-year-project-grade, software-only visual intelligence platform. Work phase by phase. After each phase: run the tests, summarise what exists, list known gaps, and wait for approval before the next phase.

Hard rules:

1. **No fake data presented as real.** Every position, track, match score and event shown in the UI must come from the pipeline output. If something is scripted or composed (see §2.3), the UI must label it "COMPOSED TIMELINE".
2. **Observation vs inference vs assumption** must be separate fields on every agent message. Never merge them.
3. **Uncertainty is first-class.** Identity matches are `accepted | ambiguous | rejected`. Ambiguous matches are never silently merged.
4. **Every agent decision is a message** on the bus with `caused_by` and `evidence`. The ledger is append-only and hash-chained.
5. Scores from heuristics are **not probabilities**. Label them `score`, not `probability`, unless calibrated.
6. Keep modules small and typed (Python type hints, TypeScript strict). Write tests for each phase.
7. Do not delete existing working code without replacing it. Existing assets: `intelligence.py` (message bus, agents, cases), `replay_pipeline.py` (HOG + centroid tracker), `server.py` (SQLite, HMAC ingest, old specialists), `web/` (experimental shell to be **replaced**), `tests/`.
8. Only process footage the user owns or is permitted to process. Local-only: bind to 127.0.0.1.

---

## 1. PRODUCT IN ONE PARAGRAPH

Every camera is an agent. Camera agents detect and track people, build compact observations, and negotiate identity handoffs with neighbouring cameras. Specialist agents (Behaviour, Queue, Security, Business Ops) investigate events. An Orchestrator opens evidence-backed **cases**. A workspace shows the agents' collaboration, a live store map, the journey of each global entity, and lets a human confirm, reject, replay and question decisions. Security (RBAC, privacy masking, tamper-evident audit, camera-health checks) is part of the architecture.

Target story the demo must tell:

> Entity E-07 entered via Camera 1, moved into the aisle, dwelt near a shelf longer than expected, left Camera 2's view, was reacquired by Camera 3 near checkout, and a review case was opened with supporting evidence and alternative explanations.

---

## 2. INPUTS: THE THREE CAMERAS

The user has **3 video files showing movement** (filenames TBD, placed in `data/videos/`). The system must work with **N cameras defined in config**, with N=3 for the demo.

### 2.1 Phase 0 discovery (mandatory first step)
Write `tools/inspect_videos.py` that, for every video, prints: resolution, fps, frame count, duration, codec, and saves a contact sheet (9 evenly spaced frames) to `data/inspect/<cam>.jpg`. Also run a quick person-detection pass and report: how many people appear, how long, whether people appear to walk from one camera's scene into another's, and whether any footage overlaps visually. **Show the user the contact sheets and ask them to confirm**: (a) the physical relationship between cameras (adjacent? overlapping? sequential?), (b) which camera is the entrance, (c) are the videos recorded simultaneously.

### 2.2 `config/cameras.yaml` (single source of truth)
```yaml
store_clock_start: "2026-01-01T10:00:00"   # arbitrary reference
cameras:
  - id: CAM-01
    name: Entrance
    file: data/videos/cam1.mp4
    clock_offset_s: 0.0          # offset onto the shared store clock
    zones_px: config/zones/cam1.json   # polygons in pixel space
    homography: config/calib/cam1.json # pixel -> floor (metres or map units)
    neighbours: [CAM-02]
    edges:                        # image edges where people leave/enter toward neighbours
      - {side: right, leads_to: CAM-02}
  - id: CAM-02 ...
  - id: CAM-03 ...
floorplan: config/floorplan.json   # width/height, zones polygons, camera positions + FOV cones
```

### 2.3 Timeline modes (the honest part)
- **SYNC mode**: the videos were recorded simultaneously. Use real timestamps.
- **COMPOSED mode**: videos are separate or sequential clips. Place them on a shared store clock using `clock_offset_s` so that a person leaving cam N plausibly appears in cam N+1 after a transit gap. The UI must show a visible badge "COMPOSED TIMELINE — clips aligned manually" and the evaluation section must state that cross-camera results are an integration test, not a benchmark.
Implement both; select by `mode:` in config.

---

## 3. TECH STACK (fixed unless a blocker is found)

- Python 3.11, FastAPI + Uvicorn, WebSocket + SSE, SQLite (WAL), Pydantic v2 models.
- Perception: `ultralytics` YOLO (person class; note AGPL licence in README) with its built-in ByteTrack; OpenCV for I/O. Re-ID embeddings: `torchreid` OSNet (preferred) or fallback to a DINOv2/CLIP image embedding via `torch`; last-resort fallback: HSV histograms (keep existing code as the baseline for comparison).
- Frontend: Vite + React + TypeScript, Zustand for state, HTML canvas + SVG (d3-scale/d3-shape only) for the map and thread view. No heavy chart dashboard libraries. Video via HTML `<video>` with a canvas overlay (boxes are drawn from JSON, not burned into the video, so privacy masking can be toggled live).
- Tests: pytest, Playwright for 2–3 UI smoke tests.
- One-command run: `./run.sh` (creates venv, installs, runs pipeline if outputs are missing, starts server).

---

## 4. REPOSITORY STRUCTURE

```text
apn/
  config/              cameras.yaml  floorplan.json  zones/  calib/  thresholds.yaml  roles.yaml
  data/videos/         (user footage)
  apn/
    core/              bus.py  protocol.py  ledger.py (hash chain)  memory.py  clock.py
    perception/        detector.py  tracker.py  reid.py  floor.py  zones.py  pipeline.py
    agents/            base.py camera.py tracking.py handoff.py identity.py behaviour.py
                       queue.py security.py business_ops.py evidence.py privacy.py
                       health.py orchestrator.py
    cases/             models.py  builder.py  hypotheses.py
    security/          auth.py  rbac.py  redact.py  audit.py
    api/               main.py  routes_*.py  ws.py
    store/             db.py  schema.sql  repositories.py
  tools/               inspect_videos.py  calibrate.py  make_scenario.py  export_case.py
  eval/                metrics.py  run_eval.py  groundtruth/
  web/                 (React app, see §10)
  tests/
  docs/                ARCHITECTURE.md  PROTOCOL.md  EVALUATION.md  THREAT_MODEL.md
  run.sh  README.md
```

---

## 5. DATA CONTRACTS

### 5.1 Message envelope (all agent communication)
```json
{
  "id": "MSG-000123",
  "type": "observation | track.updated | handoff.request | handoff.offer | handoff.response | identity.link | identity.unlink | zone.event | hypothesis | finding | case.opened | case.updated | evidence.attached | human.decision | health.alert | privacy.action | agent.error",
  "sender": "camera-agent:CAM-02",
  "ts_source": 12.48,
  "ts_ingest": 1767262812.5,
  "payload": {},
  "observed": {},
  "inferred": {},
  "assumptions": [],
  "confidence": 0.0,
  "evidence": ["FRAME:CAM-02:300", "MSG-000101"],
  "caused_by": "MSG-000118",
  "visibility_role": ["security_operator","investigator","admin"],
  "prev_hash": "…", "hash": "…"
}
```
`hash = SHA256(prev_hash + canonical_json(message_without_hash))`. Provide `verify_chain()` and a test that tampering with any row is detected.

### 5.2 Observation (from camera agent, per tracked person per processed frame)
`camera_id, local_track_id, ts_source, store_ts, frame_idx, bbox_px[4], foot_px[2], foot_floor[2] (nullable if uncalibrated), zone, velocity_floor, heading_deg, detector_score, embedding_ref, crop_ref, quality {blur, occlusion_est, size_px}`.

### 5.3 Entities
- `LocalTrack`: camera_id, local_track_id, first/last ts, observations, mean embedding (quality-weighted), zone history, status (active/lost/exited), exit_edge, last_foot_floor, last_velocity.
- `GlobalEntity`: `entity_id` (E-001…), member local tracks, link records (each link keeps score components and decision state), status, anonymised display label, first/last seen, journey (ordered zone/camera segments).

### 5.4 Case
`case_id, kind, severity (info|attention|high), urgency 0–1, state (open|investigating|needs_human|confirmed|dismissed|closed), entity_id, zone, camera_ids, opened_at, timeline[], hypotheses[ {id, label, supporting[], contradicting[], score} ], findings[], evidence[], alternative_explanations[], recommended_response, human_decisions[], trace[] (message ids), narrative (generated from facts only)`.

---

## 6. PHASES (each with deliverables and acceptance criteria)

### Phase 0 — Discovery & config
Deliver: `inspect_videos.py`, contact sheets, `cameras.yaml` draft, a written summary of the footage and the chosen timeline mode.
Accept: user confirms camera relationships; config loads and validates (Pydantic).

### Phase 1 — Core runtime and protocol
Deliver: `bus.py` (async pub/sub, deterministic ordering in replay), `protocol.py` (Pydantic models for every message type), `ledger.py` (hash chain, persisted), merge/refactor of `intelligence.py` into `apn/core` + `apn/agents` **so `server.py`'s duplicate specialist logic is removed**. Add replay clock (play/pause/seek/speed).
Accept: tests — chain verification, tamper detection, causal chain query (`trace(msg_id)` returns ancestors back to the first observation), deterministic replay gives identical ledgers.

### Phase 2 — Perception pipeline
Deliver: detector wrapper (YOLO person), ByteTrack local tracking, per-detection crops saved (`data/crops/…`, retained per policy), Re-ID embeddings, quality scoring, zone assignment from polygons, speed/heading from floor coordinates. Output `observations.parquet`/JSON + ledger messages. Keep the old HOG pipeline selectable (`--detector hog`) as the **baseline for evaluation**.
Accept: runs on all 3 videos at ≥ real-time/2 on CPU (or document GPU need); every observation has bbox, foot point, zone, embedding ref; overlay-render test.

### Phase 3 — Calibration and floor map
Deliver: `tools/calibrate.py` — a simple web or OpenCV tool: user clicks ≥4 floor points per camera on a frame and the matching points on the floorplan; saves a homography. Draw zone polygons on camera frames; save in pixel space and projected floor space. `floorplan.json` with zones: Entrance, Main Aisle, Shelves, Service Counter, Checkout, Exit, Restricted (staff-only). Camera positions and FOV cones.
Accept: projecting foot points of a known walking path yields a smooth trajectory on the map; mark residual error. If calibration is skipped, fall back to normalised image coordinates and label the map "approximate".

### Phase 4 — Camera agents and event intelligence
Each Camera Agent (one instance per camera) subscribes to its perception stream and publishes: `observation`, `track.updated`, `zone.event` (entered/exited zone, with dwell), `exit.predicted` (track approaching a configured edge, with heading and ETA). Short-term memory: last 10 s of each track. Camera Agent exposes status: fps processed, active tracks, last heartbeat.
Accept: unit tests with synthetic tracks for zone entry/exit, dwell timers, edge prediction.

### Phase 5 — Handoff and identity (the core contribution)
**Handoff Agent** on `exit.predicted` or track loss near an edge publishes `handoff.request`:
`{source_camera, source_track, embedding, last_foot_floor, exit_dir, ts, candidate_cameras[], expiry_s, minimal_disclosure: true}`. Minimal disclosure: send embedding + kinematics only, **never crops**, unless escalated by a human.
**Candidate Camera Agents** compare against newly appearing tracks within a time window and reply `handoff.offer` with component scores:
- appearance: cosine similarity of quality-weighted embeddings
- temporal: plausibility of transit time given distance/walk speed (Gaussian around expected)
- spatial: entry position/heading compatible with source exit edge
- topology: camera adjacency / zone connectivity
- exclusivity: penalise if candidate is already strongly linked elsewhere
`score = Σ w_i·component_i` with weights in `thresholds.yaml`. Compute `margin = best − runner_up`.
**Identity Agent** decides: `accepted` if score ≥ T_acc and margin ≥ M_acc; `ambiguous` if score ≥ T_amb; else `rejected`. Accepted → `identity.link` merges into a `GlobalEntity` (union-find with link provenance). Ambiguous → keep **fork**, expose both candidates, count identities as bounds [min,max]. A `human.decision` can confirm/reject; rejecting must split entities and re-run dependent findings (`identity.unlink` + recompute).
Conflict handling: if two requests claim the same candidate, run a small assignment (Hungarian) with the exclusivity term.
Accept: tests for accept/ambiguous/reject paths, unlink recompute, minimal-disclosure assertion (no crop bytes in handoff messages), comparison script reporting baseline HSV vs embedding approach on the available footage (report honestly if footage cannot validate).

### Phase 6 — Specialist agents
All configurable in `thresholds.yaml`; each publishes `hypothesis`/`finding` with measurements and confidence.
- **Behaviour Agent**: dwell > threshold per zone type; loitering (low displacement over window); pacing/backtracking (path revisits); against-flow movement (heading vs zone's expected flow vector); sudden stop; running. Dwell is **never** labelled theft; it emits a hypothesis set: `needs_assistance`, `comparing_products`, `congestion_wait`, `suspicious_behaviour`, each with supporting/contradicting facts.
- **Queue Agent**: person count and density in the checkout/service polygons, queue length estimate, per-entity wait time (from entering queue polygon until service/exit), trend (growing/stable/draining), service-counter idle time.
- **Security Agent**: restricted-zone entry, entering from exit-only direction, abandoned object (stationary object-like blob / bag class if detected, no nearby person for X s — mark as low-confidence experimental if only YOLO generic classes available), possible concealment cue (only as a *low-weight cue* from sustained shelf proximity + body-occlusion pattern; clearly labelled "unverified cue", never a conclusion).
- **Business Ops Agent**: unattended service counter, checkout bottleneck, wait-time breach, understaffed-zone recommendation (a *suggestion* to a human, never an action).
Accept: each rule has unit tests with synthetic trajectories; each finding includes thresholds and measured values.

### Phase 7 — Evidence, cases, orchestrator
- **Evidence Agent**: given an entity and time window, collects best-quality crops per camera, a short clip reference per camera (start/end source time), the track path, and the relevant message ids. Produces an evidence bundle with thumbnails; respects privacy policy.
- **Orchestrator**: subscribes to findings, deduplicates, routes to specialists for corroboration, detects disagreement (e.g. Behaviour says suspicious, Business Ops says counter unattended explains the wait), scores urgency (severity × confidence × persistence × zone risk), decides `notify human | keep monitoring | dismiss as normal`, and closes cases. Generates `narrative` strictly from structured facts via templates (no free-form hallucination); optionally an LLM summariser may be plugged in behind a flag, must be given only structured facts, and its output is marked "generated summary".
- **Why-endpoint**: `GET /cases/{id}/why` returns the causal chain (message trace), the thresholds crossed, alternative hypotheses and what evidence would change the conclusion.
Accept: end-to-end replay produces at least one coherent case for the target scenario, with timeline across ≥2 cameras and ≥2 competing hypotheses.

### Phase 8 — Security, privacy, health
- **Auth/RBAC**: roles Administrator, Security Operator, Business Operations, Investigator, Auditor in `roles.yaml` mapping to permissions (view_raw_video, view_masked_video, view_cases, decide, adjust_thresholds, manage_agents, view_audit, export). Local session tokens; per-agent identities with signed messages (HMAC or Ed25519) so injected observations fail verification.
- **Privacy Agent**: modes `raw | masked | metadata_only`. Masking = blur the upper ~22% of every person box (head/face proxy) and optionally the entire silhouette to a coloured shape; applied server-side to served crops and client-side to overlay. Anonymous entity labels. Retention policy (e.g. crops deleted after N hours) with a purge job and an audit entry.
- **Audit**: hash-chained ledger + `/audit/verify`. UI shows a green "chain intact" or red tamper marker.
- **Health Agent**: detects frozen feed (frame diff ≈ 0 for N s), obstruction (sudden global brightness/variance drop), viewpoint shift (feature homography between reference and current frame), replayed footage (duplicate frame-hash sequence), agent silence (missing heartbeat), message anomalies (rate spikes, malformed signature, observation teleporting faster than humanly possible). Emits `health.alert` and lowers dependent confidence.
- Provide `tools/attack_demo.py`: injects a forged observation, a frozen feed and a replayed clip, and show the system detecting each.
Accept: tests for RBAC denial, signature rejection, tamper detection, each health detector on synthetic perturbations of the real videos.

### Phase 9 — API
REST + WebSocket (all under `/api`, token required):
`GET /state`, `GET /cameras`, `GET /entities`, `GET /entities/{id}/journey`, `GET /tracks/{id}`, `GET /cases`, `GET /cases/{id}`, `GET /cases/{id}/why`, `POST /cases/{id}/decision`, `POST /handoffs/{id}/decision`, `POST /agents/{id}/pause|isolate|resume`, `PATCH /thresholds`, `POST /ask` (question to an agent: returns the explanation built from ledger facts), `GET /audit`, `GET /audit/verify`, `POST /replay/{play|pause|seek|speed}`, `GET /video/{camera}` (range requests, role-checked), `GET /crop/{id}` (role-checked/masked), `WS /stream` (live messages, track positions at ~10 Hz, replay clock).
Accept: OpenAPI docs render; permission tests per role.

### Phase 10 — Workspace UI (see §7)

### Phase 11 — Evaluation and docs
Deliver `eval/run_eval.py` and `docs/EVALUATION.md`: hand-label a small ground truth (track identities across the 3 cameras for the clips, using a simple labelling tool or a CSV), compute IDF1 / ID switches / handoff precision & recall / false-merge rate for: (A) HOG+HSV baseline, (B) YOLO+ByteTrack+embedding, (C) full handoff negotiation with margin test. Report limitations honestly (footage size, composed timeline). Also write `THREAT_MODEL.md` and `PROTOCOL.md` (message types, minimal disclosure, conflict resolution; this is the novelty write-up).

---

## 7. WORKSPACE UI SPECIFICATION

Design language: dark, calm, instrument-like ("operations room"), not a chart dashboard. One accent colour per meaning: teal = observed fact, amber = inferred/uncertain, violet = assumption, red = risk, grey = inactive. Typography: a monospace for ids/timestamps, a clean sans for text. Motion only where it carries meaning (a message travelling between agents, a trail fading). Respect `prefers-reduced-motion`.

Global layout: left rail (agents + camera list), centre stage (switchable lenses), right panel (case file / inspector), bottom (replay scrubber and agent activity stream).

**Header strip**: store clock, mode badge (SYNC or COMPOSED TIMELINE), role selector, privacy mode toggle, audit chain status, replay controls.

**Centre-stage views (tabs/lenses on the same data):**

1. **Store Twin (default)** — top-down floorplan, zone polygons labelled, camera icons with FOV cones that pulse when a camera sees someone. People are nodes at their projected floor position with fading trails; colour = state (normal, dwelling, alert), ring thickness = confidence; dashed ghost = lost track predicted forward; handoff arcs between cameras animate when requests/offers fly; clicking a node opens the Inspector.
2. **Entity Thread** — one horizontal "metro line" per global entity; stations = cameras/zones; interchanges = handoffs. Ambiguous handoffs draw as a fork with both candidates and their scores; confirm/reject collapses the fork. Dwell shown as stretched stations. Click a segment → jumps replay to that time.
3. **Agent Constellation** — agents as nodes on rings (cameras outer ring, specialists inner, orchestrator centre). Messages are particles along edges; colour by type. Click a particle/message → highlights its full `caused_by` chain and shows envelope fields including observed / inferred / assumptions.
4. **Perception View** — selected camera video with canvas overlay: boxes, track ids, zone polygons, motion trails, predicted-exit arrows, a side panel with current observations and camera-agent status (fps, tracks, last heartbeat, health).
5. **Handoff Court** — exit crop (or masked silhouette depending on role) beside ranked candidates; each candidate shows component bars (appearance, temporal, spatial, topology, exclusivity), score, margin; buttons Accept / Reject / Can't tell; submitting writes a `human.decision` and visibly updates entity links.
6. **Case Board** — case header (severity, urgency, state), generated narrative, cross-camera timeline with synchronised thumbnails, hypothesis panel (side-by-side bars with supporting/contradicting facts), alternative explanations, recommended response, evidence wall, action bar (Approve / Dismiss / Mark normal / Mark suspicious / Escalate / Ask why).
7. **Reasoning Replay** — a scrubber that rewinds video **and** system state: what each agent knew at time t, which messages existed, which links were provisional.
8. **Control & Security Room** — agent list with pause/isolate buttons and heartbeat; threshold sliders (with an "impact preview": how many findings would change), role/permission matrix, audit log with verify button, health alerts, privacy mode status, attack-demo triggers.

**Agent activity stream** (always visible bottom) — human-readable lines generated from messages, e.g. `Camera Agent 02 found a possible match (0.81, margin 0.12) → Identity Agent linked E-07`. Click to open that message's trace.

**Interactions that must work:** select entity (highlights across all views), scrub/seek, pause an agent and see downstream confidence drop, reject a match and watch the entity split and cases recompute, change role and see raw video disappear, toggle masking, ask an agent "why" (answer built from ledger facts with links).

Empty/error states: no footage, camera offline (greyed zone + coverage-gap hatch), calibration missing ("approximate positions").

---

## 8. DEMO SCENARIO SCRIPT

Define `scenarios/scenario_01.yaml` that records the expected outcome so the demo is reproducible and testable:

1. Entity enters CAM-01 (Entrance) → local track created.
2. Track approaches the CAM-01 edge toward CAM-02 → `exit.predicted`, `handoff.request`.
3. CAM-02 offers a candidate → Identity links → `E-001`.
4. Entity dwells in the aisle zone beyond threshold → Behaviour hypotheses.
5. Entity leaves CAM-02 view, reappears on CAM-03 near Checkout → second handoff (make one ambiguous on purpose if the footage allows, to demonstrate the Handoff Court).
6. Queue Agent reports checkout count/wait time.
7. Orchestrator opens a case; Evidence Agent attaches crops/clips from all 3 cameras.
8. Operator opens the case, replays the journey, asks "why", confirms a match, dismisses or escalates.
9. Audit verify passes; a forged observation injected by the attack demo is rejected.

The scenario test asserts these message sequences exist in the ledger in causal order.

---

## 9. THRESHOLDS (`config/thresholds.yaml`, all runtime-adjustable and audited)

```yaml
detector: {conf: 0.35, imgsz: 960, process_every_n_frames: 2}
tracking: {track_buffer_s: 3.0}
dwell_s: {shelf: 20, main_aisle: 30, service: 45, checkout: 60, entrance: 15}
loiter: {window_s: 30, max_displacement_m: 1.5}
handoff:
  weights: {appearance: 0.45, temporal: 0.20, spatial: 0.15, topology: 0.10, exclusivity: 0.10}
  T_accept: 0.80
  M_accept: 0.10
  T_ambiguous: 0.62
  max_transit_s: 20
queue: {queue_len_alert: 4, wait_alert_s: 90}
health: {frozen_s: 3, brightness_drop: 0.5, heartbeat_timeout_s: 5}
privacy: {mode: masked, crop_retention_hours: 24}
```
Tune these on the real footage and record the final values and rationale in EVALUATION.md.

---

## 10. TESTING MATRIX

Unit: protocol validation, hash chain, zone geometry, homography projection, dwell/loiter/queue rules, handoff scoring and decisions, RBAC, signature checks, health detectors.
Integration: full replay of the 3 videos produces expected ledger shape; determinism; scenario assertions.
UI: Playwright — loads, role switch hides raw video, reject-match splits entity, why-panel opens a trace.
Performance: report fps per stage and end-to-end latency in EVALUATION.md.

---

## 11. DEFINITION OF DONE

- `./run.sh` starts everything and the workspace opens with the 3-camera replay.
- The target scenario plays end to end with real pipeline outputs.
- At least one ambiguous handoff can be resolved by a human and the consequences propagate.
- A case shows hypotheses, alternative explanations, evidence, and a working "why" trace.
- Privacy masking and role restrictions demonstrably work.
- Tamper and injection attacks are detected in the attack demo.
- Docs, protocol write-up, threat model and honest evaluation are complete.

## 12. THINGS NOT TO DO

- Do not claim biometric/facial recognition; use anonymous appearance embeddings only.
- Do not label anyone a thief; output cues and hypotheses for human review.
- Do not present composed-timeline cross-camera matches as benchmark results.
- Do not store raw footage or crops longer than the retention policy.
- Do not add cloud calls; everything is local.
- Do not make agents take external actions (messages, staffing changes); recommendations only.
- Do not make novelty or patent claims in docs; state "protocol design candidate pending prior-art review".

---

## 13. FIRST MESSAGE TO SEND AFTER PASTING THIS SPEC

"Begin Phase 0. Inspect the three videos in data/videos, generate contact sheets and the draft cameras.yaml, then show me what you found and ask me the questions in §2.1. Do not start Phase 1 until I answer."
