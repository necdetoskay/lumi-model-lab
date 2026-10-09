import json
import copy
from pathlib import Path
import pytest
from src.spineforge_production_plan_review_v2 import build_review_input,bind_review
from src.spineforge_production_pipeline import request_for
from src.spineforge_production_compact_v3 import CompactStoryPlanV3,compile_compact_v3
from src.spineforge_production_config import RunConfigV1
from src.spineforge_seeded_design import verify_frozen_seed
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_production_story import build_chain

ROOT=Path("evidence/spineforge-relay/SFR-V1-Q17-COMPACT-V3-ROBOT-20261009")

def context():
    request=StoryRequestV1.model_validate_json((ROOT/"request-input.json").read_bytes())
    seed=verify_frozen_seed(ROOT/"seed-input.json",ROOT/"frozen-seed.json")
    compact=CompactStoryPlanV3.model_validate_json((ROOT/"plan-1-compact.json").read_bytes())
    design=compile_compact_v3(request,seed,compact)
    rows=build_chain(ROOT/"plan-1-fixture.json")[4]
    payload=build_review_input(request,seed,compact,design,rows)
    return request,seed,compact,design,rows,payload

def test_selection_binds_to_exact_original_field_without_model_copying():
    request,seed,compact,design,rows,p=context()
    field=next(f for f in p["source_fields"] if f["compact_pointer"]=="/scenes/3/emotional_transition")
    raw=dict(review_id=p["review_id"],decision="REWRITE",findings=[dict(field_id=field["id"],category="LANGUAGE",reason="Clean the actual label typo",repair_instruction="Use a clean emotional-transition label")],summary="Synthetic selection; no model-quality verdict")
    review=bind_review(raw,p,request,seed,compact,design,rows)
    assert review.findings[0].source_value==field["value"]
    assert review.findings[0].compact_pointer=="/scenes/3/emotional_transition"
    assert "rel relieved" in json.dumps(review.findings[0].source_value)
    assert "source_value" not in p["output_schema"]["$defs"]["ReviewSelectionV2"]["properties"]
    assert "design_pointer" not in p["output_schema"]["$defs"]["ReviewSelectionV2"]["properties"]

@pytest.mark.parametrize("defect",["stale","unknown","copied_value","wrong_decision","duplicate","table_value","table_pointer","projection"])
def test_invalid_selection_or_tampered_context_rejects(tmp_path,defect):
    request,seed,compact,design,rows,p=context();p=copy.deepcopy(p)
    finding=dict(field_id=p["source_fields"][0]["id"],category="CAUSALITY",reason="Synthetic blocker",repair_instruction="Reconsider plan")
    raw=dict(review_id=p["review_id"],decision="REWRITE",findings=[finding],summary="Control")
    if defect=="stale": raw["review_id"]="0"*64
    elif defect=="unknown": finding["field_id"]="/design/fixture/scene_plans/0"
    elif defect=="copied_value": finding["source_value"]="fabricated"
    elif defect=="wrong_decision": raw["decision"]="PASS"
    elif defect=="duplicate": raw["findings"].append(copy.deepcopy(finding))
    elif defect=="table_value": p["source_fields"][0]["value"]="changed"
    elif defect=="table_pointer": p["source_fields"][0]["compact_pointer"]="/seed/world"
    else: p["projected_transitions"][0]["exit"]["open_threads"]=[]
    with pytest.raises(ValueError): bind_review(raw,p,request,seed,compact,design,rows)

def test_strict_schema_bounds_review_id_and_editable_source_ids():
    *_,p=context()
    kwargs,expected=request_for("plan_guard",p,RunConfigV1())
    schema=kwargs["response_format"]["json_schema"]["schema"]
    assert kwargs["response_format"]["type"]=="json_schema" and kwargs["response_format"]["json_schema"]["strict"] is True
    assert expected["response_format"]==kwargs["response_format"]
    assert schema["properties"]["review_id"]["enum"]==[p["review_id"]]
    assert schema["$defs"]["ReviewSelectionV2"]["properties"]["field_id"]["enum"]==[f["id"] for f in p["source_fields"]]
    assert all(not f["compact_pointer"].startswith("/fixture") for f in p["source_fields"])
    assert all("target_scene_id" not in f["compact_pointer"] for f in p["source_fields"])
    assert p["projected_transitions"][3]["exit"]["resolved_threads"]==p["projected_transitions"][4]["entry"]["resolved_threads"]
