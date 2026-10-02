from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_story_audit_once import (
    PRIMARY_MODEL,
    SECONDARY_MODEL,
    execute_story_audit_once,
)


MANIFEST = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)

FAMILY_ORDER = [
    "physical_feasibility",
    "causal_logic",
    "state_continuity",
    "epistemic_order",
    "spatial_consistency",
    "temporal_consistency",
    "response_causality",
    "closure_integrity",
    "canon_integrity",
    "language_naturalness",
    "age_suitability",
    "spine_fidelity",
    "narrative_coherence",
]


def _body(prompt_tokens: int, completion_tokens: int, cost: float) -> dict:
    return {
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
        }
    }


def _request() -> dict:
    return {
        "temperature": 0.0,
        "max_tokens": 3500,
        "reasoning": None,
        "response_format": None,
    }


def _clean_evaluations() -> list[dict]:
    return [
        {
            "family": family,
            "present": False,
            "severity": None,
            "repair_scope": None,
            "span_ids": [],
            "exact_text": None,
            "reason": "No concrete defect in this family.",
        }
        for family in FAMILY_ORDER
    ]


def test_stage5_v2_dual_audit_uses_same_frozen_writer_artifact_and_emits_one_artifact():
    seen = []

    def primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("primary", payload["source_artifact"]))
        assert "spine_context_pack" not in payload
        assert "reader_profile" not in payload
        assert payload["audit_authority_projection_sha256"]
        segment = next(
            row
            for row in payload["story_segments"]
            if "arriving at his shoulder" in row["text"]
        )
        evaluations = _clean_evaluations()
        evaluations[FAMILY_ORDER.index("language_naturalness")] = {
            "family": "language_naturalness",
            "present": True,
            "severity": "minor",
            "repair_scope": "LOCAL_REPAIR",
            "span_ids": [segment["id"]],
            "exact_text": "arriving at his shoulder",
            "reason": "The phrase is understandable but idiomatically unnatural English.",
        }
        raw = {
            "evaluations": evaluations,
            "summary": "One local language issue.",
        }
        return raw, _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("secondary", payload["source_artifact"]))
        raw = {
            "evaluations": _clean_evaluations(),
            "summary": "No additional defect.",
        }
        return raw, _body(90, 10, 0.02), _request(), []

    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )

    assert result["status"] == "audit_completed"
    assert result["audit_contract_revision"] == "family-by-family-multi-finding-v3"
    assert result["models"]["primary"] == PRIMARY_MODEL
    assert result["models"]["secondary"] == SECONDARY_MODEL
    assert result["input_verified_before_inference"] is True
    assert result["input_verified_after_inference"] is True
    assert result["source_story_mutated"] is False
    assert result["audit_authority_projection_sha256"]
    assert result["audit_authority_projection_bytes"] > 0
    assert len(seen) == 2
    assert seen[0][1] == seen[1][1]
    assert seen[0][1]["story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )

    artifact = result["audit_artifact"]
    assert artifact["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert artifact["next_stage"] == "STORY_LOCAL_REPAIR"
    assert artifact["source_artifact_id"] == result["source_artifact_id"]
    assert artifact["source_story_sha256"] == result["source_story_sha256"]
    assert len(artifact["findings"]) == 1
    assert artifact["findings"][0]["exact_text"] == "arriving at his shoulder"

    totals = result["audit_usage_rollup"]["totals"]
    assert totals["api_calls"] == 2
    assert totals["input_tokens"] == 190
    assert totals["output_tokens"] == 30
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False


def test_stage5_v2_requires_every_auditor_to_decide_every_family():
    secondary_called = False

    def primary(**kwargs):
        raw = {
            "evaluations": _clean_evaluations()[:-1],
            "summary": "Incomplete family coverage.",
        }
        return raw, _body(10, 5, 0.0), _request(), []

    def secondary(**kwargs):
        nonlocal secondary_called
        secondary_called = True
        raise AssertionError("Secondary must not run after invalid primary contract.")

    with pytest.raises(RuntimeError, match="every family exactly once"):
        execute_story_audit_once(
            api_key="not-used",
            primary_call_fn=primary,
            secondary_call_fn=secondary,
        )
    assert secondary_called is False


def test_stage5_v2_clean_dual_audit_routes_to_english_master_seal():
    def clean(**kwargs):
        return (
            {
                "evaluations": _clean_evaluations(),
                "summary": "Clean.",
            },
            _body(10, 5, 0.0),
            _request(),
            [],
        )

    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=clean,
        secondary_call_fn=clean,
    )
    artifact = result["audit_artifact"]
    assert artifact["decision"] == "ACCEPT"
    assert artifact["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert artifact["source_story_mutated"] is False
