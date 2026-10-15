"""V4 contract tests: actual V4 source rules, no paid provider calls."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.v4_logistics import (canonical_beat_route,derive_spine_route,
    apply_logistics_model_patch,V4RepairRejected)
from src.v4_full_pipeline import build_model_reviewed_spine
from src.episode_writer_v4_generate import _validate_source,build_writer_input

F2=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")

def exemplar():
    return copy.deepcopy(json.loads(F2.read_text(encoding="utf-8")))

def test_model_architect_can_omit_nonadjacent_visits_and_python_derives_exact_route():
    original=exemplar()["episode_spine"]
    expected=canonical_beat_route(original["beats"])
    bad=copy.deepcopy(original)
    bad["logistics_plan"]["location_sequence"]=[expected[0],expected[-1]]
    if bad["logistics_plan"]["location_sequence"]==expected:
        bad["logistics_plan"]["location_sequence"]=[expected[0]]
    with pytest.raises(ValidationError):
        EpisodeSpineV2.model_validate(bad)
    fixed,report=derive_spine_route(bad)
    assert report["changed"] is True
    assert report["input_sha256"]!=report["output_sha256"]
    assert fixed["logistics_plan"]["location_sequence"]==expected
    assert fixed["beats"]==bad["beats"]
    assert bad["logistics_plan"]["location_sequence"]!=expected
    EpisodeSpineV2.model_validate(fixed)

def test_generalized_repeat_visits_are_preserved():
    rows=[{"location_ref":x} for x in ["A","A","B","C","A","B","A","B","A"]]
    assert canonical_beat_route(rows)==["A","B","C","A","B","A","B","A"]

@pytest.mark.parametrize("field",["beats","logistics_plan.location_sequence",
    "episode_role","decision_point.branches","writer_rules"])
def test_haiku_forbidden_edit_is_rejected(field):
    raw=exemplar()["episode_spine"]
    raw,_=derive_spine_route(raw)
    with pytest.raises(V4RepairRejected):
        apply_logistics_model_patch(raw,{"patches":[{"field":field,"value":"tamper"}]})

def test_only_bounded_model_logistics_prose_is_accepted():
    raw=exemplar()["episode_spine"]
    raw,_=derive_spine_route(raw)
    replacement="All transitions, including decision-to-climax and final payoff, require travel. Feasibility remains conditional on the established movement windows."
    new,applied=apply_logistics_model_patch(raw,{
        "patches":[{"field":"logistics_plan.feasibility_rationale","value":replacement}]})
    assert len(applied)==1
    assert new["beats"]==raw["beats"]
    assert new["logistics_plan"]["location_sequence"]==raw["logistics_plan"]["location_sequence"]
    assert new["logistics_plan"]["feasibility_rationale"]==replacement
    EpisodeSpineV2.model_validate(new)

def test_unverified_location_disallowed():
    raw=exemplar()["episode_spine"]
    with pytest.raises(V4RepairRejected,match="UNAUTHORIZED_LOCATION_REF"):
        derive_spine_route(raw,allowed_locations={"nowhere"})

def test_v4_model_approval_cannot_be_forged_as_human_review():
    approved=exemplar()
    source={
        "status":"v4_gate_accept_model_reviewed",
        "v4_version":"V4",
        "gate":approved["gate"],
        "episode_spine":approved["episode_spine"],
        "approved_premise":approved["approved_premise"],
        "projection":approved["projection"],
        "usage_rollup":approved["source_usage_rollup"],
    }
    newer=build_model_reviewed_spine(source,case_id="age18.closed-platform.mystery.stress-01")
    assert newer["schema_version"]=="episode-spine-v4-model-reviewed.v1"
    assert newer["human_review"]["verdict"]!="APPROVE"
    assert newer["model_creative_review"]["verdict"]=="ACCEPT"
    _validate_source(newer)
    writer_input=build_writer_input(newer,authority_packet_version="v2")
    assert writer_input["task"]=="write_episode_from_v4_luna_accepted_spine"
    assert "human_review" not in writer_input
    invalid=copy.deepcopy(newer)
    invalid["human_review"]={"verdict":"APPROVE"}
    with pytest.raises(RuntimeError,match="Never forge"):
        _validate_source(invalid)
    other=copy.deepcopy(newer)
    other["model_creative_review"]["verdict"]="REPLAN"
    with pytest.raises(RuntimeError,match="evidence"):
        _validate_source(other)
    tampered=copy.deepcopy(newer)
    tampered["episode_spine"]["title"]="Injected and unreviewed"
    with pytest.raises(RuntimeError,match="source hash mismatch"):
        _validate_source(tampered)

def test_v4_full_runner_no_grant_does_not_dispatch(tmp_path):
    from src.v4_full_pipeline import run
    with pytest.raises(RuntimeError,match="PAID_AUTHORIZATION"):
        run(case_manifest=Path("not-even-read.json"),out_dir=tmp_path/"out")
    assert not (tmp_path/"out").exists()
