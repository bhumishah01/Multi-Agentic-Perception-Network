from __future__ import annotations
from apn.core import HashChainedLedger, MessageEnvelope
from .models import Case, Finding, Hypothesis


SEVERITY_WEIGHT = {"info": .25, "attention": .6, "high": 1.0}


class CaseBuilder:
    def __init__(self, ledger: HashChainedLedger) -> None:
        self.ledger = ledger
        self.cases: dict[str, Case] = {}
        self._keys: dict[tuple, str] = {}

    def from_finding(self, message: MessageEnvelope) -> Case:
        finding = Finding.model_validate({**message.inferred["finding"], "evidence": list(message.evidence)})
        key = (finding.kind, finding.entity_id, finding.zone)
        if key in self._keys:
            case = self.cases[self._keys[key]]
            case.findings.append(finding)
            case.trace.append(message.id)
            case.evidence = list(dict.fromkeys(case.evidence + finding.evidence))
            return case
        case_id = f"CASE-{len(self.cases)+1:05d}"
        hypotheses = self._hypotheses(finding)
        urgency = round(min(1.0, SEVERITY_WEIGHT.get(finding.severity, .25) * finding.confidence), 6)
        case = Case(
            case_id=case_id, kind=finding.kind, severity=finding.severity, urgency=urgency,
            state="needs_human" if urgency >= .45 else "open", entity_id=finding.entity_id,
            zone=finding.zone, camera_ids=finding.camera_ids, opened_at=message.ts_source,
            timeline=[{"ts": message.ts_source, "event": finding.kind, "message_id": message.id}],
            hypotheses=hypotheses, findings=[finding], evidence=finding.evidence,
            alternative_explanations=[item.label for item in hypotheses[1:]],
            recommended_response="Review linked evidence and confirm context; no external action is automatic.",
            human_decisions=[], trace=[item.id for item in self.ledger.trace(message.id)],
            narrative=self._narrative(finding),
        )
        self.cases[case_id] = case
        self._keys[key] = case_id
        return case

    @staticmethod
    def _hypotheses(finding: Finding) -> list[Hypothesis]:
        if finding.kind in {"extended_dwell", "loitering"}:
            return [
                Hypothesis(id="H-1", label="needs_assistance", supporting=[finding.explanation], score=.55),
                Hypothesis(id="H-2", label="comparing_products", supporting=["prolonged shelf-area presence"], score=.5),
                Hypothesis(id="H-3", label="congestion_wait", supporting=[], contradicting=["queue membership not established"], score=.3),
                Hypothesis(id="H-4", label="unverified_security_cue", supporting=[finding.explanation], contradicting=["intent cannot be observed"], score=.2),
            ]
        return [Hypothesis(id="H-1", label=finding.kind, supporting=[finding.explanation], score=finding.confidence),
                Hypothesis(id="H-2", label="normal_operational_context", contradicting=[finding.explanation], score=.25)]

    @staticmethod
    def _narrative(finding: Finding) -> str:
        subject = finding.entity_id or "An observed entity"
        return (f"{subject} produced a {finding.kind.replace('_',' ')} finding in {finding.zone}. "
                f"{finding.explanation} This is a review cue, not a conclusion about intent.")

    def why(self, case_id: str) -> dict:
        case = self.cases[case_id]
        return {"case_id": case_id, "trace": [item.model_dump(mode="json") for item in self.ledger.trace(case.trace[-1])],
                "thresholds": [finding.thresholds for finding in case.findings],
                "hypotheses": [item.model_dump() for item in case.hypotheses],
                "evidence_that_would_change_conclusion": ["human context", "additional camera view", "identity correction"]}
