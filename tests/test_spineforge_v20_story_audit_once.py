from __future__ import annotations

import json

import pytest

from src.spineforge_v20_story_audit_once import (
    PRIMARY_MODEL,
    SECONDARY_AUDIT_SCHEMA_NAME,
    SECONDARY_MODEL,
    execute_story_audit_once,
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
        "max_tokens": 6000,
        "reasoning": None,
        "response_format": {"type": "json_schema"},
    }


def _clean_primary_evaluations() -> list[dict]:
    return [
        {
            "family": family,
            "present": False,
            "findings": [],
            "reason": "No concrete defect in this family.",
        }
        for family in FAMILY_ORDER
    ]


def _language_specialist_raw(
    payload: dict,
    *,
    defect_span_id: str | None = None,
    exact_text: str | None = None,
) -> dict:
    findings = []
    if defect_span_id is not None:
        findings.append(
            {
                "severity": "minor",
                "span_ids": [defect_span_id],
                "exact_text": exact_text,
                "reason": "Understandable but idiomatically unnatural English movement phrasing.",
            }
        )
    return {
        "language_sentence_scan": [
            {
                "span_id": str(row["id"]),
                "status": "defect" if str(row["id"]) == defect_span_id else "clean",
                "editor_action": (
                    "REWRITE" if str(row["id"]) == defect_span_id else "KEEP"
                ),
                "rewrite": (
                    "Nisa said, coming up beside him."
                    if str(row["id"]) == defect_span_id
                    else ""
                ),
            }
            for row in payload["story_segments"]
        ],
        "findings": findings,
        "summary": "Language-only sentence audit complete.",
    }


def test_stage5_language_specialist_uses_same_frozen_story_but_not_full_authority():
    seen = []

    def primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("primary", payload))
        raw = {
            "evaluations": _clean_primary_evaluations(),
            "summary": "Primary audit clean.",
        }
        return raw, _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("secondary", payload))
        segment = next(
            row
            for row in payload["story_segments"]
            if "arriving at his shoulder" in row["text"]
        )
        raw = _language_specialist_raw(
            payload,
            defect_span_id=segment["id"],
            exact_text="arriving at his shoulder",
        )
        return raw, _body(90, 10, 0.02), _request(), []

    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )

    assert result["status"] == "audit_completed"
    assert result["audit_contract_revision"] == "primary-v3-plus-language-specialist-v2"
    assert result["secondary_contract_revision"] == "language-specialist-v2"
    assert result["models"]["primary"] == PRIMARY_MODEL
    assert result["models"]["secondary"] == SECONDARY_MODEL
    assert result["source_story_mutated"] is False

    primary_payload = seen[0][1]
    secondary_payload = seen[1][1]
    assert primary_payload["source_artifact"] == secondary_payload["source_artifact"]
    assert primary_payload["source_artifact"]["story_sha256"] == (
        "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f"
    )
    assert "audit_authority_projection" in primary_payload
    assert "approved_narrative_spine" in primary_payload
    assert "audit_authority_projection" not in secondary_payload
    assert "approved_narrative_spine" not in secondary_payload
    assert secondary_payload["task"] == "contrastive_edit_frozen_story_english_naturalness"
    assert len(secondary_payload["story_segments"]) == 199

    artifact = result["audit_artifact"]
    assert artifact["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert artifact["next_stage"] == "STORY_LOCAL_REPAIR"
    assert len(artifact["findings"]) == 1
    assert artifact["findings"][0]["family"] == "language_naturalness"
    assert artifact["findings"][0]["repair_scope"] == "LOCAL_REPAIR"
    assert artifact["findings"][0]["span_ids"] == ["S006"]
    assert artifact["findings"][0]["exact_text"] == "arriving at his shoulder"

    assert result["secondary_language_sentence_scan_count"] == 199
    assert next(
        row
        for row in result["secondary_language_sentence_scan"]
        if row["span_id"] == "S006"
    )["status"] == "defect"

    totals = result["audit_usage_rollup"]["totals"]
    assert totals["api_calls"] == 2
    assert totals["input_tokens"] == 190
    assert totals["output_tokens"] == 30
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False


def test_stage5_primary_still_requires_all_thirteen_families_before_secondary_runs():
    secondary_called = False

    def primary(**kwargs):
        return (
            {
                "evaluations": _clean_primary_evaluations()[:-1],
                "summary": "Incomplete primary coverage.",
            },
            _body(10, 5, 0.0),
            _request(),
            [],
        )

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


def test_stage5_language_specialist_requires_199_exact_order_scan_and_matching_findings():
    def primary(**kwargs):
        return (
            {
                "evaluations": _clean_primary_evaluations(),
                "summary": "Primary clean.",
            },
            _body(10, 5, 0.0),
            _request(),
            [],
        )

    def incomplete_secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        raw = _language_specialist_raw(payload)
        raw["language_sentence_scan"] = raw["language_sentence_scan"][:-1]
        return raw, _body(10, 5, 0.0), _request(), []

    with pytest.raises(RuntimeError, match="every story sentence exactly once"):
        execute_story_audit_once(
            api_key="not-used",
            primary_call_fn=primary,
            secondary_call_fn=incomplete_secondary,
        )

    def mismatch_secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        raw = _language_specialist_raw(payload)
        raw["language_sentence_scan"][5]["status"] = "defect"
        raw["language_sentence_scan"][5]["editor_action"] = "REWRITE"
        raw["language_sentence_scan"][5]["rewrite"] = "Synthetic native-English rewrite."
        return raw, _body(10, 5, 0.0), _request(), []

    with pytest.raises(RuntimeError, match="must exactly match finding span ids"):
        execute_story_audit_once(
            api_key="not-used",
            primary_call_fn=primary,
            secondary_call_fn=mismatch_secondary,
        )


def test_stage5_clean_primary_and_clean_language_specialist_routes_to_english_master_seal():
    def primary(**kwargs):
        return (
            {
                "evaluations": _clean_primary_evaluations(),
                "summary": "Primary clean.",
            },
            _body(10, 5, 0.0),
            _request(),
            [],
        )

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        assert kwargs["schema_name"] == SECONDARY_AUDIT_SCHEMA_NAME
        return (
            _language_specialist_raw(payload),
            _body(10, 5, 0.0),
            _request(),
            [],
        )

    result = execute_story_audit_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )
    artifact = result["audit_artifact"]
    assert artifact["decision"] == "ACCEPT"
    assert artifact["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert artifact["source_story_mutated"] is False
