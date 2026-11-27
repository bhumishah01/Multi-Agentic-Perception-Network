# Multi-Agentic Perception Network (APN)

APN is a privacy-conscious, camera-to-decision system for supermarket operations. It converts surveillance video into anonymous movement observations, coordinates specialist agents, answers operational questions, and preserves the evidence behind every recommendation.

The project is designed as a final-year major project and an extensible research prototype—not as a collection of dashboard mock-ups.

## The problem

Retailers already own cameras, but most camera systems only record incidents for later review. Store managers still depend on manual observation, disconnected reports and intuition to answer daily questions:

- Where is customer movement slowing down?
- Which aisle needs assistance right now?
- Is checkout pressure increasing?
- Where are routes blocked or shelves difficult to access?
- What changed after a staffing or layout decision?
- Can a finding be traced back to the exact footage and model evidence?

Existing video analytics commonly stop at detection counts. Business dashboards commonly show aggregated numbers without explaining where they came from. APN connects these two sides: camera evidence becomes an explainable, question-driven operational decision.

## The solution

APN adds an intelligence layer to a store’s existing camera network. Each camera produces privacy-protected local observations. Specialist agents interpret movement, queues, dwell, safety and business context. A master orchestrator selects the required agents for a manager’s question, verifies their evidence and returns an answer with boundaries and recommended next steps.

Two workspaces serve different users:

| Workspace | User | Purpose |
|---|---|---|
| Manager workspace | Store manager / business owner | Ask questions, see current operating signals, review recommendations, plan staffing and experiments |
| Technical evidence laboratory | Engineer / reviewer / security operator | Inspect footage, detections, provenance, agent reasoning, uncertainty, robustness and audit state |

This separation prevents technical diagnostics from overwhelming the manager while keeping every business conclusion inspectable.

## Why APN is novel

APN is not only a detector and not only a dashboard. Its contribution is the combination of:

1. **Prompt-to-evidence retail intelligence** — a manager asks a natural-language question and receives an answer scoped to the selected camera and evidence window.
2. **Visible multi-agent reasoning** — camera, tracking, movement, queue, business and evidence agents are selected according to the question rather than running a fixed response template.
3. **Uncertainty-preserving cross-camera memory** — handoffs are ranked and retained as accepted, ambiguous or rejected; APN does not silently invent a global identity.
4. **Business and technical separation** — recommendations are simple for operators, while provenance, model health and failure modes remain available to reviewers.
5. **Privacy and security by design** — anonymous local IDs, face masking, minimal-disclosure messages, RBAC, retention controls and a hash-chained ledger are part of the system architecture.
6. **Closed-loop operational learning** — APN can propose a controlled intervention, record human approval and compare the next evidence window without directly changing store operations.
7. **Resilience as an agentic advantage** — the laboratory compares centralised and distributed behaviour under camera loss, message delay, ambiguous handoffs and forged observations.

## End-to-end operating flow

### 1. Discover and register footage

APN scans the configured surveillance directory, ignores operating-system sidecars, fingerprints each video and maps it to a camera role. New or changed files trigger catalogue and reel updates.

### 2. Build camera-role reels

Multiple clips from the same store area are assembled into role-specific replay reels while retaining exact clip-to-reel provenance.

### 3. Run perception

YOLO detects people; ByteTrack maintains camera-local tracks. The pipeline records timestamps, bounding boxes, foot points, zones, appearance references and evidence crops.

### 4. Apply privacy controls

The interface masks face regions and operates on anonymous track IDs. APN does not use face recognition or store claimed personal identities.

### 5. Create spatial and temporal memory

Camera agents maintain recent local-track observations, dwell windows, movement direction, exits and candidate next-camera transitions.

### 6. Negotiate cross-camera handoffs

Handoff and identity agents rank candidates using time, topology, movement and appearance evidence. A margin test prevents weak candidates from being treated as confirmed identities.

### 7. Produce specialist findings

Movement, queue, safety, business and evidence specialists analyse the relevant observation set. Each finding carries its supporting facts, assumptions, confidence and alternatives.

### 8. Ask the store

The manager selects an evidence zone and asks a question such as “How many customers were in aisle one?” APN compiles an agent plan and answers from the current observation window.

### 9. Recommend—not silently execute

APN can recommend assistance, checkout capacity, safety inspection or a controlled placement experiment. Operational changes require human approval.

### 10. Verify and audit

The system preserves the source window, messages, decisions and report in its audit trail. Technical reviewers can reproduce how the conclusion was reached.

## What APN does

```text
Surveillance footage
        ↓
Person detection + local tracking + privacy masking
        ↓
Camera agents + movement memory + uncertain handoff negotiation
        ↓
Business, queue, safety and evidence specialists
        ↓
Master orchestrator + verification
        ↓
Manager workspace / technical evidence laboratory / audit report
```

Current capabilities include:

- automatic discovery of supermarket videos from an external drive;
- YOLO11 person detection and ByteTrack camera-local tracking;
- face-region privacy masking without biometric identification;
- anonymous movement, dwell, occupancy and queue observations;
- multi-agent investigation with evidence-bound answers;
- manager questions scoped to a selected camera and replay window;
- cross-camera candidate ranking with explicit uncertainty;
- operational recommendations, what-if simulations and reports;
- role-based access, health monitoring and a tamper-evident audit ledger;
- light and dark manager and technical workspaces.

## Feature catalogue

### Manager and business intelligence

- prompt-led store investigation;
- moving replay-window metrics sourced from the observation ledger;
- rush and checkout-pressure review;
- aisle and zone comparison;
- customer-journey hypotheses with uncertainty labels;
- lost-opportunity and assistance-review signals;
- product-interest model-readiness funnel;
- scenario-aware placement experiment planner;
- staff coverage and counter-capacity simulation;
- weekday/weekend comparative planning;
- operational notification centre and live change pop-ups;
- evidence-linked owner reports.

### Computer vision and perception

- video discovery, fingerprinting and camera assignment;
- YOLO11 person detection;
- ByteTrack camera-local tracking;
- OpenCV baseline for controlled comparison;
- zone, dwell, occupancy and motion observations;
- privacy-masked evidence crops;
- image-plane heatmaps and local-track paths;
- floor projection and calibration API;
- exact source-clip and timestamp provenance.

### Multi-agent framework

- typed asynchronous message bus;
- camera agents with local memory;
- exit prediction and adjacency-aware candidate generation;
- handoff negotiation and identity-component recomputation;
- movement, queue, safety, business and evidence specialists;
- master orchestration based on question intent;
- competing hypotheses and alternative explanations;
- evidence verifier and human-review states;
- persistent operator accept/reject decisions.

### Security and governance

- no face recognition;
- local anonymous track identifiers;
- face-region masking;
- role-based access control;
- bearer-authenticated local API;
- minimal-disclosure inter-agent messages;
- configurable evidence retention and purge;
- SHA-256 hash-chained audit ledger;
- forged-observation, frozen-feed and replay detection exercises;
- explicit evidence and deployment boundaries.

### Technical and evaluation laboratory

- selectable camera roles and individual source clips;
- detection overlays and observation queue;
- agent-delegation and verification theatre;
- cross-camera trajectory graph;
- traffic heatmap and passage funnel;
- controllable queue digital twin;
- camera-loss, delay and ambiguity incident injection;
- centralised-versus-agentic robustness comparison;
- automated backend and browser verification.

## Client value

For a real store deployment, APN is intended to reduce manual camera review and shorten the path from observation to action:

- use existing camera infrastructure rather than installing a new sensor network;
- surface assistance and congestion cues while they are operationally relevant;
- support staffing and checkout decisions with traceable evidence;
- evaluate layout changes as controlled experiments rather than assumptions;
- keep privacy, uncertainty and human approval visible;
- give technical teams a reproducible explanation for every manager-facing output.

APN is software-only at the application layer. Production deployment would connect RTSP/NVR streams, store-specific zones, synchronized clocks, POS or inventory data where authorised, and a consented evaluation dataset.

## Run locally

Requirements: macOS/Linux, Python 3.11+, Node.js, FFmpeg and the project surveillance drive when original clips are required.

```bash
cd apn
./run.sh
```

Then open [http://127.0.0.1:8766](http://127.0.0.1:8766).

`run.sh` validates the backend, discovers footage, rebuilds changed camera reels, runs perception when the media fingerprint changes, builds the web application and starts the API. If the external drive is unavailable, APN starts from its cached camera-role reels and marks original source feeds unavailable.

## Surveillance layout

Original media is kept outside Git at:

```text
/Volumes/One Touch/SURVELLIANCE /SUPERMARKET FINAL
```

The current controlled validation pack contains 14 clips assigned to four operational camera roles:

| Role | Area | Files |
|---|---|---|
| CAM-01 | Entrance and produce | `CAM-01_01.mp4`–`CAM-01_02.mp4` |
| CAM-02 | Grocery aisles | `CAM-02_01.mp4`–`CAM-02_07.mp4` |
| CAM-03 | Promotions and assistance | `CAM-03_01.mp4`–`CAM-03_03.mp4` |
| CAM-04 | Checkout and exit | `CAM-04_01.mp4`–`CAM-04_02.mp4` |

The pack is suitable for system integration and repeatable evaluation. It is not represented as synchronized production CCTV or as identity ground truth. APN keeps this limitation visible because evidence provenance is part of the project’s security model.

## Repository map

```text
apn/
├── apn/                 # production Python package
│   ├── agents/          # camera, handoff, identity and specialist agents
│   ├── api/             # FastAPI service
│   ├── business/        # analytics, simulation and reporting
│   ├── core/            # protocol, bus, replay clock and audit ledger
│   ├── perception/      # detection, tracking, zones and projection
│   ├── security/        # RBAC, privacy, health and retention
│   └── store/           # runtime state and decisions
├── config/              # cameras, zones, thresholds and roles
├── docs/                # architecture, protocol, threat model and evaluation
├── eval/                # evaluation runner and declared ground truth
├── scenarios/           # reproducible investigation scenarios
├── tests/               # backend and end-to-end tests
├── tools/               # ingestion, perception, calibration and verification
├── web2/                # active React interface
└── run.sh               # complete local entry point
```

Detailed documentation begins at [apn/docs/README.md](apn/docs/README.md).

## Verification

```bash
cd apn
.venv/bin/python -m unittest discover -s tests -v
cd web2 && npm run build && npm run test:ui
```

The current suite covers the perception runtime, agent protocol, security boundaries, business analytics, API and manager/technical user journeys.

## Evidence boundary

APN reports observations supported by processed video: detections, camera-local tracks, visible duration, movement, zones and occupancy. It does not claim a person’s identity, purchase, intent or commercial outcome without the required evidence source. Cross-camera matches remain accepted, ambiguous or rejected rather than being silently forced.

## Technology

Python, FastAPI, OpenCV, Ultralytics YOLO, ByteTrack, React, TypeScript, Vite and Playwright.

> Ultralytics is distributed under AGPL-3.0. Review its licence before distributing or commercialising this build.
