from __future__ import annotations

import json

import pytest

from src.spineforge_v20_story_local_repair_cycle2_handoff import (
    build_story_local_repair_cycle2_handoff,
)
from src.spineforge_v20_story_local_repair_cycle2_once import (
    execute_story_local_repair_cycle2_once,
)


def _body():
    return {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "cost": 0.01,
        }
    }


def _request():
    return {
        "temperature": 0.0,
        "max_tokens": 8000,
        "reasoning": None,
        "response_format": {"type": "json_schema"},
    }


def test_stage8_handoff_uses_stage7_product_and_repaired_story_offsets():
    handoff = build_story_local_repair_cycle2_handoff()
    assert handoff["schema"] == "spineforge-v20-story-local-repair-cycle2-handoff.v1"
    assert handoff["artifact_type"] == "IMMUTABLE_STAGE8_LOCAL_REPAIR_INPUT"
    assert handoff["stage"] == 8
    assert handoff["status"] == "READY_NOT_AUTHORIZED"
    assert handoff["immutable"] is True
    assert handoff["artifact_id"] == (
        "story-local-repair-cycle2-handoff:ccbb5ef3fbed5b5babb5a1ec07f57daa04d62b83eed68d0864b65258d87a1804"
    )
    assert handoff["source_stage7_product_artifact_id"] == (
        "story-reaudit-product:7ec8360d92ab8a77431e78a039340b56277cc2ec7ac2ea301fe847f059655abe"
    )
    assert handoff["source_story_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert handoff["finding_count"] == 16
    assert handoff["allowed_edit_span_count"] == 16
    assert handoff["repair_cycle_index"] == 2
    assert handoff["paid_attempt_index"] == 3
    assert handoff["paid_execution_authorized"] is False
    assert "S006" not in handoff["allowed_edit_span_ids"]
    assert "S161" in handoff["allowed_edit_span_ids"]


def test_stage8_fake_repair_changes_only_stage7_allowed_spans():
    handoff = build_story_local_repair_cycle2_handoff()

    def fake_call(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        rows = []
        for target in payload["target_segments"]:
            rows.append({
                "span_id": target["span_id"],
                "replacement_text": target["source_text"] + " [fixed]",
                "addresses_finding_indexes": target["finding_indexes"],
            })
        return {"patches": rows, "summary": "Synthetic."}, _body(), _request(), []

    result = execute_story_local_repair_cycle2_once(
        api_key="not-used",
        handoff=handoff,
        call_fn=fake_call,
        system_prompt="PATCHES ONLY",
    )
    assert result["status"] == "repair_generated"
    assert result["stage"] == 8
    assert result["patch_count"] == 16
    assert result["no_change_resolution_count"] == 0
    assert result["changed_span_ids"] == handoff["allowed_edit_span_ids"]
    assert result["changed_spans_subset_of_allowed"] is True
    assert result["all_findings_addressed"] is True
    assert result["source_story_mutated"] is False
    assert result["automatic_retry_executed"] is False
    assert result["reaudit_executed"] is False
    assert result["next_stage"] == "STORY_REAUDIT"
    assert result["repair_usage_rollup"]["totals"]["api_calls"] == 1


def test_stage8_forbidden_span_is_rejected():
    handoff = build_story_local_repair_cycle2_handoff()

    def fake_call(**kwargs):
        return {
            "patches": [{
                "span_id": "S006",
                "replacement_text": "Forbidden change.",
                "addresses_finding_indexes": [0],
            }],
            "summary": "Bad.",
        }, _body(), _request(), []

    with pytest.raises(RuntimeError, match="forbidden span"):
        execute_story_local_repair_cycle2_once(
            api_key="not-used",
            handoff=handoff,
            call_fn=fake_call,
            system_prompt="PATCHES ONLY",
        )
