from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from apn.core import AsyncMessageBus, MessageEnvelope


@dataclass(frozen=True)
class HandoffPolicy:
    weights: dict[str, float]
    accept: float = .80
    margin: float = .10
    ambiguous: float = .62

    def decide(self, components: dict[str, float], runner_up: float = 0.0) -> dict:
        required = {"appearance", "temporal", "spatial", "topology", "exclusivity"}
        if set(components) != required or any(not 0 <= value <= 1 for value in components.values()):
            raise ValueError("handoff requires five component scores in [0,1]")
        score = sum(self.weights[name] * components[name] for name in required)
        margin = score - runner_up
        state = "accepted" if score >= self.accept and margin >= self.margin else "ambiguous" if score >= self.ambiguous else "rejected"
        return {"state": state, "score": round(score, 6), "margin": round(margin, 6), "components": components}


def assign_exclusive(requests: list[str], candidates: list[str], scores: dict[tuple[str,str],float]) -> list[tuple[str,str,float]]:
    """Exact small-batch assignment preventing two requests claiming one track."""
    if not requests or not candidates:return []
    size=min(len(requests),len(candidates));best:list[tuple[str,str,float]]=[];best_total=-1.0
    for chosen in permutations(candidates,size):
        assignment=[(requests[index],chosen[index],scores.get((requests[index],chosen[index]),0.0)) for index in range(size)]
        total=sum(item[2] for item in assignment)
        if total>best_total:best,best_total=assignment,total
    return best


class HandoffAgent:
    def __init__(self, bus: AsyncMessageBus, topology: dict[str, list[str]], expiry_s: float = 20) -> None:
        self.bus = bus
        self.topology = topology
        self.expiry_s = expiry_s
        bus.subscribe("exit.predicted", self.on_exit)

    async def on_exit(self, message: MessageEnvelope) -> None:
        source = message.observed["source_camera"]
        payload = {
            "source_camera": source, "source_track": message.observed["source_track"],
            "embedding_ref": message.payload.get("embedding_ref"),
            "last_foot_floor": message.observed.get("last_foot_floor"),
            "exit_dir": message.observed["exit_edge"], "candidate_cameras": self.topology.get(source, []),
            "expiry_s": self.expiry_s, "minimal_disclosure": True,
        }
        if any(key in payload for key in ("crop", "crop_ref", "image", "bytes")):
            raise ValueError("minimal-disclosure handoff must not contain crop data")
        await self.bus.publish(
            "handoff.request", "handoff-agent", ts_source=message.ts_source,
            observed={"source_camera": source, "source_track": payload["source_track"]},
            inferred={"candidate_cameras": payload["candidate_cameras"]},
            assumptions=("configured topology is current",), payload=payload,
            evidence=(message.id,), caused_by=message.id, ts_ingest=message.ts_ingest,
        )
