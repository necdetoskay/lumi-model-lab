"""Generic event evidence checks. Semantic extraction is not deterministic truth.

The guard maps natural language to frozen predicates and audits residual meaning.
This module checks completeness, attribution, exact anchors and provenance locally.
It never awards satisfaction from keyword presence or a writer's assertion alone.
"""
from __future__ import annotations

from typing import Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import (
    StrictModel, Provenance, SceneContractV1, StoryStateV1, ValidationFinding,
)
from src.spineforge_relay_v1_compile import _value_at


class PredicateEvidenceV1(StrictModel):
    event_id: str
    predicate_id: str
    subject: str
    action: str
    target: str
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "AMBIGUOUS"]
    provenance: Provenance
    exact_text: str
    evidence_subject: str
    state_pointer: str | None
    reason: str = Field(min_length=1)


def evaluate_events(*, contract: SceneContractV1, state: StoryStateV1,
                    prose: str, evidence: list[PredicateEvidenceV1]) -> list[ValidationFinding]:
    findings = []

    def block(code, message, anchors=None):
        findings.append(ValidationFinding(code=code, family="contract", severity="BLOCKING",
                                          message=message, evidence=anchors or []))

    expected = {(e.id, p.id): (e, p) for e in contract.required_events for p in e.predicates}
    seen = set()
    for row in evidence:
        key = (row.event_id, row.predicate_id)
        if key not in expected or key in seen:
            block("EVENT_EVIDENCE_ID", f"Unknown or duplicate predicate: {key}")
            continue
        seen.add(key)
        event, predicate = expected[key]
        if (row.subject, row.action, row.target) != (predicate.subject, predicate.action, predicate.target):
            block("EVENT_ATTRIBUTION", f"Predicate attribution mismatch: {key}")
        if row.verdict != "SUPPORTED":
            block("EVENT_NOT_SATISFIED", f"{key}: {row.verdict}: {row.reason}")
        if not row.exact_text.strip() or row.exact_text not in prose:
            block("EVENT_UNGROUNDED", f"No exact prose anchor for {key}")
        if row.provenance not in event.allowed_provenance or row.provenance in event.forbidden_provenance:
            block("EVENT_PROVENANCE", f"Forbidden evidence provenance for {key}")
        if row.evidence_subject.casefold() in {s.casefold() for s in event.forbidden_evidence_subjects}:
            block("EVENT_FORBIDDEN_SUBJECT", f"Forbidden evidence subject for {key}")
        if row.provenance == "STORY_STATE_KNOWLEDGE":
            # The quote remains mandatory: established knowledge must be used in prose.
            prefix = "/characters/" + row.subject.replace("~", "~0").replace("/", "~1") + "/knowledge/"
            exists, value = _value_at(state.model_dump(mode="json"), row.state_pointer or "") if row.state_pointer else (False, None)
            if not row.state_pointer or not row.state_pointer.startswith(prefix) or not exists or value != row.evidence_subject:
                block("EVENT_KNOWLEDGE_SOURCE", f"Unestablished or wrong-character knowledge for {key}")
        elif row.state_pointer is not None:
            block("EVENT_SOURCE_MISMATCH", f"Direct observation cannot claim a state pointer: {key}")
    for key in expected.keys() - seen:
        block("EVENT_MISSING_EVIDENCE", f"Missing predicate evidence: {key}")
    return findings
