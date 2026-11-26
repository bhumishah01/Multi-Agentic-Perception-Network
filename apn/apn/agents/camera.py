from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import math

from apn.core import AsyncMessageBus, MessageEnvelope


@dataclass
class TrackMemory:
    camera_id: str
    track_id: str
    observations: deque[dict] = field(default_factory=deque)
    zone: str | None = None
    zone_entered_at: float | None = None
    last_exit_prediction: float | None = None


class CameraAgent:
    def __init__(self, camera_id: str, bus: AsyncMessageBus, neighbours: list[str],
                 edges: list[dict], memory_s: float = 10.0, frame_width: int = 1280) -> None:
        self.camera_id = camera_id
        self.bus = bus
        self.neighbours = neighbours
        self.edges = edges
        self.memory_s = memory_s
        self.frame_width = frame_width
        self.tracks: dict[str, TrackMemory] = {}
        self.processed = 0
        self.last_heartbeat = 0.0
        bus.subscribe("observation", self.on_observation)

    async def on_observation(self, message: MessageEnvelope) -> None:
        observation = message.observed
        if observation.get("camera_id") != self.camera_id:
            return
        self.processed += 1
        self.last_heartbeat = message.ts_source
        track_id = observation["local_track_id"]
        memory = self.tracks.setdefault(track_id, TrackMemory(self.camera_id, track_id))
        memory.observations.append(observation)
        while memory.observations and message.ts_source - memory.observations[0]["store_ts"] > self.memory_s:
            memory.observations.popleft()
        await self.bus.publish(
            "track.updated", f"camera-agent:{self.camera_id}", ts_source=message.ts_source,
            observed={"camera_id": self.camera_id, "local_track_id": track_id,
                      "observation_count_window": len(memory.observations), "last": observation},
            evidence=(message.id, *message.evidence), caused_by=message.id,
            score=observation.get("detector_score"), ts_ingest=message.ts_ingest,
        )
        zone = observation["zone"]
        if memory.zone != zone:
            if memory.zone is not None:
                await self._zone_event(message, memory, "exited", memory.zone)
            memory.zone = zone
            memory.zone_entered_at = message.ts_source
            await self._zone_event(message, memory, "entered", zone)
        await self._maybe_predict_exit(message, memory)

    async def _zone_event(self, parent: MessageEnvelope, memory: TrackMemory, action: str, zone: str) -> None:
        dwell = max(0.0, parent.ts_source - (memory.zone_entered_at or parent.ts_source))
        await self.bus.publish(
            "zone.event", f"camera-agent:{self.camera_id}", ts_source=parent.ts_source,
            observed={"camera_id": self.camera_id, "local_track_id": memory.track_id,
                      "zone": zone, "action": action, "dwell_s": dwell},
            evidence=(parent.id,), caused_by=parent.id, ts_ingest=parent.ts_ingest,
        )

    async def _maybe_predict_exit(self, parent: MessageEnvelope, memory: TrackMemory) -> None:
        if len(memory.observations) < 2 or not self.edges:
            return
        previous, current = memory.observations[-2], memory.observations[-1]
        width = self.frame_width
        x_previous, x_current = previous["foot_px"][0], current["foot_px"][0]
        direction = "right" if x_current > x_previous else "left"
        edge = next((item for item in self.edges if item["side"] == direction), None)
        if edge is None:
            return
        near_edge = (direction == "right" and x_current >= .85 * width) or (direction == "left" and x_current <= .15 * width)
        if not near_edge or memory.last_exit_prediction == parent.ts_source:
            return
        memory.last_exit_prediction = parent.ts_source
        await self.bus.publish(
            "exit.predicted", f"camera-agent:{self.camera_id}", ts_source=parent.ts_source,
            observed={"source_camera": self.camera_id, "source_track": memory.track_id,
                      "last_foot_floor": current.get("foot_floor"), "exit_edge": direction},
            inferred={"target_camera": edge["leads_to"], "eta_s": 2.0},
            assumptions=("configured camera edge topology", "constant short-term motion"),
            confidence=.6, evidence=(parent.id,), caused_by=parent.id, ts_ingest=parent.ts_ingest,
        )

    def status(self) -> dict:
        return {"camera_id": self.camera_id, "processed_observations": self.processed,
                "active_tracks": len(self.tracks), "last_heartbeat": self.last_heartbeat}
