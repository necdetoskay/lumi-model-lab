from __future__ import annotations

import json
from pathlib import Path

from src.saga_blueprint_contract import NarrativeFixture

MATRIX=Path("data/specifications/story_lab/age18_lane_stabilization_matrix_v1.json")
FIXTURE=Path("data/specifications/saga_lab/age18_orbital_legacy_link_fixture_v1.json")
CONTRACT=Path("data/specifications/story_lab/age18_a2_orbital_case_contract_v1.json")


def test_stabilization_matrix_requires_three_independent_cases() -> None:
    m=json.loads(MATRIX.read_text())
    assert m["lane_status"]=="SINGLE_CASE_QUALIFIED"
    assert m["required_additional_cases"]==3
    assert m["paid_boundary"]["authorized"] is False
    cases={x["case_id"]:x for x in m["cases"]}
    assert cases["AGE18-A1-BEACON-RIDGE"]["status"]=="PUBLICATION_READY_CONTROL"
    assert cases["AGE18-A2-ORBITAL-LEGACY-LINK"]["formal_record_mechanics"] is False


def test_orbital_fixture_is_exact_age18_and_schema_valid() -> None:
    f=NarrativeFixture.model_validate_json(FIXTURE.read_text())
    assert f.character.age==18
    assert f.audience_band=="YOUNG_ADULT"
    assert f.story_mode=="DISCOVERY"
    assert f.world.world_type=="SCIENCE_FICTION"


def test_a2_contract_forbids_beacon_ridge_overfit() -> None:
    c=json.loads(CONTRACT.read_text())
    assert c["exact_age"]==18
    assert c["controlled_intent"]["formal_record_mechanics_forbidden_as_core_choice"] is True
    assert "no five-reading tide series" in c["controlled_intent"]["required_difference_from_control"]
    assert c["paid_boundary"]["authorized"] is False
    assert c["paid_boundary"]["writer_authorized"] is False
