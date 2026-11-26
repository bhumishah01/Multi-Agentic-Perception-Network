from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    agent: str
    entity_id: str | None = None
    zone: str
    camera_ids: list[str]
    severity: str
    confidence: float = Field(ge=0, le=1)
    measurements: dict[str, float | int | str]
    thresholds: dict[str, float | int | str]
    explanation: str
    evidence: list[str]


class Hypothesis(BaseModel):
    id: str
    label: str
    supporting: list[str] = []
    contradicting: list[str] = []
    score: float = Field(ge=0, le=1)


class Case(BaseModel):
    case_id: str
    kind: str
    severity: str
    urgency: float = Field(ge=0, le=1)
    state: str
    entity_id: str | None
    zone: str
    camera_ids: list[str]
    opened_at: float
    timeline: list[dict]
    hypotheses: list[Hypothesis]
    findings: list[Finding]
    evidence: list[str]
    alternative_explanations: list[str]
    recommended_response: str
    human_decisions: list[dict]
    trace: list[str]
    narrative: str
