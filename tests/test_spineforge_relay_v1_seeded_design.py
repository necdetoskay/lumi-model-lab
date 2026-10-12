import json
from pathlib import Path
import pytest
from src.spineforge_seeded_design import (StorySeedV1,SeededStoryDesignV2,freeze_seed,verify_frozen_seed,
    seeded_planner_input,validate_seeded_design,record_seeded_design,compare_story_states)
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_relay_v1_contracts import canonical_sha256

ROOT=Path("tests/fixtures/story_scenarios_v1")
MOSAIC=Path("tests/fixtures/spineforge_relay_v1/q12_span_mosaic_chain.json")
RECORDS=Path("evidence/spineforge-relay/SFR-V1-Q12-SOURCE-SPAN-MOSAIC-20261008")

def mosaic_seed():
    f=json.loads(MOSAIC.read_text())
    return StorySeedV1(story_id=f["story_id"],scenario_id="adapter",characters=f["initial_state"]["characters"],
        relevant_character_canon=f["relevant_character_canon"],world=f["initial_state"]["world"],
        objects=f["initial_state"]["objects"],topology=f["topology"],prop_authorization_policy=f["prop_authorization_policy"],
        open_threads=f["initial_state"]["open_threads"],narrative_obligations=f["initial_state"]["narrative_obligations"])


def test_catalog_preserves_ten_candidates_and_selected_robot():
    data=json.loads((ROOT/"catalog.json").read_text(encoding="utf8"))
    assert len(data["scenarios"])==10 and len({r["id"] for r in data["scenarios"]})==10
    assert data["selected_scenario_id"]=="SCENARIO-03"
    assert data["scenarios"][2]["characters"]==["Ada","Bora"]
    request=StoryRequestV1.model_validate_json((ROOT/"broken-robot-request.json").read_bytes())
    assert request.original_prompt==data["scenarios"][2]["synopsis"]


def test_robot_seed_keeps_physical_truth_separate_from_initial_knowledge():
    seed=StorySeedV1.model_validate_json((ROOT/"broken-robot-seed.json").read_bytes())
    assert seed.objects["robot"].state["operational"] is False
    assert seed.objects["robot"].state["fault"]=="loose_motor_connector"
    assert seed.objects["robot"].state["fault_discovered"] is False
    assert all("loose_motor_connector" not in c.knowledge for c in seed.characters.values())
    assert seed.initial_state("S01")["revision"]==0
    assert "global_spine_sha256" not in seed.initial_state("S01")
    template=seed.initial_state("S01")
    template["world"]["time"]["minutes_until_opening"]=0
    template["open_threads"].clear()
    assert seed.world["time"]["minutes_until_opening"]==20 and seed.open_threads


def test_freeze_is_exclusive_and_rejects_source_replacement(tmp_path):
    seed=mosaic_seed();path=tmp_path/"seed.json";path.write_text(seed.model_dump_json())
    frozen=tmp_path/"frozen.json";freeze_seed(path,frozen)
    assert verify_frozen_seed(path,frozen)==seed
    with pytest.raises(FileExistsError):freeze_seed(path,frozen)
    path.write_text(seed.model_dump_json()+" ")
    with pytest.raises(ValueError,match="Frozen starting seed changed"):verify_frozen_seed(path,frozen)


def test_robot_prepare_records_frozen_seed_without_generation(tmp_path):
    seedpath=ROOT/"broken-robot-seed.json";freeze=tmp_path/"freeze.json";freeze_seed(seedpath,freeze)
    proof=record_seeded_design(ROOT/"broken-robot-request.json",seedpath,tmp_path/"run",freeze_path=freeze)
    assert proof["status"]=="READY_FOR_PLANNER" and proof["provider_calls"]==0
    payload=json.loads((tmp_path/"run/planner-input.json").read_text(encoding="utf8"))
    assert payload["seed_sha256"]==proof["seed_sha256"]
    assert payload["schema"]=="spineforge.planner-input.v2"
    assert (tmp_path/"run/frozen-seed.json").read_bytes()==freeze.read_bytes()


def test_changed_seed_is_recorded_as_rejection(tmp_path):
    seed=mosaic_seed();path=tmp_path/"seed.json";path.write_text(seed.model_dump_json())
    freeze=tmp_path/"freeze.json";freeze_seed(path,freeze)
    seed.characters["Aya"].knowledge.append("invented")
    path.write_text(seed.model_dump_json())
    result=record_seeded_design(Path("tests/fixtures/story_design_v1/mosaic-request.json"),path,tmp_path/"run",freeze_path=freeze)
    assert result["status"]=="REJECTED_DESIGN" and result["message"]=="Frozen starting seed changed"

@pytest.mark.parametrize("field",["initial_state","relevant_character_canon","topology","prop_authorization_policy","story_id","seed_hash"])
def test_planner_cannot_change_seed_fields(tmp_path,field):
    seed=mosaic_seed()
    raw=json.loads(Path("tests/fixtures/story_design_v1/mosaic-adapter-proposal.json").read_text())
    raw.update(schema_name="spineforge.story-design.v2",seed_sha256=canonical_sha256(seed))
    d=SeededStoryDesignV2.model_validate(raw)
    request=StoryRequestV1.model_validate_json(Path("tests/fixtures/story_design_v1/mosaic-request.json").read_bytes())
    if field=="seed_hash":d.seed_sha256="0"*64
    elif field=="story_id":d.fixture[field]="different"
    else:d.fixture[field]={}
    path=tmp_path/"fixture.json";path.write_text(json.dumps(d.fixture))
    with pytest.raises(ValueError,match="seed"):validate_seeded_design(request,seed,d,path)


def test_seeded_plan_can_use_existing_compiler_without_changing_start(tmp_path):
    seed=mosaic_seed()
    raw=json.loads(Path("tests/fixtures/story_design_v1/mosaic-adapter-proposal.json").read_text())
    raw.update(schema_name="spineforge.story-design.v2",seed_sha256=canonical_sha256(seed))
    request=StoryRequestV1.model_validate_json(Path("tests/fixtures/story_design_v1/mosaic-request.json").read_bytes())
    proof=validate_seeded_design(request,seed,SeededStoryDesignV2.model_validate(raw),MOSAIC)
    assert proof["seed_preserved"] is True and proof["actual_state_advanced"] is False


def test_compare_accepted_story_replays_before_reporting_changes(tmp_path):
    seed=mosaic_seed();path=tmp_path/"seed.json";path.write_text(seed.model_dump_json())
    freeze=tmp_path/"freeze.json";freeze_seed(path,freeze)
    proof=compare_story_states(path,freeze,MOSAIC,RECORDS)
    assert proof["initial_revision"]==0 and proof["final_revision"]==6
    assert any(r["path"]=="/objects/mosaic_panel/state/displayed" and r["before"] is False and r["after"] is True for r in proof["changes"])
    assert any(r["path"]=="/open_threads" and r["after"]==[] for r in proof["changes"])
    assert proof["offline_replay"]=="PASS"


def test_comparison_rejects_a_story_using_different_frozen_canon(tmp_path):
    seed=mosaic_seed();seed.relevant_character_canon["Aya"]["age"]=13
    path=tmp_path/"seed.json";path.write_text(seed.model_dump_json())
    freeze=tmp_path/"freeze.json";freeze_seed(path,freeze)
    with pytest.raises(ValueError,match="Story changed frozen seed field"):
        compare_story_states(path,freeze,MOSAIC,RECORDS)
