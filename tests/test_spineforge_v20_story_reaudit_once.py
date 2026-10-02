from __future__ import annotations

import json

from src.spineforge_v20_story_reaudit_once import execute_story_reaudit_once


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


def _body(prompt: int, completion: int, cost: float):
    return {
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "cost": cost,
        }
    }


def _request():
    return {
        "temperature": 0.0,
        "max_tokens": 6000,
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
        "summary": "Full repaired story clean.",
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


def test_stage7_reaudit_reads_frozen_stage6_artifact_and_accepts_clean_full_reaudit():
    seen = []

    def primary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("primary", payload))
        return _clean_primary(), _body(100, 20, 0.01), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        seen.append(("secondary", payload))
        return _clean_secondary(payload), _body(90, 10, 0.02), _request(), []

    result = execute_story_reaudit_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )

    assert result["status"] == "reaudit_completed"
    assert result["source_stage6_artifact_id"] == (
        "story-local-repair:eca2fd757acea1bc5bf982ea3ded100a62fdae68687d0652d61ff729795614f1"
    )
    assert result["source_repaired_story_sha256"] == (
        "a3298380efdb74b3d7ddd30d84d9b959bece6f7ee9f0b45d83bdf62c5639a1d4"
    )
    assert result["secondary_language_sentence_scan_count"] == 199
    assert result["source_story_mutated"] is False
    assert result["automatic_retry_executed"] is False
    assert result["repair_executed"] is False
    assert result["translation_executed"] is False
    assert result["state_commit_executed"] is False

    primary_payload = seen[0][1]
    secondary_payload = seen[1][1]
    assert primary_payload["source_artifact"]["artifact_id"].startswith(
        "story-local-repair:"
    )
    assert secondary_payload["source_artifact"] == primary_payload["source_artifact"]
    assert len(primary_payload["story_segments"]) == 199
    assert len(secondary_payload["story_segments"]) == 199
    s006 = next(x for x in primary_payload["story_segments"] if x["id"] == "S006")
    assert s006["text"] == '"I saw it first," Nisa said, stepping up beside him.'
    assert primary_payload["stage6_lineage"]["no_change_span_ids"] == ["S161"]

    artifact = result["reaudit_artifact"]
    assert artifact["schema"] == "spineforge-v20-story-reaudit-artifact.v1"
    assert artifact["stage"] == 7
    assert artifact["full_story_reaudited"] is True
    assert artifact["stable_span_count"] == 199
    assert artifact["decision"] == "ACCEPT"
    assert artifact["next_stage"] == "ENGLISH_MASTER_SEAL"

    totals = result["reaudit_usage_rollup"]["totals"]
    assert totals["api_calls"] == 2
    assert totals["input_tokens"] == 190
    assert totals["output_tokens"] == 30
    assert totals["cost_usd"] == 0.03


def test_stage7_language_finding_routes_back_to_bounded_story_local_repair():
    def primary(**kwargs):
        return _clean_primary(), _body(10, 5, 0.0), _request(), []

    def secondary(**kwargs):
        payload = json.loads(kwargs["user_prompt"])
        rows = _clean_secondary(payload)
        target = next(row for row in payload["story_segments"] if row["id"] == "S161")
        rows["language_sentence_scan"][160] = {
            "span_id": "S161",
            "status": "defect",
            "editor_action": "REWRITE",
            "rewrite": target["text"] + " Clarified.",
        }
        rows["findings"] = [{
            "severity": "minor",
            "span_ids": ["S161"],
            "exact_text": "great root span",
            "reason": "Synthetic re-audit finding.",
        }]
        return rows, _body(10, 5, 0.0), _request(), []

    result = execute_story_reaudit_once(
        api_key="not-used",
        primary_call_fn=primary,
        secondary_call_fn=secondary,
    )
    artifact = result["reaudit_artifact"]
    assert artifact["decision"] == "LOCAL_REPAIR_REQUIRED"
    assert artifact["next_stage"] == "STORY_LOCAL_REPAIR"
    assert artifact["findings"][0]["span_ids"] == ["S161"]
