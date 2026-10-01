from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v20_local_repair import validate_repair_diff
from src.spineforge_v20_obligations import load_qualification_cases


SOURCE = Path("evidence/spineforge-v20-repair/36908095596-source.json")
SPEC = Path("evidence/spineforge-v20-repair/36908095596-repair-spec.json")


def _source() -> NarrativeSpineV1:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    return NarrativeSpineV1.model_validate(data["narrative_spine"])


def test_repair_spec_is_bound_to_exact_source_and_local_finding():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["source_run_id"] == 36908095596
    assert spec["source_context_fingerprint"] == source["context_fingerprint"]
    assert spec["source_spine_hash"] == source["spine_hash"]
    assert spec["source_gate_decision"] == "REPAIR"
    assert spec["finding"]["repairability"] == "LOCAL"
    assert spec["paid_state"] == "NOT_AUTHORIZED"


def test_gate_target_path_normalization_accounts_for_actual_external_change_field():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert "beats[2].character_action" in spec["finding"]["target_path"]
    assert "narrative_spine.beats[2].external_change" in spec["allowed_change_paths"]
    assert "actually in beats[2].external_change" in spec["normalized_problem"]["note"]


def test_diff_guard_accepts_minimal_route_line_fix():
    source = _source()
    raw = source.model_dump(mode="json", by_alias=True)
    repaired_raw = deepcopy(raw)
    repaired_raw["beats"][2]["external_change"] = (
        "The glider catches a root and tilts, but holds. Arda uses the route line "
        "to steady the glider, then unfastens it, coils it, and carries it inland."
    )
    repaired = NarrativeSpineV1.model_validate(repaired_raw)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    changed = validate_repair_diff(
        source=source,
        repaired=repaired,
        allowed_change_paths=spec["allowed_change_paths"],
    )
    assert changed == ["narrative_spine.beats[2].external_change"]


def test_diff_guard_rejects_story_replan_hidden_inside_local_repair():
    source = _source()
    raw = source.model_dump(mode="json", by_alias=True)
    repaired_raw = deepcopy(raw)
    repaired_raw["central_question"] = "A completely different story question"
    repaired = NarrativeSpineV1.model_validate(repaired_raw)
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="forbidden paths"):
        validate_repair_diff(
            source=source,
            repaired=repaired,
            allowed_change_paths=spec["allowed_change_paths"],
        )


def test_source_still_valid_against_frozen_context_and_obligations():
    pack = SpineContextPackV1.model_validate_json(
        Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json").read_text(encoding="utf-8")
    )
    case = load_qualification_cases().cases[0]
    assert pack.context_fingerprint == json.loads(SPEC.read_text())["source_context_fingerprint"]
    assert case.obligations.exact_age == 12


def test_regate_transport_failure_preserves_repaired_spine_and_repair_usage():
    from src.spineforge_v20_local_repair import run_local_repair

    source = _source()
    source_raw = source.model_dump(mode="json", by_alias=True)
    repaired_raw = deepcopy(source_raw)
    repaired_raw["beats"][2]["external_change"] = (
        "The glider catches a root and tilts, but holds. Arda uses the route line "
        "to steady the glider, then unfastens it, coils it, and carries it inland."
    )

    pack = SpineContextPackV1.model_validate_json(
        Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json").read_text(encoding="utf-8")
    )
    case = load_qualification_cases().cases[0]
    spec = json.loads(SPEC.read_text(encoding="utf-8"))

    def fake_repair(**kwargs):
        return (
            repaired_raw,
            {"usage": {"prompt_tokens": 10, "completion_tokens": 5}},
            {"response_format": {"type": "json_object"}},
            [],
        )

    def gate_boom(**kwargs):
        raise RuntimeError("synthetic gate transport failure")

    result = run_local_repair(
        source_spine=source,
        context_pack=pack,
        obligations=case.obligations,
        repair_spec=spec,
        api_key="not-used",
        repair_call_fn=fake_repair,
        gate_call_fn=gate_boom,
    )
    assert result["status"] == "repair_regate_transport_failed"
    assert result["repaired_spine"]["beats"][2]["external_change"].endswith("carries it inland.")
    assert result["changed_paths"] == ["narrative_spine.beats[2].external_change"]
    assert result["writer_authorized"] is False
    assert result["pipeline_usage_rollup"]["totals"]["api_calls"] == 1
