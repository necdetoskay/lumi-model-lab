from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import (
    MockCanonicalStateV1,
    build_spine_context_pack,
    fingerprint_value,
    write_spine_context_pack,
)

SOURCE=Path("data/specifications/story_lab/age18_forbidden_cartographer_mock_canonical_state_v1.json")


def test_mock_canonical_state_builds_reveal_safe_context_pack(tmp_path:Path) -> None:
    source=MockCanonicalStateV1.model_validate_json(SOURCE.read_text())
    pack=build_spine_context_pack(source)
    assert pack.schema_id=="spine-context-pack.v1"
    assert pack.built_from=="MOCK_CANONICAL_STATE"
    assert pack.character["name"]=="Leyra"
    assert pack.reader_profile["exact_age"]==18
    assert pack.session_target["target_words_min"]==1600
    assert pack.session_target["target_words_max"]==2500
    assert {x.key for x in pack.inventory}=={
        "ward_compass","survey_kit","eastern_maps","field_log"
    }
    assert {x.key for x in pack.opportunities}=={
        "ashen_gate_resurvey_opportunity","independent_map_seal_path"
    }


def test_pack_contains_revision_lineage_and_stable_fingerprint() -> None:
    source=MockCanonicalStateV1.model_validate_json(SOURCE.read_text())
    a=build_spine_context_pack(source)
    b=build_spine_context_pack(source)
    assert a.context_fingerprint==b.context_fingerprint
    assert len(a.context_fingerprint)==64
    types={x.entity_type for x in a.authority_revisions}
    assert "WORLD" in types
    assert "CHARACTER_STORY_STATE" in types
    assert "SAGA" in types
    assert "PREMISE" in types


def test_hidden_truth_answers_do_not_leak_into_context_pack() -> None:
    source=MockCanonicalStateV1.model_validate_json(SOURCE.read_text())
    pack=build_spine_context_pack(source)
    text=json.dumps(pack.model_dump(mode="json",by_alias=True),ensure_ascii=False)
    saga=json.loads(Path(source.saga_path).read_text())
    hidden=[
        x.get("hidden_statement")
        for x in saga["main_saga"]["hidden_truths"]
        if x.get("hidden_statement")
    ]
    assert hidden
    for secret in hidden:
        assert secret not in text
    assert pack.knowledge_boundaries["reveal_policy"]["hidden_truth_answers_included"] is False


def test_location_permissions_remain_distinct() -> None:
    source=MockCanonicalStateV1.model_validate_json(SOURCE.read_text())
    pack=build_spine_context_pack(source)
    full={x["key"] for x in pack.knowledge_boundaries["accessible_locations"]}
    rumored={x["key"] for x in pack.knowledge_boundaries["rumored_locations"]}
    locked={x["key"] for x in pack.knowledge_boundaries["locked_or_limited_locations"]}
    assert {"vellum_hall","greyfen","ashen_gate"}<=full
    assert "nameless_vale" in rumored
    assert "archive_of_cinders" in locked


def test_context_fingerprint_changes_when_canonical_state_changes() -> None:
    source=MockCanonicalStateV1.model_validate_json(SOURCE.read_text())
    a=build_spine_context_pack(source)
    raw=source.model_dump(mode="json",by_alias=True)
    raw["current_situation_notes"].append("A new canonical pressure exists.")
    changed=MockCanonicalStateV1.model_validate(raw)
    b=build_spine_context_pack(changed)
    assert a.context_fingerprint!=b.context_fingerprint


def test_pack_file_round_trip(tmp_path:Path) -> None:
    out=tmp_path/"pack.json"
    pack=write_spine_context_pack(source_path=SOURCE,out_path=out)
    stored=json.loads(out.read_text())
    copy=dict(stored)
    fingerprint=copy.pop("context_fingerprint")
    assert fingerprint==fingerprint_value(copy)
    assert pack.context_fingerprint==fingerprint
