import json
from pathlib import Path
import pytest
from src.spineforge_production_compact_v2 import CompactStoryPlanV2,compile_compact_v2
from src.spineforge_production_compact_v3 import CompactStoryPlanV3,CompactEventV3,compile_compact_v3
from src.spineforge_seeded_design import verify_frozen_seed,validate_seeded_design
from src.spineforge_story_design import StoryRequestV1
from tests.spineforge_compact_controls import upgrade_v2_control,compact_control_v3
from tests.test_spineforge_relay_v1_production_pipeline import sample

Q16=Path("evidence/spineforge-relay/SFR-V1-Q16-COMPACT-V2-ROBOT-20261009")


@pytest.mark.parametrize("attempt",[1,2])
def test_q16_derived_requirements_pass_offline_without_changing_paid_rejection(tmp_path,attempt):
    request=StoryRequestV1.model_validate_json((Q16/"request-input.json").read_bytes())
    seed=verify_frozen_seed(Q16/"seed-input.json",Q16/"frozen-seed.json")
    blob=(Q16/f"plan-{attempt}-compact.json").read_bytes()
    old=CompactStoryPlanV2.model_validate_json(blob)
    with pytest.raises(ValueError): compile_compact_v2(request,seed,old)
    migrated=upgrade_v2_control(old);design=compile_compact_v3(request,seed,migrated)
    path=tmp_path/"fixture.json";path.write_text(json.dumps(design.fixture),encoding="utf8")
    proof=validate_seeded_design(request,seed,design,path)
    assert proof["status"]=="STRUCTURAL_PASS" and proof["semantic_status"]=="REQUIRES_REVIEW"
    assert (Q16/f"plan-{attempt}-compact.json").read_bytes()==blob
    assert json.loads((Q16/"result.json").read_text())["status"]=="REJECT_NON_CONVERGENT"
    for s in design.fixture["scene_plans"]:
        for e in s["required_events"]:
            if e["required_observer"]:
                assert any(p["subject"]==e["required_observer"] and p["action"] in {"OBSERVE","ACKNOWLEDGE"} for p in e["predicates"])
            if e["separate_physical_clue_required"]:
                assert any(p["action"]=="SHOW_PHYSICAL_CLUE" for p in e["predicates"])


def setup(tmp_path):
    paths,design=sample(tmp_path/"inputs","dialogue")
    return StoryRequestV1.model_validate_json(paths["request"].read_bytes()),verify_frozen_seed(paths["seed"],paths["freeze"]),compact_control_v3(design)


@pytest.mark.parametrize("defect",["observer","observer_collision","clue_actor","clue_collision","clue_knowledge","old_flag"])
def test_invalid_declarations_fail_closed(tmp_path,defect):
    request,seed,plan=setup(tmp_path);raw=plan.model_dump(mode="json");event=raw["scenes"][0]["events"][0]
    if defect=="observer": event["required_observer"]="Invented"
    elif defect=="observer_collision":
        event["required_observer"]="Reader";event["predicates"].append(dict(id="OBSERVER",subject="Reader",action="NOTICE",target="unrelated"))
    elif defect=="old_flag": event["separate_physical_clue_required"]=True
    else:
        event["physical_clue"]={"subject":"Invented" if defect=="clue_actor" else "Reader","target":"question"}
        if defect=="clue_collision": event["predicates"].append(dict(id="PHYSICAL_CLUE",subject="Reader",action="NOTICE",target="unrelated"))
        if defect=="clue_knowledge": event["evidence_mode"]="ESTABLISHED_KNOWLEDGE"
    with pytest.raises((ValueError,RuntimeError)):
        compile_compact_v3(request,seed,CompactStoryPlanV3.model_validate(raw))


def test_visible_fact_does_not_invent_a_separate_clue(tmp_path):
    request,seed,plan=setup(tmp_path)
    design=compile_compact_v3(request,seed,plan)
    assert "separate_physical_clue_required" not in CompactEventV3.model_fields
    for s in design.fixture["scene_plans"]:
        for e in s["required_events"]:
            assert e["separate_physical_clue_required"] is False
            assert not any(p["action"]=="SHOW_PHYSICAL_CLUE" for p in e["predicates"])
