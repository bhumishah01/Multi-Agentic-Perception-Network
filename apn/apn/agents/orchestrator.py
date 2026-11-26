from __future__ import annotations
from apn.core import AsyncMessageBus, MessageEnvelope
from apn.cases import CaseBuilder


class OrchestratorAgent:
    def __init__(self, bus: AsyncMessageBus, builder: CaseBuilder) -> None:
        self.bus = bus
        self.builder = builder
        bus.subscribe("finding", self.on_finding)

    async def on_finding(self, message: MessageEnvelope) -> None:
        case = self.builder.from_finding(message)
        message_type = "case.opened" if len(case.findings) == 1 else "case.updated"
        await self.bus.publish(message_type, "orchestrator-agent", ts_source=message.ts_source,
                               inferred={"case": case.model_dump(mode="json")},
                               assumptions=("urgency uses configured deterministic weights",),
                               confidence=case.findings[-1].confidence, evidence=tuple(case.evidence),
                               caused_by=message.id, ts_ingest=message.ts_ingest)
