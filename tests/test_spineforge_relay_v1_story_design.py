import json
from pathlib import Path
import pytest
from src.spineforge_story_design import StoryRequestV1, StoryDesignV1, record_design, validate_design, planner_input
from src.spineforge_relay_v1_contracts import canonical_sha256

FIXTURES=Path("tests/fixtures/story_design_v1")

def inputs():
    return (StoryRequestV1.model_validate_json((FIXTURES/"mosaic-request.json").read_bytes()),
            StoryDesignV1.model_validate_json((FIXTURES/"mosaic-adapter-proposal.json").read_bytes()))

def test_adapter_prepares_existing_chain_without_claiming_live_generation(tmp_path):
    proof=record_design(FIXTURES/"mosaic-request.json",FIXTURES/"mosaic-adapter-proposal.json",tmp_path/"run")
    assert proof["status"]=="STRUCTURAL_PASS"
    assert proof["semantic_status"]=="REQUIRES_REVIEW"
    assert proof["projected_final_revision"]==6
    assert proof["actual_state_advanced"] is False and proof["provider_calls"]==0
    manifest=json.loads((tmp_path/"run/manifest.json").read_text())
    assert manifest["paid_authority_created"] is False
    assert "proposal-input.json" in manifest["files"]
    with pytest.raises(FileExistsError):
        record_design(FIXTURES/"mosaic-request.json",FIXTURES/"mosaic-adapter-proposal.json",tmp_path/"run")

@pytest.mark.parametrize("defect",["stale","missing","unknown","duplicate","language","age","tone","count","questions","exclusions","thread","stale_state"])
def test_design_failures_are_recorded_without_producing_authority(tmp_path,defect):
    request,design=inputs()
    if defect=="stale":design.request_sha256="0"*64
    elif defect=="missing":design.request_bindings.pop()
    elif defect=="unknown":design.request_bindings[0].predicate_id="missing"
    elif defect=="duplicate":design.request_bindings.append(design.request_bindings[0])
    elif defect in ("language","age","tone"):
        design.fixture["story_intent"][{"age":"reader_age"}.get(defect,defect)]={"language":"tr","age":8,"tone":["comic"]}[defect]
    elif defect=="count":request.scene_count=5;design.request_sha256=canonical_sha256(request)
    elif defect=="questions":design.unresolved_questions=["Unresolved ending"]
    elif defect=="exclusions":request.forbidden=["No violence"];design.request_sha256=canonical_sha256(request)
    elif defect=="thread":design.fixture["initial_state"]["open_threads"].append("unresolved")
    else:design.fixture["scene_plans"][1]["entry_state"]["/characters/Aya/location"]="invented"
    rp=tmp_path/"r.json";dp=tmp_path/"d.json"
    rp.write_text(request.model_dump_json(),encoding="utf8");dp.write_text(design.model_dump_json(),encoding="utf8")
    proof=record_design(rp,dp,tmp_path/"record")
    assert proof["status"]=="REJECTED_DESIGN"
    assert proof["provider_calls"]==0 and proof["actual_state_advanced"] is False
    assert (tmp_path/"record/request-input.json").read_bytes()==rp.read_bytes()
    assert (tmp_path/"record/proposal-input.json").read_bytes()==dp.read_bytes()


def test_request_does_not_accept_invented_user_quotes():
    request,_=inputs()
    raw=request.model_dump(mode="json")
    raw["requirements"][0]["source_text"]="The user never asked this"
    with pytest.raises(ValueError,match="exact user-request text"):
        StoryRequestV1.model_validate(raw)


def test_request_and_nested_schema_are_in_planner_input():
    request,_=inputs();payload=planner_input(request)
    assert payload["request_sha256"]==canonical_sha256(request)
    assert "RequiredEventSpecV1" in payload["fixture_schema"]["$defs"]
    assert set(payload["sources"])=={"src/spineforge_story_design.py","prompts/spineforge_story_design.md"}


def test_existing_fixture_cannot_be_swapped_after_design(tmp_path):
    request,design=inputs()
    path=tmp_path/"fixture.json";path.write_text("{}")
    with pytest.raises(ValueError,match="differs from recorded design"):
        validate_design(request,design,path)
