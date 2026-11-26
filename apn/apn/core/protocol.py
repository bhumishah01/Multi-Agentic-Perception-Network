"""Validated message protocol shared by every APN agent."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MessageType = Literal[
    "observation", "track.updated", "handoff.request", "handoff.offer",
    "handoff.response", "identity.link", "identity.unlink", "zone.event",
    "exit.predicted", "hypothesis", "finding", "finding.abstained",
    "case.opened", "case.updated", "evidence.attached", "human.decision",
    "health.alert", "privacy.action", "agent.error", "agent.heartbeat",
]


class MessageEnvelope(BaseModel):
    """The only permitted envelope for agent-to-agent communication."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str = Field(pattern=r"^MSG-\d{6,}$")
    type: MessageType
    sender: str = Field(min_length=1, max_length=120)
    ts_source: float = Field(ge=0)
    ts_ingest: float = Field(ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    observed: dict[str, Any] = Field(default_factory=dict)
    inferred: dict[str, Any] = Field(default_factory=dict)
    assumptions: tuple[str, ...] = ()
    confidence: float | None = Field(default=None, ge=0, le=1)
    score: float | None = None
    evidence: tuple[str, ...] = ()
    caused_by: str | None = None
    visibility_role: tuple[str, ...] = ("security_operator", "investigator", "admin")
    prev_hash: str = ""
    hash: str = ""

    @field_validator("evidence")
    @classmethod
    def evidence_is_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("evidence references must be unique")
        return value

    @model_validator(mode="after")
    def inference_requires_basis(self) -> "MessageEnvelope":
        if self.inferred and not (self.evidence or self.caused_by):
            raise ValueError("inference requires evidence or a causal parent")
        return self

    def without_chain_fields(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"hash"})
