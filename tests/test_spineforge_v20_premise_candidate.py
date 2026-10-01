from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1, fingerprint_value


PACK = Path("data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json")
MANIFEST = Path("data/specifications/story_lab/spineforge_v20_qualification_cases_v1.json")


def test_v20_island_context_pack_is_valid_and_fingerprint_is_canonical():
    raw = json.loads(PACK.read_text(encoding="utf-8"))
    pack = SpineContextPackV1.model_validate(raw)
    assert pack.context_fingerprint == fingerprint_value(
        {k: v for k, v in raw.items() if k != "context_fingerprint"}
    )
    assert pack.reader_profile["exact_age"] == 12
    assert pack.session_target["target_words_min"] == 1600
    assert pack.session_target["target_words_max"] == 2500


def test_v20_premise_is_story_first_and_rejects_procedural_bridge_pattern():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    premise = pack.approved_premise
    assert premise["key"] == "island_not_on_any_map"
    assert "repeated measuring" in " ".join(premise["constraints"]).lower()
    assert "uncharted_island_shore" in premise["location_refs"]
    assert "abandoned_expedition_site" in premise["location_refs"]
    assert "final Spine must commit to one path" in premise["meaningful_choice_pressure"]


def test_v20_manifest_points_only_to_candidate_fixture_and_writer_is_not_involved():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(data["cases"]) == 1
    case = data["cases"][0]
    assert case["context_fixture_status"] == "CANDIDATE"
    assert case["context_fixture_ref"] == str(PACK)
    assert case["obligations"]["exact_age"] == 12
    assert case["obligations"]["decision_required"] is True
    joined = " ".join(case["obligations"]["reject_signals"]).lower()
    assert "procedural verification" in joined
    assert "post-choice beats remain conditional" in joined
