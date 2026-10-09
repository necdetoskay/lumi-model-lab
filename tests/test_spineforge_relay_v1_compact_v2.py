import json
from pathlib import Path
import pytest
from src.spineforge_production_compact import CompactStoryPlanV1, compile_compact
from src.spineforge_production_compact_v2 import CompactStoryPlanV2, compile_compact_v2
from src.spineforge_seeded_design import verify_frozen_seed, validate_seeded_design
from src.spineforge_story_design import StoryRequestV1
from tests.spineforge_compact_controls import upgrade_plan_control, compact_control_v2
from tests.test_spineforge_relay_v1_production_pipeline import sample

Q15 = Path("evidence/spineforge-relay/SFR-V1-Q15-COMPACT-ROBOT-20261009")


@pytest.mark.parametrize("attempt", [1,2])
def test_q15_protocol_failures_are_removed_offline_without_changing_recorded_run(tmp_path,attempt):
    request=StoryRequestV1.model_validate_json((Q15/"request-input.json").read_bytes())
    seed=verify_frozen_seed(Q15/"seed-input.json",Q15/"frozen-seed.json")
    blob=(Q15/f"plan-{attempt}-compact.json").read_bytes()
    legacy=CompactStoryPlanV1.model_validate_json(blob)
    with pytest.raises(ValueError): compile_compact(request,seed,legacy)
    design=compile_compact_v2(request,seed,upgrade_plan_control(legacy))
    path=tmp_path/"fixture.json";path.write_text(json.dumps(design.fixture),encoding="utf8")
    proof=validate_seeded_design(request,seed,design,path)
    assert proof["status"]=="STRUCTURAL_PASS" and proof["semantic_status"]=="REQUIRES_REVIEW"
    assert (Q15/f"plan-{attempt}-compact.json").read_bytes()==blob
    assert json.loads((Q15/"result.json").read_text())["status"]=="REJECT_NON_CONVERGENT"
    predicates={(p["scene_id"],e["id"],q["id"]):q for p in design.fixture["scene_plans"] for e in p["required_events"] for q in e["predicates"]}
    for spatial in design.fixture["spatial_plans"]:
        for op in spatial["operations"]:
            p=predicates[spatial["scene_id"],op["event_id"],op["predicate_id"]]
            assert (p["subject"],p["action"],p["target"])==(op["subject"],op["kind"],op["target"])
    assert any(p["action"]=="CARRIES_TO_EXHIBITION_HALL" and p["subject"]=="Bora" for p in predicates.values())


def setup(tmp_path):
    paths,design=sample(tmp_path/"input","mosaic")
    request=StoryRequestV1.model_validate_json(paths["request"].read_bytes())
    seed=verify_frozen_seed(paths["seed"],paths["freeze"])
    return request,seed,compact_control_v2(design)


@pytest.mark.parametrize("defect", ["unknown_goal","duplicate_goal","uncovered_event","unknown_order","unknown_spatial_event","unknown_entity","knowledge_spatial","collision","ambiguous_predicate","invented_edge"])
def test_v2_derivation_rejects_unsupported_declarations(tmp_path,defect):
    request,seed,plan=setup(tmp_path)
    raw=plan.model_dump(mode="json");s=raw["scenes"][3];op=s["spatial_operations"][0]
    event=next(e for e in s["events"] if e["id"]==op["event_id"])
    if defect=="unknown_goal": s["goal_bindings"]["turn"]=["missing"]
    elif defect=="duplicate_goal": s["goal_bindings"]["turn"]*=2
    elif defect=="uncovered_event":
        extra=json.loads(json.dumps(event));extra["id"]="unbound";s["events"].append(extra)
    elif defect=="unknown_order": s["ordered_dependencies"]=[dict(before=dict(event_id="missing"),after=dict(event_id=event["id"]))]
    elif defect=="unknown_spatial_event": op["event_id"]="missing"
    elif defect=="unknown_entity": op["subject"]="invented"
    elif defect=="knowledge_spatial": event["evidence_mode"]="ESTABLISHED_KNOWLEDGE"
    elif defect=="invented_edge": op["edge_id"]="invented"
    elif defect=="ambiguous_predicate":
        match=next(p for p in event["predicates"] if p["action"]==op["kind"])
        extra={**match,"id":"another"};event["predicates"].append(extra)
    else:
        match=next(p for p in event["predicates"] if p["action"]==op["kind"])
        match["action"]="NARRATIVE_MOVE"
        event["predicates"].append(dict(id="SP_"+op["id"],subject="Aya",action="OBSERVE",target="panel"))
    with pytest.raises((ValueError,RuntimeError)):
        compile_compact_v2(request,seed,CompactStoryPlanV2.model_validate(raw))


def test_narrative_movement_words_never_infer_a_spatial_operation(tmp_path):
    paths,design=sample(tmp_path/"input","dialogue")
    request=StoryRequestV1.model_validate_json(paths["request"].read_bytes())
    seed=verify_frozen_seed(paths["seed"],paths["freeze"])
    plan=compact_control_v2(design)
    plan.scenes[0].events[0].predicates[0].action="MOVES_TO"
    plan.scenes[0].events[0].predicates[0].target="outside"
    expanded=compile_compact_v2(request,seed,plan)
    assert expanded.fixture["spatial_plans"][0]["operations"]==[]
    assert expanded.fixture["spatial_plans"][0]["expected_exit"]["positions"]=={"Reader":"reading_room"}
