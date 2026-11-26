from __future__ import annotations

from dataclasses import dataclass, field
from apn.core import AsyncMessageBus
from .handoff import HandoffPolicy


@dataclass
class GlobalEntity:
    entity_id: str
    members: set[str] = field(default_factory=set)
    links: list[dict] = field(default_factory=list)


class IdentityAgent:
    def __init__(self, bus: AsyncMessageBus, policy: HandoffPolicy) -> None:
        self.bus = bus
        self.policy = policy
        self.entities: dict[str, GlobalEntity] = {}
        self.track_entity: dict[str, str] = {}
        self.ambiguous: list[dict] = []

    def _entity_for(self, track: str) -> GlobalEntity:
        entity_id = self.track_entity.get(track)
        if entity_id is None:
            entity_id = f"E-{len(self.entities) + 1:03d}"
            self.entities[entity_id] = GlobalEntity(entity_id, {track})
            self.track_entity[track] = entity_id
        return self.entities[entity_id]

    async def evaluate(self, source_track: str, target_track: str, components: dict[str, float],
                       runner_up: float, ts_source: float, caused_by: str) -> dict:
        decision = self.policy.decide(components, runner_up)
        link = {"source_track": source_track, "target_track": target_track, **decision}
        if decision["state"] == "accepted":
            source = self._entity_for(source_track)
            target = self._entity_for(target_track)
            if source.entity_id != target.entity_id:
                source.members.update(target.members)
                source.links.extend(target.links)
                for member in target.members:
                    self.track_entity[member] = source.entity_id
                del self.entities[target.entity_id]
            source.links.append(link)
            message = await self.bus.publish(
                "identity.link", "identity-agent", ts_source=ts_source,
                observed={"source_track": source_track, "target_track": target_track},
                inferred={"entity_id": source.entity_id, "decision": decision},
                assumptions=("appearance descriptor is non-biometric",), score=decision["score"],
                evidence=(caused_by,), caused_by=caused_by, ts_ingest=ts_source,
            )
            link["message_id"] = message.id
        elif decision["state"] == "ambiguous":
            self.ambiguous.append(link)
        return link

    async def unlink(self, source_track: str, target_track: str, ts_source: float, caused_by: str) -> None:
        entity_id = self.track_entity.get(source_track)
        if not entity_id or self.track_entity.get(target_track) != entity_id:
            return
        entity = self.entities[entity_id]
        entity.members.discard(target_track)
        entity.links = [link for link in entity.links if not (link["source_track"] == source_track and link["target_track"] == target_track)]
        new_id = f"E-{len(self.entities) + 1:03d}"
        self.entities[new_id] = GlobalEntity(new_id, {target_track})
        self.track_entity[target_track] = new_id
        await self.bus.publish(
            "identity.unlink", "identity-agent", ts_source=ts_source,
            observed={"source_track": source_track, "target_track": target_track},
            inferred={"source_entity": entity_id, "split_entity": new_id, "recompute_required": True},
            assumptions=("human decision overrides automated link",), evidence=(caused_by,),
            caused_by=caused_by, ts_ingest=ts_source,
        )

    def identity_bounds(self) -> tuple[int, int]:
        maximum = len(self.entities) + len(self.ambiguous)
        minimum = len(self.entities)
        return minimum, maximum
