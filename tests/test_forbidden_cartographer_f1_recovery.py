from __future__ import annotations

import json
from pathlib import Path

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.forbidden_cartographer_f1_gate_recovery import _validate
from src.forbidden_cartographer_f1_safe_normalize import normalize_missing_final_return_location

SOURCE=Path("data/specifications/story_lab/age18_forbidden_cartographer_f1_recovery_source_36656865491.json")


def test_safe_normalizer_only_adds_omitted_return_location() -> None:
    source=json.loads(SOURCE.read_text())
    raw=source["architect_raw_payload"]
    normalized,repairs=normalize_missing_final_return_location(raw)
    assert len(repairs)==1
    assert raw["logistics_plan"]["location_sequence"]==["vellum_hall","greyfen","ashen_gate"]
    assert normalized["logistics_plan"]["location_sequence"]==[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    clone=json.loads(json.dumps(raw))
    clone["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    assert normalized==clone


def test_normalized_spine_is_strictly_valid_and_keeps_human_gate() -> None:
    source=json.loads(SOURCE.read_text())
    normalized,repairs=normalize_missing_final_return_location(source["architect_raw_payload"])
    spine=_validate(source,normalized)
    EpisodeSpineV2.model_validate(spine.model_dump(mode="json",by_alias=True))
    assert spine.exact_age==18
    assert spine.target_words_min==1600
    assert spine.target_words_max==2500
    assert spine.saga_progression.intended_milestone_keys==["forbidden_passage_observed"]


def test_normalizer_rejects_new_unseen_final_location() -> None:
    source=json.loads(SOURCE.read_text())
    raw=json.loads(json.dumps(source["architect_raw_payload"]))
    raw["beats"][-1]["location_ref"]="nameless_vale"
    normalized,repairs=normalize_missing_final_return_location(raw)
    assert repairs==[]
    assert normalized==raw
