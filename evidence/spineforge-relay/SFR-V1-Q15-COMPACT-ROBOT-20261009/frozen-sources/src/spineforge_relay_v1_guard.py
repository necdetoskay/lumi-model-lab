"""Local deterministic + semantic guard contracts for SpineForge Relay v1."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.spineforge_relay_v1_contracts import (
    SceneContractV1,
    SceneValidationV1,
    StoryStateV1,
    ValidationFinding,
    canonical_sha256,
)


GUARD_FAMILIES = {
    "physical",
    "causal",
    "state",
    "spatial",
    "temporal",
    "epistemic",
    "canon",
    "spine",
    "narrative",
    "contract",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SemanticGuardFindingV1(StrictModel):
    code: str = Field(min_length=1)
    family: Literal[
        "physical",
        "causal",
        "state",
        "spatial",
        "temporal",
        "epistemic",
        "canon",
        "spine",
        "narrative",
    ]
    severity: Literal["BLOCKING", "WARN"]
    exact_text: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    repair_instruction: str = Field(min_length=1)


class SemanticGuardReportV1(StrictModel):
    schema_name: Literal["spineforge-relay.semantic-guard.v1"] = "spineforge-relay.semantic-guard.v1"
    decision: Literal["PASS", "REWRITE"]
    findings: list[SemanticGuardFindingV1] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_decision(self) -> "SemanticGuardReportV1":
        blocking = [row for row in self.findings if row.severity == "BLOCKING"]
        if self.decision == "PASS" and blocking:
            raise ValueError("PASS cannot contain blocking semantic findings")
        if self.decision == "REWRITE" and not blocking:
            raise ValueError("REWRITE requires at least one blocking semantic finding")
        return self


SEMANTIC_GUARD_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_name", "decision", "findings", "summary"],
    "properties": {
        "schema_name": {
            "type": "string",
            "enum": ["spineforge-relay.semantic-guard.v1"],
        },
        "decision": {"type": "string", "enum": ["PASS", "REWRITE"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "code",
                    "family",
                    "severity",
                    "exact_text",
                    "reason",
                    "repair_instruction",
                ],
                "properties": {
                    "code": {"type": "string", "minLength": 1},
                    "family": {
                        "type": "string",
                        "enum": [
                            "physical",
                            "causal",
                            "state",
                            "spatial",
                            "temporal",
                            "epistemic",
                            "canon",
                            "spine",
                            "narrative",
                        ],
                    },
                    "severity": {"type": "string", "enum": ["BLOCKING", "WARN"]},
                    "exact_text": {"type": "string", "minLength": 1},
                    "reason": {"type": "string", "minLength": 1},
                    "repair_instruction": {"type": "string", "minLength": 1},
                },
            },
        },
        "summary": {"type": "string", "minLength": 1},
    },
}


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", text))


def deterministic_scene_findings(
    *,
    prose: str,
    contract: SceneContractV1,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    count = word_count(prose)
    if count < contract.target_words_min or count > contract.target_words_max:
        findings.append(
            ValidationFinding(
                code="WORD_BUDGET_OUTSIDE_CONTRACT",
                family="contract",
                severity="BLOCKING",
                message=(
                    f"Scene word count {count} is outside "
                    f"{contract.target_words_min}..{contract.target_words_max}."
                ),
                evidence=[str(count)],
            )
        )
    if not prose.strip():
        findings.append(
            ValidationFinding(
                code="EMPTY_SCENE",
                family="contract",
                severity="BLOCKING",
                message="Scene prose is empty.",
                evidence=[],
            )
        )
    return findings


def build_semantic_guard_input(
    *,
    state: StoryStateV1,
    contract: SceneContractV1,
    prose: str,
    deterministic_findings: list[ValidationFinding],
) -> dict[str, Any]:
    return {
        "schema": "spineforge-relay.semantic-guard-input.v1",
        "story_state": state.model_dump(mode="json"),
        "scene_contract": contract.model_dump(mode="json"),
        "candidate_prose": prose,
        "candidate_prose_sha256": canonical_sha256({"prose": prose}),
        "deterministic_findings": [
            row.model_dump(mode="json") for row in deterministic_findings
        ],
        "semantic_policy": {
            "blocking_only_for_real_state_or_story_contract_defects": True,
            "style_preference_is_not_blocking": True,
            "epistemic_claims_need_provenance": True,
            "new_persistent_facts_need_contract_authority": True,
            "do_not_rewrite": True,
        },
    }


def normalize_semantic_guard(
    *,
    raw: dict[str, Any],
    prose: str,
) -> SemanticGuardReportV1:
    report = SemanticGuardReportV1.model_validate(raw)
    seen: set[tuple[str, str]] = set()
    for finding in report.findings:
        if finding.exact_text not in prose:
            raise RuntimeError(
                f"Semantic guard exact_text is not present in candidate prose: {finding.code}"
            )
        key = (finding.code, finding.exact_text)
        if key in seen:
            raise RuntimeError("Duplicate semantic guard finding")
        seen.add(key)
    return report


def combine_scene_validation(
    *,
    scene_id: str,
    attempt: Literal[1, 2],
    deterministic: list[ValidationFinding],
    semantic: SemanticGuardReportV1,
) -> SceneValidationV1:
    findings = list(deterministic)
    findings.extend(
        ValidationFinding(
            code=row.code,
            family=row.family,
            severity=row.severity,
            message=row.reason,
            evidence=[row.exact_text, row.repair_instruction],
        )
        for row in semantic.findings
    )
    blocking = [row for row in findings if row.severity == "BLOCKING"]
    deterministic_pass = not any(
        row.severity == "BLOCKING" for row in deterministic
    )
    if blocking:
        decision = "REWRITE" if attempt == 1 else "REJECT_NON_CONVERGENT"
    else:
        decision = "ACCEPT"
    return SceneValidationV1(
        scene_id=scene_id,
        attempt=attempt,
        deterministic_pass=deterministic_pass,
        semantic_guard_used=True,
        decision=decision,
        findings=findings,
    )
