"""V4.2 regression: two real process-style repair rounds, fake model IO only."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.v4_2_full_pipeline import run
from src.story_stage_common import write_json
from src.episode_bounded_repair_v4_2 import MAX_REPAIR_ATTEMPTS

CASE=Path("data/specifications/story_lab/four_genre_v3_inputs/closed_platform_case_manifest_v4_2.json")
F2=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")

def _exercise(tmp_path,*,repeat_second=False,quality_rounds=2):
    p=json.loads(F2.read_text())
    source={"status":"v4_gate_accept_model_reviewed","v4_version":"V4",
            "gate":p["gate"],"episode_spine":p["episode_spine"],
            "approved_premise":p["approved_premise"],
            "projection":p["projection"],"usage_rollup":p["source_usage_rollup"]}
    stories=["A clean initial English story.","An initial English story, corrected once.",
             "An initial English story, corrected twice."]
    calls=[];quality=0;repairs=0
    def stage(*,trigger_path,out_dir):
        nonlocal quality,repairs
        v=json.loads(trigger_path.read_text());name=v["stage"]
        calls.append(name)
        common={"pipeline_usage_rollup":{"calls":[]}}
        if name=="SPINE":
            result=source
        elif name=="WRITER":
            result={"status":"writer_generated","story":stories[0],
                    "deterministic_checks":{"non_empty":True,"title_present":True}}
        elif name=="AUTHORITY_GATE":
            quality+=1
            result={**common,"status":"semantic_findings_need_adjudication",
                    "story":stories[min(repairs,2)],
                    "next_stage":"SEMANTIC_ADJUDICATION"} if quality<=quality_rounds else {
                    **common,"status":"clean","story":stories[min(repairs,2)],
                    "next_stage":"TRANSLATION"}
        elif name=="SEMANTIC_ADJUDICATION":
            result={**common,"status":"confirmed_findings","story":stories[min(repairs,2)],
                    "confirmed_findings":[{"repair_scope":"local","exact_quote":"some invalid fact"}],
                    "next_stage":"BOUNDED_REPAIR"}
        elif name=="BOUNDED_REPAIR":
            repairs+=1
            new=stories[1] if repeat_second else stories[min(repairs,2)]
            result={**common,"status":"repaired_recheck_required",
                    "repaired_story":new,
                    "english_repair_attempts":repairs,
                    "next_stage":"AUTHORITY_GATE_RECHECK"}
        elif name=="TRANSLATION":
            result={**common,"status":"semantic_guard_clean","next_stage":"FIDELITY",
                    "accepted_english_master":stories[2],"turkish_delivery":"Bir hikâye."}
        elif name=="FIDELITY":
            result={**common,"status":"clean","publication_ready":True,
                    "next_stage":"FINALIZE","accepted_english_master":stories[2],
                    "turkish_delivery":"Bir hikâye."}
        elif name=="FINALIZE":
            result={"status":"publication_ready","publication_ready":True,
                    "english_word_count":5,"turkish_word_count":2,
                    "product_path_cost_usd":0}
        else:raise AssertionError(name)
        write_json(out_dir/"result.json",result)
        return {"result_status":result["status"]}
    with patch("src.v4_2_full_pipeline.verify_frozen_lane",return_value={
        "runtime_revision":"AGE18-V4-ITERATIVE-QUALITY-REPAIR-v1","verified_files":65,
        "verified":True
    }):
        try: result=run(case_manifest=CASE,out_dir=tmp_path/"result",paid_authorized=True,
                        stage_dispatch=stage)
        except BaseException:
            result=None
            if not repeat_second and quality_rounds<=2:raise
    return result,calls

def test_two_distinct_model_repairs_then_complete_en_tr_offline(tmp_path):
    assert MAX_REPAIR_ATTEMPTS==3
    result,calls=_exercise(tmp_path)
    assert result["status"]=="EN_TR_STORY_COMPLETE_UNPUBLISHED"
    assert calls.count("BOUNDED_REPAIR")==2
    assert calls.count("AUTHORITY_GATE")==3
    assert calls.count("SEMANTIC_ADJUDICATION")==2
    assert calls[-1]=="FINALIZE"
    assert result["human_approval_fabricated"] is False
    assert result["world_state_commits"]==0
    assert result["publication_actions"]==0

def test_repeated_story_after_second_patch_aborts(tmp_path):
    result,calls=_exercise(tmp_path,repeat_second=True)
    assert result is None
    assert calls.count("BOUNDED_REPAIR")==2
    stopped=json.loads((tmp_path/"result/stopped.json").read_text())
    assert stopped["reason"]=="V4_2_REPAIR_CYCLE_NO_PROGRESS"
    assert stopped["world_state_commits"]==0

def test_three_rounds_then_stops_on_fourth_unresolved_diagnosis(tmp_path):
    result,calls=_exercise(tmp_path,quality_rounds=4)
    assert result is None
    assert calls.count("BOUNDED_REPAIR")<=3
    assert calls[-1]!="FINALIZE"

def test_output_token_ceiling_absent_and_version_distinct():
    from src.v4_2_full_pipeline import PROFILE,STAGE_LIMIT
    assert "v4_2" in str(PROFILE)
    assert STAGE_LIMIT==24
    assert MAX_REPAIR_ATTEMPTS==3
