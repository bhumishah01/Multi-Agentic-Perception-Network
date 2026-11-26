"""Event-driven multi-agent intelligence core for APN.

The module is deliberately UI-independent.  Every conclusion travels as a typed
message with evidence and reasoning so a later workspace can replay the exact
path from observation to case.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections import defaultdict, deque
from typing import Any, Callable
import hashlib
import time


@dataclass(frozen=True)
class Message:
    id: str
    topic: str
    sender: str
    ts: float
    payload: dict[str, Any]
    evidence: tuple[str, ...] = ()
    caused_by: str | None = None


@dataclass
class Case:
    id: str
    kind: str
    entity_id: str
    zone: str
    severity: str
    state: str
    opened_at: float
    updated_at: float
    title: str
    explanation: str
    evidence: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)


class Runtime:
    """Small deterministic message bus with a complete causal ledger."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Callable[[Message], None]]] = defaultdict(list)
        self._queue: deque[Message] = deque()
        self.ledger: list[Message] = []
        self._sequence = 0

    def subscribe(self, topic: str, handler: Callable[[Message], None]) -> None:
        self._subscriptions[topic].append(handler)

    def publish(
        self,
        topic: str,
        sender: str,
        payload: dict[str, Any],
        *,
        ts: float | None = None,
        evidence: tuple[str, ...] = (),
        caused_by: str | None = None,
    ) -> Message:
        self._sequence += 1
        message = Message(
            id=f"MSG-{self._sequence:06d}", topic=topic, sender=sender,
            ts=time.time() if ts is None else float(ts), payload=payload,
            evidence=evidence, caused_by=caused_by,
        )
        self._queue.append(message)
        return message

    def drain(self) -> list[Message]:
        delivered: list[Message] = []
        while self._queue:
            message = self._queue.popleft()
            self.ledger.append(message)
            delivered.append(message)
            for handler in self._subscriptions.get(message.topic, ()):
                handler(message)
        return delivered


class TrackingAgent:
    name = "tracking-agent"

    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.tracks: dict[tuple[str, str], dict[str, Any]] = {}
        runtime.subscribe("observation.created", self.on_observation)

    def on_observation(self, message: Message) -> None:
        p = message.payload
        key = (p["camera_id"], p["local_track_id"])
        track = self.tracks.setdefault(key, {
            "entity_id": self._entity_id(*key), "first_seen": message.ts,
            "observations": 0, "zones": [],
        })
        track["last_seen"] = message.ts
        track["observations"] += 1
        if not track["zones"] or track["zones"][-1] != p["zone"]:
            track["zones"].append(p["zone"])
        self.runtime.publish("track.updated", self.name, {
            **p, **track, "dwell_seconds": round(message.ts - track["first_seen"], 3),
        }, ts=message.ts, evidence=(message.id, *message.evidence), caused_by=message.id)

    @staticmethod
    def _entity_id(camera_id: str, local_track_id: str) -> str:
        digest = hashlib.sha1(f"{camera_id}:{local_track_id}".encode()).hexdigest()[:8].upper()
        return f"ENTITY-{digest}"


class BehaviourAgent:
    name = "behaviour-agent"

    def __init__(self, runtime: Runtime, dwell_threshold: float = 30.0) -> None:
        self.runtime = runtime
        self.dwell_threshold = dwell_threshold
        self.reported: set[tuple[str, str]] = set()
        runtime.subscribe("track.updated", self.on_track)

    def on_track(self, message: Message) -> None:
        p = message.payload
        key = (p["entity_id"], p["zone"])
        if p["dwell_seconds"] < self.dwell_threshold or key in self.reported:
            return
        self.reported.add(key)
        self.runtime.publish("finding.created", self.name, {
            "kind": "extended_dwell", "entity_id": p["entity_id"], "zone": p["zone"],
            "severity": "attention", "confidence": p["confidence"],
            "measurement": {"dwell_seconds": p["dwell_seconds"], "threshold_seconds": self.dwell_threshold},
            "explanation": f"Observed dwell of {p['dwell_seconds']:.1f}s exceeds the configured {self.dwell_threshold:.1f}s threshold.",
        }, ts=message.ts, evidence=message.evidence, caused_by=message.id)


class SecurityAgent:
    name = "security-agent"

    def __init__(self, runtime: Runtime, restricted_zones: set[str] | None = None) -> None:
        self.runtime = runtime
        self.restricted_zones = restricted_zones or {"Restricted"}
        self.reported: set[tuple[str, str]] = set()
        runtime.subscribe("track.updated", self.on_track)

    def on_track(self, message: Message) -> None:
        p = message.payload
        key = (p["entity_id"], p["zone"])
        if p["zone"] not in self.restricted_zones or key in self.reported:
            return
        self.reported.add(key)
        self.runtime.publish("finding.created", self.name, {
            "kind": "restricted_zone_entry", "entity_id": p["entity_id"], "zone": p["zone"],
            "severity": "high", "confidence": p["confidence"],
            "measurement": {"zone": p["zone"]},
            "explanation": f"An entity was observed inside restricted zone {p['zone']}.",
        }, ts=message.ts, evidence=message.evidence, caused_by=message.id)


class OrchestratorAgent:
    name = "orchestrator-agent"

    def __init__(self, runtime: Runtime, minimum_confidence: float = 0.55) -> None:
        self.runtime = runtime
        self.minimum_confidence = minimum_confidence
        self.cases: dict[tuple[str, str, str], Case] = {}
        runtime.subscribe("finding.created", self.on_finding)

    def on_finding(self, message: Message) -> None:
        p = message.payload
        if float(p["confidence"]) < self.minimum_confidence:
            self.runtime.publish("finding.abstained", self.name, {
                "finding": p, "reason": "confidence_below_case_threshold",
                "threshold": self.minimum_confidence,
            }, ts=message.ts, evidence=message.evidence, caused_by=message.id)
            return
        key = (p["kind"], p["entity_id"], p["zone"])
        case = self.cases.get(key)
        if case is None:
            case_id = f"CASE-{len(self.cases) + 1:05d}"
            case = Case(
                id=case_id, kind=p["kind"], entity_id=p["entity_id"], zone=p["zone"],
                severity=p["severity"], state="open", opened_at=message.ts, updated_at=message.ts,
                title=p["kind"].replace("_", " ").title(), explanation=p["explanation"],
            )
            self.cases[key] = case
        case.updated_at = message.ts
        case.evidence = list(dict.fromkeys([*case.evidence, *message.evidence]))
        case.trace = list(dict.fromkeys([*case.trace, *(x for x in (message.caused_by, message.id) if x)]))
        case.findings.append({"agent": message.sender, **p})
        self.runtime.publish("case.updated", self.name, asdict(case), ts=message.ts,
                             evidence=tuple(case.evidence), caused_by=message.id)


class IntelligenceEngine:
    """Facade used by video adapters, tests, and eventually the API layer."""

    def __init__(self, *, dwell_threshold: float = 30.0,
                 restricted_zones: set[str] | None = None,
                 minimum_confidence: float = 0.55) -> None:
        self.runtime = Runtime()
        self.tracking = TrackingAgent(self.runtime)
        self.behaviour = BehaviourAgent(self.runtime, dwell_threshold)
        self.security = SecurityAgent(self.runtime, restricted_zones)
        self.orchestrator = OrchestratorAgent(self.runtime, minimum_confidence)

    def observe(self, *, ts: float, camera_id: str, local_track_id: str, zone: str,
                confidence: float, evidence_id: str) -> list[Message]:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be in [0,1]")
        self.runtime.publish("observation.created", f"camera-agent:{camera_id}", {
            "camera_id": camera_id, "local_track_id": local_track_id,
            "zone": zone, "confidence": confidence,
        }, ts=ts, evidence=(evidence_id,))
        return self.runtime.drain()

    def cases(self) -> list[dict[str, Any]]:
        return [asdict(case) for case in self.orchestrator.cases.values()]

    def trace(self) -> list[dict[str, Any]]:
        return [asdict(message) for message in self.runtime.ledger]

