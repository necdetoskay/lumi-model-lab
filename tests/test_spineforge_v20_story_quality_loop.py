from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spineforge_v20_story_quality_loop import (
    build_local_repair_handoff,
    build_reaudit_handoff,
    build_reaudit_product,
    execute_local_repair,
    execute_reaudit,
)


REAUDIT_RESULT = Path(
    "evidence/spineforge-v20-paid-story-reaudit-cycle2/37014477600/"
    "age12-island-v20-story-reaudit2-result.json"
)
REAUDIT_ENVELOPE = Path(
    "evidence/spineforge-v20-paid-story-reaudit-cycle2/37014477600/"
    "age12-island-v20-story-reaudit2-envelope.json"
)
STAGE8_STORY = Path(
    "evidence/spineforge-v20-story-local-repair-cycle2-product/37010331757/"
    "story-local-repair-cycle2-artifact.json"
)
GENERIC_PRODUCT = Path(
    "evidence/spineforge-v20-story-quality-loop/37014477600-reaudit-product.json"
)


FAMILIES = [
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


def _body(prompt=10, completion=5, cost=0.0):
    return {
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "cost": cost,
        }
    }


def _request(max_tokens=6000):
    return {
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "reasoning": None,
        "response_format": {"type": "json_schema"},
    }


def _clean_primary():
    return {
        "evaluations": [
            {
                "family": family,
                "present": False,
                "findings": [],
                "reason": "No concrete defect.",
            }
            for family in FAMILIES
        ],
        "summary": "Clean.",
    }


def _clean_secondary(payload):
    return {
        "language_sentence_scan": [
            {
                "span_id": str(row["id"]),
                "status": "clean",
                "editor_action": "KEEP",
                "rewrite": "",
            }
            for row in payload["story_segments"]
        ],
        "findings": [],
        "summary": "Naturalness clean.",
    }


def test_generic_loop_builds_stage9_product_and_stage10_repair_handoff_without_cycle_specific_code():
    product = build_reaudit_product(
        result_path=REAUDIT_RESULT,
        envelope_path=REAUDIT_ENVELOPE,
        source_story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )
    assert product["schema"] == "spineforge-v20-story-quality-reaudit-product.v1"
    assert product["artifact_id"] == (
        "story-quality-reaudit:4aabbacb8c8d3b99c1139b3908b30c6a52e9125a421819ca2af4b626880a6711"
    )
    assert product["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert product["finding_count"] == 12
    assert product["stable_span_count"] == 199

    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )
    assert handoff["schema"] == "spineforge-v20-story-quality-repair-handoff.v1"
    assert handoff["artifact_id"] == (
        "story-quality-repair-handoff:cd302abc071b27a831ecccd658afa58007c238de3a14795d76539cdbe58c122e"
    )
    assert handoff["stage"] == 10
    assert handoff["repair_cycle_index"] == 3
    assert handoff["paid_attempt_index"] == 4
    assert handoff["finding_count"] == 12
    assert handoff["allowed_edit_span_count"] == 13
    assert handoff["paid_execution_authorized"] is False


def test_generic_local_repair_then_build_reaudit_handoff_needs_no_new_cycle_module(tmp_path: Path):
    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        rows = []
        for target in payload["target_segments"]:
            rows.append({
                "span_id": target["span_id"],
                "replacement_text": target["source_text"] + " [fixed]",
                "addresses_finding_indexes": target["finding_indexes"],
            })
        return {"patches": rows, "summary": "Synthetic."}, _body(), _request(8000), []

    result = execute_local_repair(
        api_key="not-used",
        handoff=handoff,
        call_fn=fake_call,
        system_prompt="PATCHES ONLY",
    )
    assert result["status"] == "repair_generated"
    assert result["stage"] == 10
    assert result["repair_cycle_index"] == 3
    assert result["paid_attempt_index"] == 4
    assert result["patch_count"] == 13
    assert result["no_change_resolution_count"] == 0
    assert result["changed_span_ids"] == handoff["allowed_edit_span_ids"]
    assert result["next_stage"] == "STORY_REAUDIT"
    assert result["automatic_retry_executed"] is False
    assert result["reaudit_executed"] is False


def test_generic_reaudit_can_accept_any_frozen_generic_story_artifact_shape():
    # Stage 8 product is an allowed immutable repaired-story source and proves
    # the generic re-audit path does not depend on a cycle-specific module.
    handoff = build_reaudit_handoff(
        story_artifact_path=STAGE8_STORY,
        stage=9,
        cycle_index=2,
    )

    def primary(**kwargs):
        return _clean_primary(), _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    result = execute_reaudit(
        api_key="not-used",
        handoff=handoff,
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )
    assert result["status"] == "reaudit_completed"
    assert result["secondary_language_sentence_scan_count"] == 199
    assert result["reaudit_artifact"]["decision"] == "ACCEPT"
    assert result["reaudit_artifact"]["next_stage"] == "ENGLISH_MASTER_SEAL"
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False


def test_generic_repair_forbidden_span_is_rejected():
    handoff = build_local_repair_handoff(
        reaudit_product_path=GENERIC_PRODUCT,
        source_story_artifact_path=STAGE8_STORY,
        stage=10,
        repair_cycle_index=3,
        paid_attempt_index=4,
    )

    def fake_call(**kwargs):
        return {
            "patches": [{
                "span_id": "S006",
                "replacement_text": "Forbidden.",
                "addresses_finding_indexes": [0],
            }],
            "summary": "Bad.",
        }, _body(), _request(8000), []

    with pytest.raises(RuntimeError, match="forbidden span"):
        execute_local_repair(
            api_key="not-used",
            handoff=handoff,
            call_fn=fake_call,
            system_prompt="PATCHES ONLY",
        )
