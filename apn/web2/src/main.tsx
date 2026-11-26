import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
const TOKEN = "apn-local-demo";
const headers = {
  Authorization: `Bearer ${TOKEN}`,
  "X-APN-Role": "Security Operator",
};
const api = async (path: string, options: RequestInit = {}) => {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  if (!response.ok) throw Error(`${response.status} ${await response.text()}`);
  return response.json();
};
type Camera = {
  id: string;
  name: string;
  clock_offset_s: number;
  agent_state: string;
};
type Observation = {
  camera_id: string;
  local_track_id: string;
  ts_source: number;
  store_ts: number;
  bbox_px: number[];
  confidence: number;
  zone?: string;
};
type State = {
  timeline_label: string;
  cameras: Camera[];
  summary: any;
  handoffs: any[];
  cases: any[];
  messages: any[];
  media: MediaCatalog;
};
type MediaCatalog = {
  source_directory: string;
  discovered_files: number;
  assigned_files: number;
  unassigned_files: number;
  disclosure: string;
  reels: { camera_id: string; name: string; duration_s: number; clip_count: number; segments: any[] }[];
};
type AskResult = {
  answer: string;
  facts: any;
  agents: string[];
  trace: string[];
  boundary: string;
  insights: string[];
  recommendation: string;
};
function Surveillance({
  camera,
  observations,
  privacy,
  onTime,
}: {
  camera: Camera;
  observations: Observation[];
  privacy: boolean;
  onTime: (n: number) => void;
}) {
  const video = useRef<HTMLVideoElement>(null),
    canvas = useRef<HTMLCanvasElement>(null),
    [ready, setReady] = useState(false);
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    v.load();
    v.play().catch(() => {});
    setReady(false);
  }, [camera.id]);
  useEffect(() => {
    let frame = 0;
    const paint = () => {
      const v = video.current,
        c = canvas.current;
      if (v && c && v.readyState >= 2) {
        const w = v.videoWidth || 1280,
          h = v.videoHeight || 720;
        if (c.width !== w || c.height !== h) {
          c.width = w;
          c.height = h;
        }
        const ctx = c.getContext("2d")!;
        ctx.drawImage(v, 0, 0, w, h);
        const t = v.currentTime;
        onTime(t);
        const nearest = observations.reduce(
          (best, row) =>
            Math.abs(row.ts_source - t) < Math.abs((best?.ts_source ?? 999) - t)
              ? row
              : best,
          undefined as Observation | undefined,
        );
        const active = nearest
          ? observations.filter(
              (row) => Math.abs(row.ts_source - nearest.ts_source) < 0.001,
            )
          : [];
        for (const row of active) {
          const [x1, y1, x2, y2] = row.bbox_px;
          ctx.strokeStyle = "#63f5d2";
          ctx.lineWidth = Math.max(2, w / 500);
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.fillStyle = "rgba(3,16,14,.86)";
          ctx.fillRect(x1, y1 - 24, Math.max(105, x2 - x1), 22);
          ctx.fillStyle = "#bfffee";
          ctx.font = `${Math.max(12, w / 80)}px ui-monospace`;
          ctx.fillText(row.local_track_id, x1 + 5, y1 - 8);
          if (privacy) {
            const fw = Math.max(6, Math.floor((x2 - x1) / 12)),
              fh = Math.max(6, Math.floor(((y2 - y1) * 0.23) / 8));
            const off = document.createElement("canvas");
            off.width = fw;
            off.height = fh;
            const ox = off.getContext("2d")!;
            ox.drawImage(v, x1, y1, x2 - x1, (y2 - y1) * 0.23, 0, 0, fw, fh);
            ctx.imageSmoothingEnabled = false;
            ctx.drawImage(off, 0, 0, fw, fh, x1, y1, x2 - x1, (y2 - y1) * 0.23);
            ctx.imageSmoothingEnabled = true;
            ctx.strokeStyle = "#f3b64c";
            ctx.strokeRect(x1, y1, x2 - x1, (y2 - y1) * 0.23);
          }
        }
      }
      frame = requestAnimationFrame(paint);
    };
    frame = requestAnimationFrame(paint);
    return () => cancelAnimationFrame(frame);
  }, [observations, privacy, onTime]);
  return (
    <div className="surveillance">
      <video
        ref={video}
        src={`/api/video/${camera.id}?token=${TOKEN}`}
        muted
        autoPlay
        loop
        playsInline
        onCanPlay={() => {
          setReady(true);
          video.current?.play().catch(() => {});
        }}
      />
      <canvas ref={canvas} />
      {!ready && (
        <div className="videoLoading">
          <span />
          Loading surveillance…
        </div>
      )}
      <div className="videoStamp">
        <b>LIVE REPLAY</b>
        <span>
          {camera.id} · {camera.name}
        </span>
      </div>
      <div className="videoLegend">
        <span className="boxIcon" /> Anonymous tracking box{" "}
        <span className="blurIcon" /> Privacy mask
      </div>
    </div>
  );
}
const AGENT_META: Record<string, { short: string; detail: string }> = {
  "Camera Agent": { short: "Camera", detail: "selected the relevant view" },
  "Tracking Agent": {
    short: "Tracking",
    detail: "counted local movement tracks",
  },
  "Identity Agent": { short: "Identity", detail: "checked duplicate handoffs" },
  "Movement Agent": { short: "Movement", detail: "analysed aisle flow" },
  "Queue Agent": { short: "Queue", detail: "measured checkout congestion" },
  "Business Agent": {
    short: "Business",
    detail: "translated measures into decisions",
  },
  "Evidence Agent": { short: "Evidence", detail: "verified supporting frames" },
};
function AgentFlow({
  phase,
  result,
}: {
  phase: number;
  result: AskResult | null;
}) {
  const agents = result?.agents || [
    "Camera Agent",
    "Tracking Agent",
    "Movement Agent",
    "Evidence Agent",
  ];
  return (
    <div className="agentFlow">
      <div className={`master ${phase > 0 ? "working" : ""}`}>
        <span className="orb">
          <i />
          <i />
          <i />
        </span>
        <div>
          <small>MASTER ORCHESTRATOR</small>
          <b>
            {phase === 0
              ? "Waiting for your question"
              : phase < agents.length + 2
                ? "Planning and delegating"
                : "Analysis complete"}
          </b>
        </div>
      </div>
      <div className="agentGrid">
        {agents.map((name, index) => {
          const active = phase === index + 2,
            done = phase > index + 2,
            meta = AGENT_META[name] || { short: name, detail: "working" };
          return (
            <article
              key={name}
              className={`${active ? "active" : ""} ${done ? "done" : ""}`}
            >
              <span>{done ? "✓" : String(index + 1).padStart(2, "0")}</span>
              <div>
                <b>{meta.short} agent</b>
                <small>
                  {active ? "working now…" : done ? meta.detail : "queued"}
                </small>
              </div>
              <i />
            </article>
          );
        })}
      </div>
      <svg
        className="flowLines"
        viewBox="0 0 800 80"
        preserveAspectRatio="none"
      >
        <path d="M400 0V25 M400 25H80V80 M400 25H290V80 M400 25H510V80 M400 25H720V80" />
      </svg>
    </div>
  );
}

function CameraEvidenceLayer({
  camera,
  observations,
}: {
  camera: Camera;
  observations: Observation[];
}) {
  const tracks = new Set(observations.map((row) => row.local_track_id)).size;
  const zones = Array.from(
    new Set(observations.map((row) => row.zone).filter(Boolean)),
  ) as string[];
  const buckets = [0, 1, 2, 3, 4, 5].map((bucket) => {
    const duration = observations.at(-1)?.ts_source || 1;
    const start = (duration / 6) * bucket;
    const end = (duration / 6) * (bucket + 1);
    return new Set(
      observations
        .filter((row) => row.ts_source >= start && row.ts_source < end)
        .map((row) => row.local_track_id),
    ).size;
  });
  const maximum = Math.max(...buckets, 1);
  const isShelfCamera = camera.id === "CAM-02";
  const handoffRisk = camera.id === "CAM-01" || camera.id === "CAM-04"
    ? "medium"
    : "review";
  return (
    <section className="cameraEvidenceLayer" aria-label="Selected camera evidence">
      <header>
        <div>
          <small>CAMERA EVIDENCE LAYER</small>
          <b>{camera.name} · observation queue</b>
        </div>
        <span>{observations.length} observations</span>
      </header>
      <div className="evidencePulse" aria-label="Observation activity sequence">
        {buckets.map((value, index) => (
          <i
            key={index}
            className={value ? "active" : ""}
            style={{ opacity: 0.2 + (0.8 * value) / maximum }}
            title={`Window ${index + 1}: ${value} local tracks`}
          />
        ))}
      </div>
      <div className="cameraEvidenceGrid">
        <article>
          <small>VISIBLE STATE</small>
          <strong>{tracks}</strong>
          <p>anonymous local tracks across {zones.length || 1} visible zone{zones.length === 1 ? "" : "s"}</p>
        </article>
        <article className={isShelfCamera ? "supported" : "blocked"}>
          <small>SHELF STATE</small>
          <strong>{isShelfCamera ? "linked" : "not observed"}</strong>
          <p>{isShelfCamera ? "The reviewed grocery interaction clips are mapped to this aisle reel." : "This camera cannot claim product picks or shelf gaps."}</p>
        </article>
        <article className={`risk ${handoffRisk}`}>
          <small>JOURNEY-LINK RISK</small>
          <strong>{handoffRisk}</strong>
          <p>Cross-camera identity remains a scored hypothesis until time, direction and appearance agree.</p>
        </article>
      </div>
      <aside>
        <b>TRUTH STATUS</b>
        <span>Observed:</span> detections, local tracks and zones.
        <span>Blocked:</span> purchase, exact SKU and confirmed cross-camera identity without matching evidence.
      </aside>
    </section>
  );
}

const STORE_SECTORS: Record<string, { role: string; question: string }> = {
  "CAM-01": { role: "Entry & produce", question: "Who entered, and where did traffic begin?" },
  "CAM-02": { role: "Grocery aisles", question: "What was viewed, picked, returned or left unavailable?" },
  "CAM-03": { role: "Promotions & assistance", question: "Where did congestion, assistance and dwell build up?" },
  "CAM-04": { role: "Checkout & exit", question: "Did visible journeys reach checkout, queue or leave?" },
};

function StoreOverview({
  state,
  observations,
  selected,
  onSelect,
}: {
  state: State;
  observations: Observation[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  const counts = state.cameras.map((camera) => ({
    ...camera,
    tracks: new Set(
      observations
        .filter((row) => row.camera_id === camera.id)
        .map((row) => row.local_track_id),
    ).size,
  }));
  const totalTracks = counts.reduce((sum, item) => sum + item.tracks, 0);
  return (
    <section className="storeOverview" id="store-overview">
      <header>
        <div>
          <small>01 · STORE-WIDE OPERATING PICTURE</small>
          <h2>One supermarket, four evidence zones</h2>
          <p>Select a sector to move from the whole-store picture into its camera evidence.</p>
        </div>
        <div className="storeStatus"><i /> COMPOSED VALIDATION STORE</div>
      </header>
      <div className="storeKpis">
        <span><b>{state.cameras.length}</b> connected camera roles</span>
        <span><b>{totalTracks}</b> camera-local tracks</span>
        <span><b>{state.media?.assigned_files || state.summary.source_clips || 0}</b> source clips with provenance</span>
        <span><b>0</b> forced identity matches</span>
      </div>
      <div className="storeRoute">
        {counts.map((camera, index) => {
          const meta = STORE_SECTORS[camera.id] || { role: camera.name, question: "Inspect this sector" };
          return <React.Fragment key={camera.id}>
            <button aria-label={`Open ${meta.role}`} className={selected === camera.id ? "selected" : ""} onClick={() => onSelect(camera.id)}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><small>{camera.id}</small><b>{meta.role}</b><p>{meta.question}</p></div>
              <em>{camera.tracks} tracks</em>
            </button>
            {index < counts.length - 1 && <div className="handoffEdge"><i /><small>scored handoff</small></div>}
          </React.Fragment>;
        })}
      </div>
      <div className="storeTruth">
        <article><small>OBSERVED</small><b>Per-camera movement</b><p>Detections, local tracks, visible zones, dwell windows and occupancy.</p></article>
        <article><small>CORRELATED</small><b>Journey hypotheses</b><p>Time, adjacency, direction and appearance rank possible cross-camera links.</p></article>
        <article><small>NOT CLAIMED</small><b>Sales and identity</b><p>No purchase, lost-sale or same-person claim is made without supporting data.</p></article>
      </div>
    </section>
  );
}

function MediaProvenance({ catalog }: { catalog: MediaCatalog }) {
  return <section className="mediaProvenance">
    <header><div><small>VALIDATION MEDIA INTAKE</small><h2>Every clip accounted for</h2></div><span className={catalog.unassigned_files ? "needsReview" : "catalogReady"}>{catalog.unassigned_files ? `${catalog.unassigned_files} NEED REVIEW` : "CATALOG CURRENT"}</span></header>
    <div className="mediaStats">
      <article><strong>{catalog.discovered_files}</strong><span>files discovered</span></article>
      <article><strong>{catalog.assigned_files}</strong><span>mapped to store zones</span></article>
      <article><strong>{catalog.reels?.length || 0}</strong><span>camera replay reels</span></article>
      <article><strong>AUTO</strong><span>rescan on launch</span></article>
    </div>
    <div className="reelMap">{catalog.reels?.map(reel => <article key={reel.camera_id}><span>{reel.camera_id}</span><div><b>{reel.name}</b><small>{reel.clip_count} clips · {reel.duration_s.toFixed(1)} seconds</small></div><i style={{width: `${Math.max(8, Math.min(100, reel.clip_count * 12))}%`}} /></article>)}</div>
    <p><b>Evidence boundary:</b> {catalog.disclosure}</p>
  </section>;
}
function Answer({
  result,
  onExplore,
}: {
  result: AskResult;
  onExplore: () => void;
}) {
  return (
    <section className="answer">
      <header>
        <span>BUSINESS ANALYSIS · VERIFIED</span>
        <b>
          {result.facts.risk === "attention"
            ? "REVIEW SIGNAL"
            : "NORMAL SIGNAL"}
        </b>
      </header>
      <p>{result.answer}</p>
      <div className="metrics businessMetrics">
        <div>
          <strong>{result.facts.local_tracks ?? "—"}</strong>
          <span>local tracks</span>
        </div>
        <div>
          <strong>{result.facts.peak_occupancy ?? "—"}</strong>
          <span>peak occupancy</span>
        </div>
        <div>
          <strong>{result.facts.median_track_s ?? "—"}s</strong>
          <span>median observed span</span>
        </div>
        <div>
          <strong>
            {result.facts.rightward ?? "—"} / {result.facts.leftward ?? "—"}
          </strong>
          <span>right / left flow</span>
        </div>
      </div>
      <div className="insights">
        {result.insights.map((item, index) => (
          <p key={item}>
            <b>0{index + 1}</b>
            {item}
          </p>
        ))}
      </div>
      <div className="recommendation">
        <small>BUSINESS RECOMMENDATION</small>
        <b>{result.recommendation}</b>
      </div>
      <button className="explore" onClick={onExplore}>
        Open detailed analytics studio <span>↓</span>
      </button>
      <aside>{result.boundary}</aside>
    </section>
  );
}

const PHASES = [
  "Observe",
  "Remember",
  "Investigate",
  "Explain",
  "Simulate",
  "Verify",
];
function InvestigationTheatre() {
  const [data, setData] = useState<any>(null),
    [phase, setPhase] = useState(0),
    [staged, setStaged] = useState(true),
    [approval, setApproval] = useState<any>(null);
  useEffect(() => {
    setData(null);
    setApproval(null);
    api(`/api/showcase?staged_scenario=${staged}`).then(setData);
  }, [staged]);
  const approve = () =>
    api("/api/showcase/approve", { method: "POST" }).then(setApproval);
  if (!data)
    return (
      <section className="theatre">
        <div className="loader" />
        Reconstructing investigation…
      </section>
    );
  return (
    <section className="theatre" id="investigation-theatre">
      <header>
        <div>
          <small>04 · GUIDED CLOSED-LOOP INVESTIGATION</small>
          <h2>{data.title}</h2>
          <p>{data.question}</p>
        </div>
        <button
          className={staged ? "scenario on" : "scenario"}
          onClick={() => setStaged(!staged)}
        >
          <i />
          {staged ? "Staged disruption included" : "Measured footage only"}
        </button>
      </header>
      <nav>
        {PHASES.map((name, index) => (
          <button
            key={name}
            className={`${phase === index ? "active" : ""} ${phase > index ? "done" : ""}`}
            onClick={() => setPhase(index)}
          >
            <span>{phase > index ? "✓" : index + 1}</span>
            <b>{name}</b>
          </button>
        ))}
      </nav>
      <div className="truthBand">
        <span>
          <i className="observedDot" /> OBSERVED
        </span>
        <p>{data.truth_boundary.observed}</p>
        <span>
          <i className="stagedDot" /> STAGED INPUT
        </span>
        <p>{data.truth_boundary.staged}</p>
      </div>
      <div className="theatreBody">
        {phase === 0 && (
          <div className="observePhase">
            <div>
              <small>MEASURED FROM CAM-04</small>
              <strong>{data.observed.peak_occupancy}</strong>
              <span>peak simultaneous tracks</span>
            </div>
            <div>
              <small>LOCAL TRACKS</small>
              <strong>{data.observed.local_tracks}</strong>
              <span>anonymous, non-biometric</span>
            </div>
            <div>
              <small>MEAN OCCUPANCY</small>
              <strong>{data.observed.mean_occupancy}</strong>
              <span>sampled frames</span>
            </div>
            <div>
              <small>PRESSURE FRAMES</small>
              <strong>{data.observed.threshold_frames}</strong>
              <span>at review threshold</span>
            </div>
          </div>
        )}
        {phase === 1 && (
          <div className="memoryPhase">
            {data.spatial_memory.map((item: any, index: number) => (
              <article key={`${item.time}-${item.zone}`}>
                <span>{item.time}</span>
                <i />
                <div>
                  <b>{item.zone}</b>
                  <p>{item.event}</p>
                  <small
                    className={
                      item.source === "OBSERVED"
                        ? "observedSource"
                        : "stagedSource"
                    }
                  >
                    {item.source}
                  </small>
                </div>
                {index < data.spatial_memory.length - 1 && <em />}
              </article>
            ))}
          </div>
        )}
        {phase === 2 && (
          <div className="investigatePhase">
            <div className="orchestratorCore">
              <i />
              <b>Master Orchestrator</b>
              <span>delegated {data.agents.length - 1} specialist tasks</span>
            </div>
            <div className="investigationAgents">
              {data.agents.slice(1).map((agent: any, index: number) => (
                <article
                  key={agent.id}
                  style={
                    {
                      "--agent-delay": `${index * 0.08}s`,
                    } as React.CSSProperties
                  }
                >
                  <span>{agent.name}</span>
                  <b>{agent.task}</b>
                  <p>{agent.result}</p>
                  <em className={agent.state}>{agent.state}</em>
                </article>
              ))}
            </div>
          </div>
        )}
        {phase === 3 && (
          <div className="explainPhase">
            <div className="hypothesisGrid">
              {data.hypotheses.map((hypothesis: any) => (
                <article
                  key={hypothesis.id}
                  className={hypothesis.state === "leading" ? "leading" : ""}
                >
                  <header>
                    <span>{hypothesis.id}</span>
                    <b>{hypothesis.label}</b>
                    <strong>{Math.round(hypothesis.score * 100)}</strong>
                  </header>
                  <div className="scoreTrack">
                    <i style={{ width: `${hypothesis.score * 100}%` }} />
                  </div>
                  <p className="supports">+ {hypothesis.support[0]}</p>
                  <p className="contradicts">− {hypothesis.contradict[0]}</p>
                  <small>
                    {hypothesis.source} · {hypothesis.state}
                  </small>
                </article>
              ))}
            </div>
            <aside>
              <small>VERIFIER CONCLUSION</small>
              <b>{data.finding.label}</b>
              <p>{data.finding.explanation}</p>
              <span>{data.finding.confidence_state}</span>
            </aside>
          </div>
        )}
        {phase === 4 && (
          <div className="simulatePhase">
            <div className="scenarioCompare">
              <section>
                <small>CURRENT CAPACITY</small>
                <strong>{data.simulation.baseline.load_index}</strong>
                <span>load index</span>
                <em className={data.simulation.baseline.signal}>
                  {data.simulation.baseline.signal}
                </em>
              </section>
              <div>
                <span>+1 staffed checkout</span>
                <i>→</i>
                <b>{data.simulation.estimated_load_reduction_pct}%</b>
                <small>estimated load reduction</small>
              </div>
              <section>
                <small>PROJECTED CAPACITY</small>
                <strong>{data.simulation.projected.load_index}</strong>
                <span>load index</span>
                <em className={data.simulation.projected.signal}>
                  {data.simulation.projected.signal}
                </em>
              </section>
            </div>
            <p>{data.simulation.boundary}</p>
          </div>
        )}
        {phase === 5 && (
          <div className="verifyPhase">
            <div className="intervention">
              <small>HUMAN-CONTROLLED INTERVENTION</small>
              <h3>{data.intervention.action}</h3>
              <div>
                {data.intervention.success_criteria.map((criterion: string) => (
                  <span key={criterion}>○ {criterion}</span>
                ))}
              </div>
              <button onClick={approve} disabled={!!approval}>
                {approval ? "Pilot approved" : "Approve staged pilot"}
              </button>
              <p>No external action is triggered by this demonstration.</p>
            </div>
            <div className={`verification ${approval ? "revealed" : ""}`}>
              <small>
                {approval
                  ? "STAGED VERIFICATION RESULT"
                  : "AWAITING HUMAN APPROVAL"}
              </small>
              {approval ? (
                <>
                  <div className="beforeAfter">
                    <section>
                      <span>Before</span>
                      <strong>{approval.verification.before.load_index}</strong>
                      <small>
                        load index · peak {approval.verification.before.peak}
                      </small>
                    </section>
                    <i>→</i>
                    <section>
                      <span>After</span>
                      <strong>{approval.verification.after.load_index}</strong>
                      <small>
                        load index · peak {approval.verification.after.peak}
                      </small>
                    </section>
                  </div>
                  <b>
                    {approval.verification.criteria_met}/
                    {approval.verification.criteria_total} success criteria met
                  </b>
                  <p>{approval.verification.conclusion}</p>
                </>
              ) : (
                <p>
                  APN will not simulate an approved outcome until a human
                  accepts the staged pilot.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
      <footer>
        <button disabled={phase === 0} onClick={() => setPhase(phase - 1)}>
          ← Previous
        </button>
        <span>
          Step {phase + 1} of {PHASES.length}
        </span>
        <button
          disabled={phase === PHASES.length - 1}
          onClick={() => setPhase(phase + 1)}
        >
          Next: {PHASES[Math.min(PHASES.length - 1, phase + 1)]} →
        </button>
      </footer>
    </section>
  );
}

function BusinessIntelligence() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/api/business/profile/supermarket").then(setData);
  }, []);
  return (
    <section className="businessBrief" id="business-intelligence">
      <header>
        <div>
          <small>05 · ANALYTICS OUTPUT CONTRACT</small>
          <h2>Which signals are measured, inferred, or still blocked?</h2>
          <p>Technical validation of the measures supplied to the manager workspace.</p>
        </div>
        <span className="verticalBadge">SUPERMARKET · SIGNAL CONTRACT</span>
      </header>
      {!data ? <div className="businessLoading"><div className="loader" /> Translating evidence…</div> : <>
        <div className="businessLead">
          <div><small>CURRENT DECISION FOCUS</small><h3>{data.primary}</h3><p>{data.action}</p></div>
          <div><small>BUSINESS QUESTIONS</small>{data.questions.map((x: string) => <span key={x}>→ {x}</span>)}</div>
        </div>
        <div className="zoneComparison">
          {data.comparison.map((item: any) => {
            const maxTracks = Math.max(...data.comparison.map((x: any) => x.local_tracks), 1);
            return <article key={item.camera_id}>
              <div><small>{item.camera_id}</small><b>{item.label}</b></div>
              <strong>{item.local_tracks}<small> local tracks</small></strong>
              <div className="comparisonBar"><i style={{width: `${item.local_tracks / maxTracks * 100}%`}} /></div>
              <p>Peak {item.peak_occupancy} · median visible {item.median_visible_s}s</p>
            </article>;
          })}
        </div>
        <div className="capabilityRoadmap">
          <article><small>MEASURABLE FROM CURRENT FOOTAGE</small>{data.available_now.map((x: string) => <span key={x}>✓ {x}</span>)}</article>
          <article><small>NEXT DATA + MODEL PATH FOR {data.label.toUpperCase()}</small>{data.future.map((x: string) => <span key={x}>+ {x}</span>)}</article>
        </div>
        <aside>{data.truth_boundary}</aside>
      </>}
    </section>
  );
}

function DeepAnalysis({ cameraId }: { cameraId: string }) {
  const [data, setData] = useState<any>(null),
    [counters, setCounters] = useState(1),
    [simulation, setSimulation] = useState<any>(null),
    [notice, setNotice] = useState("");
  useEffect(() => {
    Promise.all([
      api(`/api/business/spatial/${cameraId}`),
      api(`/api/business/comparison/${cameraId}`),
      api("/api/business/queue"),
      api("/api/business/funnel"),
      api("/api/business/recommendations"),
      api("/api/evaluation/robustness"),
    ]).then(
      ([spatial, comparison, queue, funnel, recommendations, evaluation]) =>
        setData({
          spatial,
          comparison,
          queue,
          funnel,
          recommendations,
          evaluation,
        }),
    );
  }, [cameraId]);
  const simulate = () =>
    api("/api/business/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "checkout", added_counters: counters }),
    }).then(setSimulation);
  const report = () => {
    setNotice("Generating operational report…");
    api("/api/reports/generate", { method: "POST" })
      .then((r) => {
        const blob = new Blob([JSON.stringify(r, null, 2)], {
          type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${r.report_id}.json`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        setNotice(`Report ${r.report_id} downloaded · archived at ${r.saved_to}`);
      })
      .catch((error) => setNotice(`Report failed: ${error.message}`));
  };
  const decide = (id: string, decision: string) =>
    api(`/api/business/recommendations/${id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, note: "Decision Studio review" }),
    }).then(() =>
      setNotice(`${id} marked ${decision}; no external action was taken.`),
    );
  if (!data)
    return (
      <section className="studio loadingStudio">
        <div className="loader" />
        Building Decision Studio from evidence…
      </section>
    );
  const { spatial, comparison, queue, funnel, recommendations, evaluation } =
    data;
  return (
    <section className="studio" id="decision-studio">
      <header>
        <div>
            <small>06 · DECISION STUDIO</small>
          <h2>From movement to operational decisions</h2>
          <p>
            Measured evidence, scenarios and human-controlled actions in one
            place.
          </p>
        </div>
        <button onClick={report}>Generate operational report</button>
      </header>
      <div className="studioGrid">
        <article className="heatmapCard">
          <div className="cardTitle">
            <b>Traffic heatmap & paths</b>
            <span>{cameraId}</span>
          </div>
          <div className="heatmap">
            {spatial.grid.flatMap((row: any[]) =>
              row.map((value: number, index: number) => (
                <i
                  key={`${index}-${value}`}
                  style={{
                    opacity:
                      0.12 + (0.88 * value) / Math.max(1, spatial.maximum),
                  }}
                />
              )),
            )}
            <svg viewBox="0 0 1 1" preserveAspectRatio="none">
              {spatial.paths.slice(0, 12).map((path: any, index: number) => (
                <polyline
                  key={path.track_id}
                  points={path.points
                    .map((p: any) => `${p.x},${p.y}`)
                    .join(" ")}
                  className={`path p${index % 4}`}
                />
              ))}
            </svg>
          </div>
          <p>{spatial.boundary}</p>
        </article>
        <article>
          <div className="cardTitle">
            <b>Time-window comparison</b>
            <span>within clip</span>
          </div>
          <div className="compare">
            <section>
              <small>FIRST HALF</small>
              <strong>{comparison.first.local_tracks}</strong>
              <span>tracks · peak {comparison.first.peak_occupancy}</span>
            </section>
            <em>→</em>
            <section>
              <small>SECOND HALF</small>
              <strong>{comparison.second.local_tracks}</strong>
              <span>tracks · peak {comparison.second.peak_occupancy}</span>
            </section>
          </div>
          <p>
            Track change {comparison.track_change >= 0 ? "+" : ""}
            {comparison.track_change}; peak change{" "}
            {comparison.peak_change >= 0 ? "+" : ""}
            {comparison.peak_change}. {comparison.boundary}
          </p>
        </article>
        <article>
          <div className="cardTitle">
            <b>Queue intelligence</b>
            <span className={queue.signal}>{queue.signal}</span>
          </div>
          <div className="queueNumbers">
            <strong>
              {queue.peak_occupancy}
              <small>peak</small>
            </strong>
            <strong>
              {queue.mean_occupancy}
              <small>mean</small>
            </strong>
            <strong>
              {queue.longest_observed_span_s}s<small>longest visible</small>
            </strong>
          </div>
          <p>
            {queue.frames_at_or_above_threshold} sampled frames met the review
            threshold of {queue.threshold}. {queue.boundary}
          </p>
        </article>
        <article className="funnelCard">
          <div className="cardTitle">
            <b>Operational passage funnel</b>
            <span>uncertainty-aware</span>
          </div>
          <div className="funnel">
            {funnel.stages.map((stage: any, index: number) => (
              <section
                key={stage.camera_id}
                style={{ width: `${Math.max(38, 100 - index * 12)}%` }}
              >
                <span>{stage.name}</span>
                <strong>{stage.local_tracks}</strong>
                <small>local tracks</small>
              </section>
            ))}
          </div>
          <p>
            Possible global identities: {funnel.global_identity_lower_bound}–
            {funnel.global_identity_upper_bound}. {funnel.boundary}
          </p>
        </article>
        <article className="simulationCard">
          <div className="cardTitle">
            <b>What-if simulation</b>
            <span>checkout capacity</span>
          </div>
          <label>
            Add <strong>{counters}</strong> checkout counter(s)
            <input
              type="range"
              min="1"
              max="4"
              value={counters}
              onChange={(e) => setCounters(Number(e.target.value))}
            />
          </label>
          <button onClick={simulate}>Run scenario</button>
          {simulation && (
            <div className="simResult">
              <span>Load index</span>
              <b>
                {simulation.baseline.load_index} →{" "}
                {simulation.projected.load_index}
              </b>
              <strong>
                {simulation.estimated_load_reduction_pct}% estimated reduction
              </strong>
              <small>{simulation.boundary}</small>
            </div>
          )}
        </article>
        <article className="recommendationsCard">
          <div className="cardTitle">
            <b>Human-controlled recommendations</b>
            <span>{recommendations.length} review item(s)</span>
          </div>
          {recommendations.map((item: any) => (
            <section key={item.id}>
              <div>
                <small>
                  {item.id} · {item.priority}
                </small>
                <b>{item.title}</b>
                <p>{item.reason}</p>
              </div>
              <button onClick={() => decide(item.id, "approve_for_pilot")}>
                Approve pilot
              </button>
              <button onClick={() => decide(item.id, "dismiss")}>
                Dismiss
              </button>
            </section>
          ))}
        </article>
        <article className="evaluationCard">
          <div className="cardTitle">
            <b>Robustness evaluation</b>
            <span>centralised vs agentic</span>
          </div>
          {evaluation.scenarios.map((item: any) => (
            <section key={item.scenario}>
              <b>{item.scenario.replaceAll("_", " ")}</b>
              <span>
                Central continuity {item.centralized.continuity_score}
              </span>
              <span>Agentic continuity {item.agentic.continuity_score}</span>
              <em>
                {item.agentic.abstains ? "abstains safely" : "operational"}
              </em>
            </section>
          ))}
          <p>{evaluation.boundary}</p>
        </article>
      </div>
      {notice && <div className="studioNotice">{notice}</div>}
    </section>
  );
}

function SystemLaboratory() {
  const [trajectory, setTrajectory] = useState<any>(null),
    [evidence, setEvidence] = useState<any>(null),
    [plan, setPlan] = useState<any>(null),
    [question, setQuestion] = useState(
      "Why did checkout pressure increase and what should we do?",
    ),
    [incident, setIncident] = useState("none"),
    [incidentResult, setIncidentResult] = useState<any>(null),
    [counters, setCounters] = useState(1),
    [twin, setTwin] = useState<any>(null),
    [benchmark, setBenchmark] = useState<any>(null);
  useEffect(() => {
    Promise.all([
      api("/api/lab/trajectories"),
      api("/api/lab/evidence"),
      api("/api/lab/benchmark"),
      api("/api/lab/network?incident=none"),
    ]).then(([t, e, b, network]) => {
      setTrajectory(t);
      setEvidence(e);
      setBenchmark(b);
      setIncidentResult({
        incident: "none",
        network,
        agent_response: "All camera agents are healthy. Choose an incident to test how APN degrades and recovers.",
        abstains: false,
      });
    });
    compile();
    runTwin(1);
  }, []);
  const compile = () =>
    api("/api/lab/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }).then(setPlan);
  const inject = (name: string) => {
    setIncident(name);
    api("/api/lab/incidents", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-APN-Role": "Administrator",
      },
      body: JSON.stringify({ incident: name }),
    }).then(setIncidentResult);
  };
  const runTwin = (value: number) => {
    setCounters(value);
    api("/api/lab/digital-twin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ counters: value }),
    }).then(setTwin);
  };
  if (!trajectory || !evidence || !benchmark)
    return (
      <section className="systemLab">
        <div className="loader" />
        Starting System Laboratory…
      </section>
    );
  const maxQueue = Math.max(
    ...(twin?.series || [{ queue: 1 }]).map((x: any) => x.queue),
    1,
  );
  return (
    <section className="systemLab" id="system-lab">
      <header>
        <div>
          <small>07 · SECURITY, RESILIENCE & SYSTEM LABORATORY</small>
          <h2>Experiment with the intelligence network</h2>
          <p>These are executable system behaviours—not dashboard summaries.</p>
        </div>
        <span>7 interactive systems</span>
      </header>
      <div className="labGrid">
        <article className="trajectoryLab">
          <div className="labTitle">
            <b>01 · Cross-camera trajectory graph</b>
            <span>{trajectory.tracks.length} local trajectories</span>
          </div>
          <svg viewBox="0 0 1000 250">
            {trajectory.cameras.map((camera: any, index: number) => (
              <g key={camera.id}>
                <rect
                  x={40 + index * 240}
                  y="25"
                  width="200"
                  height="195"
                  rx="6"
                />
                <text x={140 + index * 240} y="50" textAnchor="middle">
                  {camera.id}
                </text>
              </g>
            ))}
            {trajectory.tracks.slice(0, 30).map((track: any, index: number) => {
              const cam = Number(track.camera_id.slice(-2)) - 1;
              const first = track.points[0],
                last = track.points.at(-1);
              return (
                <path
                  key={track.id}
                  d={`M${55 + cam * 240 + first.x * 170} ${70 + first.y * 125} Q${140 + cam * 240} ${110 + (index % 6) * 14} ${55 + cam * 240 + last.x * 170} ${70 + last.y * 125}`}
                  className={`trajectoryPath p${index % 4}`}
                />
              );
            })}
            {trajectory.handoffs.map((handoff: any, index: number) => (
              <path
                key={handoff.handoff_id}
                d={`M${225 + index * 240} 150 L${275 + index * 240} 150`}
                className={`handoffPath ${handoff.state}`}
              />
            ))}
          </svg>
          <p>{trajectory.boundary}</p>
        </article>
        <article className="plannerLab">
          <div className="labTitle">
            <b>02 · Live query compiler</b>
            <span>question → execution DAG</span>
          </div>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button onClick={compile}>Compile agent plan</button>
          {plan && (
            <div className="planGraph">
              {plan.nodes.map((node: any) => (
                <section key={node.id} className={node.kind}>
                  <b>{node.label}</b>
                  <small>{node.task}</small>
                </section>
              ))}
            </div>
          )}
        </article>
        <article className="evidenceLab">
          <div className="labTitle">
            <b>03 · Auto-selected evidence wall</b>
            <span>privacy masked</span>
          </div>
          <div>
            {evidence.evidence.slice(0, 8).map((item: any) => (
              <figure key={`${item.camera_id}-${item.track_id}`}>
                <img
                  src={`/api/evidence-thumb/${item.crop_ref}?token=${TOKEN}`}
                  alt={`Privacy-masked evidence from ${item.camera_id}, track ${item.track_id}`}
                />
                <figcaption>
                  <b>
                    {item.camera_id} · {item.track_id}
                  </b>
                  <span>
                    T+{item.ts.toFixed(1)}s · frame {item.frame_idx}
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
          <p>
            {evidence.causal_graph.length} causal ledger nodes link observations
            to findings.
          </p>
        </article>
        <article className="incidentLab">
          <div className="labTitle">
            <b>04 · Incident injection laboratory</b>
            <span>
              {incidentResult?.network.global_confidence || "normal"} confidence
            </span>
          </div>
          <div className="incidentButtons">
            {[
              ["none", "Nominal"],
              ["camera_loss", "Kill CAM-03"],
              ["message_delay", "Add 5s delay"],
              ["identity_ambiguity", "Force ambiguity"],
              ["queue_surge", "Queue surge"],
              ["forged_message", "Forge message"],
            ].map(([id, label]) => (
              <button
                key={id}
                className={incident === id ? "active" : ""}
                onClick={() => inject(id)}
              >
                {label}
              </button>
            ))}
          </div>
          {incidentResult && (
            <>
              <div className="edgeNodes">
                {incidentResult.network.nodes.map((node: any) => (
                  <section key={node.id} className={node.state}>
                    <i />
                    <b>{node.id}</b>
                    <span>{node.state}</span>
                    <small>
                      {node.processing_fps} FPS · {node.latency_ms}ms
                    </small>
                  </section>
                ))}
              </div>
              <aside>
                <b>APN RESPONSE</b>
                {incidentResult.agent_response}
                <span>
                  {incidentResult.abstains
                    ? "SAFE ABSTENTION ACTIVE"
                    : "NETWORK OPERATIONAL"}
                </span>
              </aside>
            </>
          )}
        </article>
        <article className="twinLab">
          <div className="labTitle">
            <b>05 · Animated operational twin</b>
            <span>{twin?.stable ? "stable" : "queue growing"}</span>
          </div>
          <label>
            Active checkout counters: <strong>{counters}</strong>
            <input
              type="range"
              min="1"
              max="4"
              value={counters}
              onChange={(e) => runTwin(Number(e.target.value))}
            />
          </label>
          {twin && (
            <svg viewBox="0 0 600 190">
              <line x1="35" y1="160" x2="570" y2="160" />
              <line x1="35" y1="20" x2="35" y2="160" />
              <polyline
                points={twin.series
                  .map(
                    (x: any) =>
                      `${35 + (x.minute / 12) * 535},${160 - (x.queue / maxQueue) * 130}`,
                  )
                  .join(" ")}
              />
              <text x="40" y="18">
                queue: {twin.final_queue} final · {twin.peak_queue} peak
              </text>
            </svg>
          )}
          <p>{twin?.boundary}</p>
        </article>
        <article className="benchmarkLab">
          <div className="labTitle">
            <b>06 · Architecture benchmark</b>
            <span>centralised vs APN</span>
          </div>
          {benchmark.experiments.map((item: any) => (
            <section key={item.incident}>
              <b>{item.incident.replaceAll("_", " ")}</b>
              <label>
                Centralised
                <i
                  style={{ width: `${item.centralized.task_coverage * 100}%` }}
                />
              </label>
              <label>
                Agentic APN
                <i style={{ width: `${item.agentic.task_coverage * 100}%` }} />
              </label>
              <em>{item.agentic.safe_abstention ? "safe abstention" : ""}</em>
            </section>
          ))}
          <p>{benchmark.boundary}</p>
        </article>
      </div>
    </section>
  );
}

type OwnerSection = "overview" | "performance" | "journeys" | "planning";

const hourlyTraffic = [28, 36, 52, 67, 61, 78, 92, 84, 69, 48];
const typicalTraffic = [31, 34, 45, 55, 58, 66, 75, 73, 60, 45];
const dayLabels = ["10a", "11a", "12p", "1p", "2p", "3p", "4p", "5p", "6p", "7p"];

function MiniLineChart() {
  const points = (values: number[]) => values.map((value, index) => `${index * 11.11},${100 - value}`).join(" ");
  return <div className="ownerLineChart" aria-label="Hourly footfall compared with typical traffic">
    <div className="chartLegend"><span><i className="todayDot" /> Today</span><span><i /> Typical Wednesday</span></div>
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img">
      {[20, 40, 60, 80].map(y => <line key={y} x1="0" x2="100" y1={y} y2={y} />)}
      <polyline className="typicalLine" points={points(typicalTraffic)} />
      <polyline className="todayLine" points={points(hourlyTraffic)} />
    </svg>
    <div className="chartAxis">{dayLabels.map(x => <span key={x}>{x}</span>)}</div>
  </div>;
}

function OwnerDashboard({ onTechnical, onExit }: { onTechnical: () => void; onExit: () => void }) {
  const [section, setSection] = useState<OwnerSection>("overview");
  const [profile, setProfile] = useState<any>(null);
  const [state, setState] = useState<State | null>(null);
  const [counters, setCounters] = useState(2);
  const [report, setReport] = useState<any>(null);
  const [reportStatus, setReportStatus] = useState("");
  const [evidence, setEvidence] = useState<any>(null);
  const [experiment, setExperiment] = useState<"closed" | "design" | "result">("closed");
  const [scenario, setScenario] = useState<"weekend" | "midweek" | "friday">("weekend");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [weekendPlanOpen, setWeekendPlanOpen] = useState(false);
  const [selectedFunnel, setSelectedFunnel] = useState("Stopped");
  const [dismissedAlerts, setDismissedAlerts] = useState<string[]>([]);
  const [actionedAlerts, setActionedAlerts] = useState<string[]>([]);
  useEffect(() => {
    Promise.all([api("/api/business/profile/supermarket"), api("/api/state")])
      .then(([p, s]) => { setProfile(p); setState(s); });
  }, []);
  const maxTraffic = Math.max(...(profile?.comparison || []).map((x: any) => x.local_tracks), 1);
  const prepareReport = (openPlanning = false) => {
    setReportStatus("Preparing report from the current evidence ledger…");
    if (openPlanning) setSection("planning");
    api("/api/reports/generate", { method: "POST" })
      .then((value) => { setReport(value); setReportStatus(""); })
      .catch((error) => setReportStatus(`Report failed: ${error.message}`));
  };
  const downloadReport = () => {
    if (!report) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const link = document.createElement("a"); link.href = url; link.download = `${report.report_id}.json`; link.click(); URL.revokeObjectURL(url);
  };
  const evidenceItems = [
    { n: 3, t: "Long hesitation", d: "Grocery aisle · no visible assistance", camera: "CAM-02", window: "3.mp4 · reel T+20–30s", observed: "Extended visible dwell in the reviewed grocery shelf clip.", inference: "Assistance opportunity; intent and satisfaction are not claimed." },
    { n: 2, t: "Comparison pattern", d: "Grocery shelf · repeated product consideration", camera: "CAM-02", window: "4.mp4 · reel T+30–40s", observed: "Repeated shelf-facing movement marked for interaction-model review.", inference: "Possible comparison event; exact SKU requires product labels." },
    { n: 1, t: "Shelf access blocked", d: "Trolley congestion in grocery aisle", camera: "CAM-02", window: "5.mp4 · reel T+40–50s", observed: "Overlapping tracks and trolley placement reduced visible shelf access.", inference: "Congestion cue; commercial impact requires repeated windows." },
  ];
  const scenarioModels = {
    weekend: { label: "Weekend rush", crowd: "High", mission: "Quick completion", winner: "A", title: "Keep complementary items together", explanation: "High crowd pressure makes a longer discovery route frustrating and increases congestion. Reduce search time by placing bread and spreads together.", a: [86, 91, 78, 88], b: [54, 48, 63, 59], action: "Create a compact breakfast zone and open one additional checkout counter." },
    midweek: { label: "Midweek restock", crowd: "Low–medium", mission: "Full-basket restock", winner: "B", title: "Use a measured discovery route", explanation: "Restock shoppers already traverse multiple aisles and the store has spare movement capacity. Separation can increase category discovery without creating peak-hour friction.", a: [68, 72, 71, 69], b: [82, 65, 88, 79], action: "Separate the categories across a short, measurable route and monitor abandonment." },
    friday: { label: "Friday occasion shop", crowd: "Medium–high", mission: "Occasion-led basket", winner: "C", title: "Use an occasion bundle, not either default", explanation: "Friday missions are category-specific. A visible occasion station can combine snacks, nuts and eligible beverages while keeping normal staples easy to find.", a: [71, 76, 69, 72], b: [62, 55, 78, 64], action: "Pilot a clearly priced weekend-hosting bundle and compare attachment rate with the normal layout." },
  } as const;
  const activeScenario = scenarioModels[scenario];
  const alerts = [
    { id: "assist", level: "now", title: "Customer assistance recommended", detail: "Extended hesitation detected in Grocery Aisle 2.", source: "CAM-02 · 3 dwell signals", action: "Dispatch floor staff" },
    { id: "safety", level: "review", title: "Possible aisle obstruction", detail: "Shelf access reduced during a congested window. Inspect for a spill, fallen item or blocked path.", source: "CAM-02 · access signal", action: "Send safety check" },
    { id: "surge", level: "tomorrow", title: "Tomorrow’s surge may exceed baseline", detail: "Weekend profile indicates higher traffic. Compact complementary products and prepare checkout capacity.", source: "Projected operating baseline", action: "Prepare weekend plan" },
  ];
  const activeAlerts = alerts.filter(x => !dismissedAlerts.includes(x.id));
  const funnelStages = [
    { label: "Passed shelf", value: 100, meaning: "Visible in the shelf zone", evidence: "Anonymous path crossed the configured product zone." },
    { label: "Looked", value: 72, meaning: "Head and body orientation cue", evidence: "Requires the interaction model; shown as a validation scenario." },
    { label: "Stopped", value: 51, meaning: "Movement slowed near the shelf", evidence: "Supported by visible dwell and track displacement." },
    { label: "Touched", value: 34, meaning: "Hand approached the shelf", evidence: "Requires hand–product interaction detection." },
    { label: "Picked up", value: 23, meaning: "Possible shelf-removal event", evidence: "Requires shelf-state change plus hand tracking." },
    { label: "Retained", value: 16, meaning: "Item remained with shopper", evidence: "Purchase is not claimed without checkout/POS linkage." },
  ];
  const activeFunnel = funnelStages.find(x => x.label === selectedFunnel)!;
  const nav: { id: OwnerSection; label: string; hint: string }[] = [
    { id: "overview", label: "Today", hint: "Brief, rush & actions" },
    { id: "performance", label: "Store performance", hint: "Aisles, products & affinity" },
    { id: "journeys", label: "Customer journeys", hint: "Flow & lost opportunities" },
    { id: "planning", label: "Planning", hint: "Staff, comparisons & reports" },
  ];
  return <main className="ownerApp ownerV3">
    <header className="ownerTopbar">
      <div className="ownerBrand"><span>M</span><div><b>Meridian Operations</b><small>Store intelligence by APN</small></div></div>
      <div className="ownerStore"><i /> Wednesday, 27 November <small>· Store 01</small></div>
      <div className="notificationControl"><button aria-label="Open operational notifications" className="notificationBell" onClick={() => setNotificationsOpen(!notificationsOpen)}>◉<span>{activeAlerts.length}</span></button>{notificationsOpen && <div className="notificationPanel"><header><div><small>OPERATIONAL NOTIFICATIONS</small><b>What needs attention</b></div><button onClick={() => setNotificationsOpen(false)}>×</button></header>{activeAlerts.length ? activeAlerts.map(alert => <article key={alert.id} className={alert.level}><i/><div><small>{alert.level === "now" ? "ACT NOW" : alert.level === "tomorrow" ? "PLAN AHEAD" : "REVIEW"}</small><b>{alert.title}</b><p>{alert.detail}</p><em>{alert.source}</em><div><button onClick={() => {setActionedAlerts([...actionedAlerts, alert.id]); if(alert.id === "surge"){setWeekendPlanOpen(true);setNotificationsOpen(false);}}}>{actionedAlerts.includes(alert.id) ? "Action assigned ✓" : alert.action}</button><button onClick={() => setDismissedAlerts([...dismissedAlerts, alert.id])}>Dismiss</button></div></div></article>) : <p className="allClear">All operational alerts reviewed.</p>}</div>}</div>
      <button className="technicalDoor" onClick={onTechnical}>Technical evidence ↗</button>
      <button className="quietButton" onClick={onExit}>Sign out</button>
    </header>
    <div className="ownerShell">
      <aside className="ownerSidebar">
        <div><small>STORE MANAGER</small><b>Good afternoon, Bhumi</b><p>Three decisions need your attention</p></div>
        <nav>{nav.map(item => <button key={item.id} className={section === item.id ? "active" : ""} onClick={() => setSection(item.id)}><span>{item.label}</span><small>{item.hint}</small></button>)}</nav>
        <div className="ownerTruth"><b>Today’s brief</b><span><i /> Current footage reviewed</span><span><i className="demo" /> Forecast clearly labelled</span><p>Commercial results remain pending until POS is connected.</p></div>
      </aside>
      <section className="ownerContent">
        {activeAlerts.some(x => x.level === "now") && <div className="liveAlert"><span><i/> LIVE RECOMMENDATION</span><div><b>Customer may need assistance in Grocery Aisle 2</b><p>Three extended dwell signals were detected without visible staff engagement.</p></div><button onClick={() => { setActionedAlerts([...actionedAlerts,"assist"]); setDismissedAlerts([...dismissedAlerts,"assist"]); }}>Dispatch staff</button><button className="alertEvidence" onClick={() => setEvidence(evidenceItems[0])}>Evidence</button></div>}
        <div className="decisionHorizon"><article className="now"><small>NOW</small><b>Support Grocery Aisle</b><p>Repeated hesitation is visible in the current replay.</p></article><article><small>NEXT SHIFT</small><b>Prepare checkout capacity</b><p>Use the queue trigger before opening another counter.</p></article><article><small>LEARN</small><b>Run one controlled placement test</b><p>Compare ease, congestion and abandonment—not assumptions.</p></article></div>
        {section === "overview" && <>
          <header className="ownerPageHead"><div><small>01 · EXECUTIVE BRIEF · UPDATED JUST NOW</small><h1>Your store, in one decision-ready view</h1><p>The current replay supports a checkout-pressure review. Forecast panels below are clearly marked planning scenarios.</p></div><button onClick={() => prepareReport(true)}>Generate owner brief</button></header>
          {reportStatus && <div className="ownerNotice">{reportStatus}</div>}
          <div className="ownerKpis">
            <article><small>OBSERVED LOCAL TRACKS</small><strong>{state?.summary?.local_tracks ?? "—"}</strong><span>Across {state?.media?.assigned_files || 0} source clips</span></article>
            <article><small>INGESTION MODE</small><strong>Replay</strong><span>YOLO observations · batch stream</span></article>
            <article><small>BUSIEST ZONE</small><strong>{[...(profile?.comparison || [])].sort((a:any,b:any)=>b.local_tracks-a.local_tracks)[0]?.label || "—"}</strong><span>Measured from current footage</span></article>
            <article><small>CHECKOUT PRESSURE</small><strong>{counters === 2 ? "Elevated" : "Controlled"}</strong><span>{counters} active counters</span></article>
          </div>
          <div className="ownerGrid overviewGrid">
            <article className="ownerCard trafficCard"><header><div><small>02 · RUSH FORECAST</small><h2>Traffic today</h2></div><span className="demoBadge">PROJECTED BASELINE</span></header><MiniLineChart /><footer><b>Forecast</b><span>92 visitors at 4 PM</span><p>Prepare one additional checkout counter by 3:45 PM.</p></footer></article>
            <article className="ownerCard actionCard"><header><div><small>DECISIONS THAT NEED ATTENTION</small><h2>Recommended now</h2></div><b>3</b></header>
              <section><span className="priority high">HIGH</span><div><b>Prepare checkout capacity</b><p>Traffic is moving toward the projected peak.</p></div><button onClick={() => setCounters(3)}>Apply</button></section>
              <section><span className="priority medium">MED</span><div><b>Inspect Grocery Aisle 2</b><p>High attention with repeated hesitation signals.</p></div><button onClick={() => { setSection("journeys"); setEvidence(evidenceItems[0]); }}>Evidence</button></section>
              <section><span className="priority low">TEST</span><div><b>Trial bread–spread placement</b><p>Run a controlled layout experiment; measure basket path and abandonment.</p></div><button onClick={() => { setSection("performance"); setExperiment("design"); }}>Design</button></section>
            </article>
            <article className="ownerCard staffCard"><header><div><small>RUSH RESPONSE SIMULATOR</small><h2>What if we open another counter?</h2></div></header><div className="counterControl"><button onClick={() => setCounters(Math.max(1, counters - 1))}>−</button><strong>{counters}<small> active counters</small></strong><button onClick={() => setCounters(Math.min(5, counters + 1))}>+</button></div><div className="pressureTrack"><i style={{ width: `${Math.max(18, 82 - counters * 17)}%` }} /></div><p>Projected checkout pressure: <b>{counters >= 3 ? "Low" : counters === 2 ? "Medium" : "High"}</b></p><aside>Recommended: 3 counters between 3:45–5:15 PM.</aside></article>
          </div>
        </>}

        {section === "performance" && <>
          <header className="ownerPageHead"><div><small>STORE & PRODUCT INTELLIGENCE</small><h1>Where attention becomes opportunity</h1><p>Compare zones, understand visible product interest and design measurable placement experiments.</p></div><span className="ownerPill">4 active camera zones</span></header>
          <div className="ownerGrid performanceGrid">
            <article className="ownerCard aisleCard"><header><div><small>03 · AISLE PERFORMANCE</small><h2>Zone comparison</h2></div><span>Current footage</span></header><div className="aisleTable">
              {(profile?.comparison || []).map((item: any, index: number) => <section key={item.camera_id}><div><b>{item.label}</b><small>{item.camera_id}</small></div><strong>{item.local_tracks}</strong><div className="ownerBar"><i style={{width: `${item.local_tracks / maxTraffic * 100}%`}} /></div><span>{index === 0 ? "High flow" : index === 1 ? "Engagement opportunity" : index === 3 ? "Pressure watch" : "Stable"}</span></section>)}
            </div></article>
            <article className="ownerCard funnelOwner"><header><div><small>04 · PRODUCT-INTEREST FUNNEL</small><h2>Where visible interest may drop</h2></div><span className="futureBadge">MODEL READINESS</span></header><div className="funnelInteractive">{funnelStages.map(stage => <button key={stage.label} className={selectedFunnel === stage.label ? "active" : ""} onClick={() => setSelectedFunnel(stage.label)}><span style={{width:`${stage.value}%`}}/><b>{stage.label}</b><em>{stage.value}</em></button>)}</div><aside className="funnelExplanation"><small>SELECTED STAGE</small><b>{activeFunnel.label}: {activeFunnel.meaning}</b><p>{activeFunnel.evidence}</p></aside><p className="truthNote">Values demonstrate the intended interaction funnel. Camera-only observations and future-model stages are explicitly separated.</p></article>
            <article className="ownerCard placementCard"><header><div><small>05 · PLACEMENT DECISION STUDIO</small><h2>Choose a strategy for the shopping situation</h2></div><span className="demoBadge">CONTROLLED TEST</span></header><div className="placementChoices"><article><small>BUSY PERIOD</small><b>Reduce search friction</b><p>Keep complementary categories within a short route when crowd pressure is high.</p></article><article><small>QUIET RESTOCK PERIOD</small><b>Increase discovery</b><p>Test a measured category route when shoppers have time and aisles have capacity.</p></article><article><small>OCCASION SHOP</small><b>Create a mission-led zone</b><p>Build a clearly priced temporary display around the shopping mission.</p></article></div><button onClick={() => setExperiment("design")}>Open scenario planner</button></article>
          </div>
        </>}

        {section === "journeys" && <>
          <header className="ownerPageHead"><div><small>CUSTOMER EXPERIENCE</small><h1>See journeys, friction and missed moments</h1><p>Movement becomes an operational story while identity uncertainty stays visible.</p></div><span className="ownerPill">Privacy protected</span></header>
          <div className="ownerGrid journeyGrid">
            <article className="ownerCard journeyCard"><header><div><small>06 · CUSTOMER JOURNEY</small><h2>Most common observed route</h2></div><span>Journey hypothesis</span></header><div className="journeyRoute">{["Entrance","Produce","Grocery","Service","Checkout","Exit"].map((x,i) => <React.Fragment key={x}><span><i>{i+1}</i>{x}<small>{[100,72,64,38,55,48][i]}%</small></span>{i<5&&<b>→</b>}</React.Fragment>)}</div><div className="journeyStats"><span><b>2m 48s</b> visible journey proxy</span><span><b>Grocery</b> longest dwell zone</span><span><b>Service</b> largest route drop</span></div><p className="truthNote">Cross-camera links are scored hypotheses until synchronized footage confirms continuity.</p></article>
            <article className="ownerCard lossCard"><header><div><small>07 · LOST-OPPORTUNITY DETECTOR</small><h2>Moments worth reviewing</h2></div><b>6 signals</b></header>
              {evidenceItems.map(x => <section key={x.t}><strong>{x.n}</strong><div><b>{x.t}</b><p>{x.d}</p></div><button onClick={() => setEvidence(x)}>View evidence</button></section>)}
              <aside><b>Potential action:</b> Place assistance near Grocery Aisle 2 during the next comparable peak and measure whether hesitation falls.</aside>
            </article>
          </div>
        </>}

        {section === "planning" && <>
          <header className="ownerPageHead"><div><small>PLANNING & LEARNING</small><h1>Turn every shift into a better next shift</h1><p>Compare periods, deploy staff, run experiments and close the loop with a daily report.</p></div><button onClick={() => prepareReport()}>Prepare daily report</button></header>
          {reportStatus && <div className="ownerNotice">{reportStatus}</div>}
          <div className="ownerGrid planningGrid">
            <article className="ownerCard deploymentCard"><header><div><small>08 · STAFF DEPLOYMENT</small><h2>Recommended coverage</h2></div><span className="demoBadge">PROJECTED COVERAGE</span></header>{[["Entrance & Produce",2,"Covered"],["Main Grocery",3,"+1 at 4 PM"],["Service Counter",1,"Stable"],["Checkout",3,"+1 at 3:45 PM"]].map(([zone,note,status]) => <section key={String(zone)}><div><b>{zone}</b><small>{status}</small></div><strong>{note}</strong><span>staff</span></section>)}</article>
            <article className="ownerCard compareCard"><header><div><small>09 · COMPARATIVE ANALYTICS</small><h2>Weekday vs weekend</h2></div><span className="demoBadge">PROJECTED BASELINE</span></header>{[["Footfall",68,88],["Engagement",54,63],["Checkout pressure",42,76],["Assistance demand",36,58]].map(([label,weekday,weekend]) => <section key={String(label)}><b>{label}</b><div><i style={{width:`${weekday}%`}}/><span style={{width:`${weekend}%`}}/></div><small>Weekday {weekday} · Weekend {weekend}</small></section>)}<footer><span><i /> Weekday</span><span><i /> Weekend</span></footer></article>
            <article className="ownerCard reportCard"><header><div><small>10 · AUTOMATED OWNER REPORT</small><h2>Operational report centre</h2></div><span>{report ? "Prepared now" : "On demand"}</span></header><div className="reportPreview"><small>EXECUTIVE SUMMARY</small><p>The current footage produced a checkout-pressure review cue and measurable grocery-aisle dwell. Longer operating samples are required before calling either a recurring trend.</p><b>Next controlled test</b><p>Trial one additional checkout counter and one employee near the grocery aisle during a comparable window, then compare pressure and hesitation.</p>{report && <div className="reportLocation"><b>{report.report_id}</b><span>Stored locally at</span><code>{report.saved_to}</code></div>}</div><div className="reportActions"><button onClick={() => prepareReport()}>{report ? "Regenerate report" : "Generate operational report"}</button>{report && <button className="secondary" onClick={downloadReport}>Download report</button>}</div><p className="truthNote">Includes evidence, confidence and explicit data limitations.</p></article>
          </div>
        </>}
        {evidence && <div className="ownerModal" role="dialog" aria-label="Evidence review"><div className="modalCard"><header><div><small>CAMERA EVIDENCE REVIEW</small><h2>{evidence.t}</h2></div><button onClick={() => setEvidence(null)}>×</button></header><div className="evidenceSource"><span><b>{evidence.camera}</b> source camera</span><span><b>{evidence.window}</b> evidence window</span><span><b>{evidence.n}</b> detected signals</span></div><section><small>OBSERVED BY THE CAMERA PIPELINE</small><p>{evidence.observed}</p></section><section><small>BUSINESS INTERPRETATION</small><p>{evidence.inference}</p></section><aside>Privacy-safe evidence uses anonymous local track IDs. No face identity is stored or claimed.</aside><footer><button onClick={() => setEvidence(null)}>Close</button><button onClick={onTechnical}>Open technical evidence workspace</button></footer></div></div>}
        {weekendPlanOpen && <div className="ownerModal" role="dialog" aria-label="Weekend operating plan"><div className="modalCard weekendPlan"><header><div><small>WEEKEND OPERATING PLAN</small><h2>A practical plan your team can use</h2><p>Built from the projected weekend profile and current checkout review cue.</p></div><button onClick={() => setWeekendPlanOpen(false)}>×</button></header><div className="planSummary"><span><small>PLAN WINDOW</small><b>Saturday · 3:30–6:00 PM</b></span><span><small>PRIMARY RISK</small><b>Checkout and aisle congestion</b></span><span><small>OWNER</small><b>Shift manager</b></span></div><div className="planTimeline"><article><time>Before 3:30</time><div><b>Prepare capacity</b><p>Brief one flexible employee, confirm Counter 3 readiness and clear trolley obstructions.</p></div><span>Manager</span></article><article><time>3:45 PM</time><div><b>Open Counter 3 if queue threshold is reached</b><p>Trigger only when four or more visible tracks persist across the review window.</p></div><span>Checkout lead</span></article><article><time>4:00–5:15</time><div><b>Place assistance near Grocery</b><p>Respond to repeated hesitation while keeping the aisle route clear.</p></div><span>Floor lead</span></article><article><time>After 6:00</time><div><b>Close the learning loop</b><p>Compare queue pressure, assistance signals and congestion against the previous window.</p></div><span>APN report</span></article></div><aside><b>Success measures</b><span>Lower pressure frames</span><span>Shorter visible hesitation</span><span>No increase in blocked access</span></aside><footer><button onClick={() => setWeekendPlanOpen(false)}>Close</button><button onClick={() => {setSection("planning");setWeekendPlanOpen(false);}}>Review planning metrics</button></footer></div></div>}
        {experiment !== "closed" && <div className="ownerModal" role="dialog" aria-label="A/B placement experiment"><div className="modalCard experimentModal"><header><div><small>SCENARIO-AWARE PLACEMENT ENGINE</small><h2>When should products be together or apart?</h2></div><button onClick={() => setExperiment("closed")}>×</button></header><div className="scenarioTabs">{(Object.keys(scenarioModels) as Array<keyof typeof scenarioModels>).map(key => <button key={key} className={scenario === key ? "active" : ""} onClick={() => { setScenario(key); setExperiment("design"); }}><b>{scenarioModels[key].label}</b><small>{scenarioModels[key].crowd} crowd · {scenarioModels[key].mission}</small></button>)}</div>{experiment === "design" ? <><div className="scenarioContext"><span><small>EXPECTED CROWD</small><b>{activeScenario.crowd}</b></span><span><small>SHOPPING MISSION</small><b>{activeScenario.mission}</b></span><span><small>DECISION RULE</small><b>Crowding + mission + friction</b></span></div><div className="variantGrid"><article><small>VARIANT A</small><b>Complementary placement</b><p>Bread, butter and spreads placed together for speed and convenience.</p></article><article><small>VARIANT B</small><b>Discovery route</b><p>Categories separated across a measured route to increase discovery.</p></article></div><section><small>SUCCESS MEASURES</small><p>Search time · route friction · congestion · category discovery · abandonment · POS basket value when connected</p></section><aside>The engine uses explicit rules for this scenario. It does not randomly choose a variant or rearrange the physical store.</aside><footer><button onClick={() => setExperiment("closed")}>Cancel</button><button onClick={() => setExperiment("result")}>Evaluate this scenario</button></footer></> : <><div className={`experimentResult winner${activeScenario.winner}`}><small>RECOMMENDATION FOR {activeScenario.label.toUpperCase()}</small><strong>{activeScenario.winner === "C" ? "Occasion strategy" : `Variant ${activeScenario.winner}`}</strong><span>{activeScenario.title}</span><p>{activeScenario.explanation}</p></div><div className="scenarioScores"><header><b>Why this result changes</b><span>Projected decision indices</span></header>{["Customer ease","Congestion control","Discovery potential","Overall fit"].map((label,index) => <section key={label}><b>{label}</b><div><span>A</span><i style={{width:`${activeScenario.a[index]}%`}}/><em>{activeScenario.a[index]}</em></div><div><span>B</span><i className="b" style={{width:`${activeScenario.b[index]}%`}}/><em>{activeScenario.b[index]}</em></div></section>)}</div><div className="scenarioAction"><small>RECOMMENDED PILOT</small><b>{activeScenario.action}</b></div><footer><button onClick={() => setExperiment("design")}>Change scenario</button><button onClick={() => setExperiment("closed")}>Save pilot plan</button></footer></>}</div></div>}
      </section>
    </div>
  </main>;
}

function Landing({ onEnter }: { onEnter: () => void }) {
  const [role, setRole] = useState("Store Manager");
  return <main className="apnLanding">
    <nav><div className="landingBrand"><span>APN</span><b>Agentic Perception Network</b></div><small>SUPERMARKET INTELLIGENCE · PRIVATE VALIDATION ENVIRONMENT</small></nav>
    <section className="landingHero">
      <div className="landingCopy"><small>THE CAMERA-TO-DECISION OPERATING SYSTEM</small><h1>Your store already sees everything.<br/><em>Now it can understand.</em></h1><p>APN turns privacy-protected camera evidence into rush forecasts, aisle intelligence, customer-journey findings and decisions your team can act on.</p><div className="landingSignals"><span><i /> Anonymous movement</span><span><i /> Multi-agent reasoning</span><span><i /> Human-controlled action</span></div></div>
      <form className="accessCard" onSubmit={e => { e.preventDefault(); onEnter(); }}><small>SECURE WORKSPACE ACCESS</small><h2>Enter Meridian Supermarket</h2><p>Choose your role to open the appropriate intelligence workspace.</p><label>Work email<input type="email" defaultValue="manager@meridian.local" required /></label><label>Role<select value={role} onChange={e => setRole(e.target.value)}><option>Store Manager</option><option>Operations Lead</option><option>Technical Reviewer</option></select></label><label>Password<input type="password" defaultValue="apn-local" required /></label><button type="submit">Open {role} workspace <span>→</span></button><aside><i /> Local validation workspace · no external data is transmitted</aside></form>
    </section>
    <footer><span>Observe</span><i /><span>Investigate</span><i /><span>Explain</span><i /><span>Simulate</span><i /><span>Verify</span></footer>
  </main>;
}

function ProductPortal() {
  const [entered, setEntered] = useState(false);
  const [workspace, setWorkspace] = useState<"owner" | "technical">("owner");
  if (!entered) return <Landing onEnter={() => setEntered(true)} />;
  if (workspace === "owner") return <OwnerDashboard onTechnical={() => setWorkspace("technical")} onExit={() => setEntered(false)} />;
  return <div className="technicalPortal"><nav className="portalReturn"><button onClick={() => setWorkspace("owner")}>← Business owner workspace</button><span>TECHNICAL & EVIDENCE WORKSPACE</span></nav><App /></div>;
}
function App() {
  const [state, setState] = useState<State | null>(null),
    [observations, setObservations] = useState<Observation[]>([]),
    [cameraId, setCameraId] = useState("CAM-02"),
    [privacy, setPrivacy] = useState(true),
    [query, setQuery] = useState(
      "Why did checkout pressure increase and what should we do?",
    ),
    [result, setResult] = useState<AskResult | null>(null),
    [phase, setPhase] = useState(0),
    [deep, setDeep] = useState(false),
    [error, setError] = useState(""),
    [time, setTime] = useState(0),
    timer = useRef<number | undefined>(undefined);
  useEffect(() => {
    Promise.all([api("/api/state"), api("/api/observations")])
      .then(([s, o]) => {
        setState(s);
        setObservations(o);
      })
      .catch((e) => setError(e.message));
  }, []);
  const camera = state?.cameras.find((c) => c.id === cameraId),
    cameraRows = useMemo(
      () => observations.filter((row) => row.camera_id === cameraId),
      [observations, cameraId],
    );
  const run = async () => {
    if (!query.trim()) return;
    window.clearInterval(timer.current);
    setPhase(1);
    setResult(null);
    try {
      const response = (await api("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      })) as AskResult;
      setResult(response);
      let step = 1;
      timer.current = window.setInterval(() => {
        step++;
        setPhase(step);
        if (step >= response.agents.length + 2)
          window.clearInterval(timer.current);
      }, 650);
    } catch (e: any) {
      setError(e.message);
    }
  };
  if (error)
    return (
      <main className="boot">
        <h1>APN is not running</h1>
        <p>The interface cannot reach the intelligence engine.</p>
        <code>cd apn && ./run.sh</code>
        <small>{error}</small>
      </main>
    );
  if (!state || !camera)
    return (
      <main className="boot">
        <div className="loader" />
        Connecting surveillance to the agent network…
      </main>
    );
  return (
    <main className="command">
      <header className="header">
        <div className="logo">APN</div>
        <div>
          <h1>Agentic Perception Network</h1>
          <p>Ask the space. Watch the agents investigate.</p>
        </div>
        <span className="dataset">
          COMPOSED VIDEO TEST · {state.summary.observations} OBSERVATIONS
        </span>
        <div className="status">
          <i /> system ready
        </div>
      </header>
      <section className="osHero">
        <small>THE CAMERA-TO-DECISION OPERATING SYSTEM</small>
        <h2>Observe. Investigate. Explain. Simulate. Verify.</h2>
        <p>
          One guided operational story built from surveillance evidence,
          multi-agent reasoning and human-controlled action.
        </p>
        <a href="#store-overview">Start with the store overview ↓</a>
      </section>
      <StoreOverview
        state={state}
        observations={observations}
        selected={cameraId}
        onSelect={setCameraId}
      />
      <MediaProvenance catalog={state.media} />
      <section className="workspace" id="workspace">
        <div className="videoColumn">
          <div className="sectionTitle">
            <div>
              <small>02 · SELECTED CAMERA EVIDENCE</small>
              <h2>See what the system sees</h2>
            </div>
            <button
              className={privacy ? "privacy on" : "privacy"}
              onClick={() => setPrivacy(!privacy)}
            >
              <span /> Face privacy {privacy ? "on" : "off"}
            </button>
          </div>
          <div className="cameraStrip">
            {state.cameras.map((c) => (
              <button
                key={c.id}
                className={cameraId === c.id ? "selected" : ""}
                onClick={() => setCameraId(c.id)}
              >
                <i />
                <span>
                  <b>{c.id}</b>
                  <small>{c.name}</small>
                </span>
                <em>{c.agent_state}</em>
              </button>
            ))}
          </div>
          <Surveillance
            key={camera.id}
            camera={camera}
            observations={cameraRows}
            privacy={privacy}
            onTime={setTime}
          />
          <div className="videoTimeline">
            <span>{time.toFixed(1)}s</span>
            <div>
              <i
                style={{
                  width: `${Math.min(100, (time / (cameraRows.at(-1)?.ts_source || 1)) * 100)}%`,
                }}
              />
            </div>
            <span>{cameraRows.length} detections</span>
          </div>
          <CameraEvidenceLayer camera={camera} observations={cameraRows} />
        </div>
        <div className="intelligence">
          <div className="sectionTitle">
            <div>
              <small>03 · AGENTIC INVESTIGATION</small>
              <h2>Ask the master orchestrator</h2>
            </div>
            <span className="livePulse">
              <i /> agents online
            </span>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run();
            }}
            className="prompt"
          >
            <textarea
              aria-label="Ask the orchestrator"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about an aisle, movement, customer count, queue or bottleneck…"
            />
            <button type="submit">
              Investigate <span>→</span>
            </button>
          </form>
          <div className="suggestions">
            {[
              "How many customers were in aisle one?",
              "Analyse the checkout bottleneck",
              "Show movement across the store",
            ].map((x) => (
              <button key={x} onClick={() => setQuery(x)}>
                {x}
              </button>
            ))}
          </div>
          <AgentFlow phase={phase} result={result} />
          {result && phase >= result.agents.length + 2 ? (
            <Answer
              result={result}
              onExplore={() => {
                setDeep(true);
                setTimeout(
                  () =>
                    document
                      .getElementById("decision-studio")
                      ?.scrollIntoView({ behavior: "smooth" }),
                  100,
                );
              }}
            />
          ) : phase > 0 ? (
            <div className="thinking">
              <span />
              <p>
                {phase === 1
                  ? "Orchestrator is reading your intent…"
                  : "Agents are exchanging evidence…"}
              </p>
            </div>
          ) : (
            <div className="emptyState">
              <b>Your investigation will unfold here</b>
              <p>
                Submit a question to see the orchestrator choose agents,
                delegate work, verify evidence and return one clear answer.
              </p>
            </div>
          )}
        </div>
      </section>
      <InvestigationTheatre />
      <BusinessIntelligence />
      <DeepAnalysis cameraId={cameraId} />
      <SystemLaboratory />
      <footer>
        <span>
          <i className="boxIcon" /> detection & tracking
        </span>
        <span>
          <i className="blurIcon" /> privacy by design
        </span>
        <span>
          <i className="agentIcon" /> visible multi-agent reasoning
        </span>
        <b>Scores are decision cues, not identity probabilities.</b>
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<ProductPortal />);
