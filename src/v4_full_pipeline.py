"""V4 complete one-case story pipeline (EN -> TR) with explicit model review.

No human approval is fabricated; independent Luna ACCEPT is separately named
model approval. The product path never commits world state or publishes content.
No manual story edits. All paid requests require an external one-use grant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from src.episode_spine_v2_contract import EpisodeSpineGateV2, EpisodeSpineV2
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest
from src.story_stage_common import read_json, write_json
from src.v4_lane_stage import run as v4_stage_run

STAGE_LIMIT=16
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v4.json")


def build_model_reviewed_spine(spine_result:dict[str,Any], *, case_id:str)->dict[str,Any]:
    if spine_result.get("status")!="awaiting_human_review":
        raise RuntimeError("V4_SPINE_NOT_FROZEN_VALIDATED")
    gate=EpisodeSpineGateV2.model_validate(spine_result.get("gate"))
    if gate.decision!="ACCEPT":
        raise RuntimeError("V4_INDEPENDENT_LUNA_GATE_REPLAN")
    spine=EpisodeSpineV2.model_validate(spine_result.get("episode_spine"))
    if spine_result.get("v4_version")!="V4":
        raise RuntimeError("V4_GENERIC_ROUTE_ENGINE_NOT_EXECUTED")
    canonical=spine.model_dump(mode="json",by_alias=True)
    encoded=json.dumps(canonical,sort_keys=True,ensure_ascii=False).encode("utf-8")
    digest=hashlib.sha256(encoded).hexdigest()
    review={
        "model":"openai/gpt-5.6-luna",
        "verdict":"ACCEPT",
        "automated":True,
        "source_spine_sha256":digest,
        "basis":"independent V4 Luna gate + full deterministic EpisodeSpineV2 contract",
    }
    return {
        "schema_version":"episode-spine-v4-model-reviewed.v1",
        "source_run_id":digest,
        "qualification_provenance":{"case_id":case_id,"lane_revision":"AGE18-V4-DERIVED-LOGISTICS-v1"},
        "model_creative_review":review,
        "human_review":{"verdict":"NOT_REQUESTED_FOR_V4_AUTONOMOUS_QUALIFICATION"},
        "approved_premise":spine_result["approved_premise"],
        "projection":spine_result["projection"],
        "episode_spine":canonical,
        "gate":gate.model_dump(mode="json",by_alias=True),
        "source_usage_rollup":spine_result["usage_rollup"],
    }


def run(*,case_manifest:Path,out_dir:Path, paid_authorized:bool=False,
        stage_dispatch:Callable[...,dict[str,Any]]=v4_stage_run)->dict[str,Any]:
    if paid_authorized is not True:
        raise RuntimeError("V4_REQUIRES_OWNER_GRANTED_EXPLICIT_PAID_AUTHORIZATION")
    case=load_case_manifest(case_manifest)
    if case["lane_profile"]!=str(PROFILE) or case["case_id"]!="age18.closed-platform.mystery.stress-01":
        raise RuntimeError("V4_CASE_IS_NOT_FRESH_APPROVED_TARGET")
    verification=verify_frozen_lane(PROFILE)
    if verification["runtime_revision"]!="AGE18-V4-DERIVED-LOGISTICS-v1":
        raise RuntimeError("V4_SOURCE_REVISION_MISMATCH")
    if out_dir.exists():
        raise RuntimeError("V4_EVIDENCE_DIRECTORY_MUST_BE_NEW")
    out_dir.mkdir(parents=True)
    steps=[]
    approved_path=out_dir/"v4_luna_reviewed_spine.json"
    current_path:Path|None=None

    def step(name:str,**kwargs)->dict[str,Any]:
        if len(steps)>=STAGE_LIMIT:
            raise RuntimeError("V4_EXCEEDED_EXPECTED_STAGE_COUNT")
        stage_dir=out_dir/f"{len(steps)+1:02d}_{name.lower()}"
        stage_dir.mkdir(parents=True)
        trigger={
            "schema_version":"frozen-lane-stage-trigger.v1",
            "stage":name,"paid_authorized":True,
            "case_manifest":str(case_manifest),**{k:str(v) for k,v in kwargs.items()},
        }
        trigger_path=stage_dir/"trigger.json"
        write_json(trigger_path,trigger)
        try:
            envelope=stage_dispatch(trigger_path=trigger_path,out_dir=stage_dir)
        except BaseException as exc:
            steps.append({"stage":name,"status":"STAGE_STOPPED",
                          "reason_type":type(exc).__name__,
                          "result_path":str(stage_dir/"result.json")})
            raise
        result_path=stage_dir/"result.json"
        result=read_json(result_path)
        steps.append({"stage":name,"status":result.get("status"),
                      "result_path":str(result_path)})
        return result

    try:
        spine=step("SPINE")
        accepted=build_model_reviewed_spine(spine,case_id=case["case_id"])
        write_json(approved_path,accepted)
        writer=step("WRITER",approved=approved_path)
        dc=writer.get("deterministic_checks") or {}
        if not dc.get("non_empty") or not dc.get("title_present"):
            raise RuntimeError("V4_WRITER_EMPTY_OR_TITLE_MISSING")
        current_path=out_dir/"02_writer"/"result.json"
        quality_repairs=0
        while True:
            quality=step("AUTHORITY_GATE",source=current_path,approved=approved_path)
            qnext=quality.get("next_stage")
            current_path=Path(steps[-1]["result_path"])
            if qnext=="SEMANTIC_ADJUDICATION":
                adjudicated=step("SEMANTIC_ADJUDICATION",source=current_path)
                qnext=adjudicated.get("next_stage")
                current_path=Path(steps[-1]["result_path"])
            if qnext=="TRANSLATION":
                source_english=read_json(current_path)
                accepted_en=source_english.get("story") or source_english.get("repaired_story")
                if not isinstance(accepted_en,str) or not accepted_en.strip():
                    raise RuntimeError("V4_ACCEPTED_ENGLISH_TEXT_MISSING")
                en_path=out_dir/"accepted_en.json"
                write_json(en_path,{
                    "schema_version":"v4-accepted-english.v1",
                    "accepted_english_master":accepted_en,
                    "story":accepted_en,
                    "pipeline_usage_rollup":source_english["pipeline_usage_rollup"],
                    "english_repair_attempts":quality_repairs,
                })
                current_path=en_path
                break
            if qnext!="BOUNDED_REPAIR" or quality_repairs>=1:
                raise RuntimeError("V4_ENGLISH_QUALITY_BLOCKED")
            fixed=step("BOUNDED_REPAIR",source=current_path,approved=approved_path)
            if fixed.get("next_stage")!="AUTHORITY_GATE_RECHECK":
                raise RuntimeError("V4_ENGLISH_REPAIR_NOT_CLEAN")
            quality_repairs+=1
            current_path=Path(steps[-1]["result_path"])

        translated=step("TRANSLATION",source=current_path,approved=approved_path)
        current_path=Path(steps[-1]["result_path"])
        translation_repairs=0
        if translated.get("next_stage")=="TRANSLATION_REPAIR":
            repaired=step("TRANSLATION_REPAIR",source=current_path)
            if repaired.get("next_stage")!="FIDELITY":
                raise RuntimeError("V4_TURKISH_REPAIR_NOT_CLEAN")
            current_path=Path(steps[-1]["result_path"])
            translation_repairs+=1
        elif translated.get("next_stage")!="FIDELITY":
            raise RuntimeError("V4_TRANSLATION_BLOCKED")
        while True:
            fidelity=step("FIDELITY",source=current_path)
            current_path=Path(steps[-1]["result_path"])
            fnext=fidelity.get("next_stage")
            if fnext=="FIDELITY_ADJUDICATION":
                adjudication=step("FIDELITY_ADJUDICATION",source=current_path)
                current_path=Path(steps[-1]["result_path"])
                fnext=adjudication.get("next_stage")
            if fnext=="FINALIZE" and read_json(current_path).get("publication_ready") is True:
                break
            if fnext!="TRANSLATION_REPAIR" or translation_repairs>=1:
                raise RuntimeError("V4_TURKISH_FIDELITY_BLOCKED")
            repaired=step("TRANSLATION_REPAIR",source=current_path)
            if repaired.get("next_stage")!="FIDELITY":
                raise RuntimeError("V4_TURKISH_REPAIR_NOT_CLEAN")
            translation_repairs+=1
            current_path=Path(steps[-1]["result_path"])
        final=step("FINALIZE",source=current_path,approved=approved_path)
        if final.get("publication_ready") is not True:
            raise RuntimeError("V4_FINAL_DELIVERY_NOT_READY")
        summary={
            "schema":"v4-one-case-e2e-evidence.v1",
            "status":"EN_TR_STORY_COMPLETE_UNPUBLISHED",
            "case_id":case["case_id"],
            "stage_results":steps,
            "english_word_count":final["english_word_count"],
            "turkish_word_count":final["turkish_word_count"],
            "total_pipeline_cost_usd":final["product_path_cost_usd"],
            "human_approval_fabricated":False,
            "model_creative_review":accepted["model_creative_review"],
            "world_state_commits":0,
            "publication_actions":0,
            "manual_story_edits":0,
        }
        write_json(out_dir/"summary.json",summary)
        return summary
    except BaseException as exc:
        write_json(out_dir/"stopped.json",{
            "status":"FAILED_NO_PUBLICATION",
            "reason_type":type(exc).__name__,
            "reason":str(exc)[:500],
            "stage_results":steps,
            "human_approval_fabricated":False,
            "world_state_commits":0,"publication_actions":0,
            "manual_story_edits":0,
        })
        raise


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--case-manifest",type=Path,default=Path("data/specifications/story_lab/four_genre_v3_inputs/closed_platform_case_manifest_v4.json"))
    p.add_argument("--out-dir",required=True,type=Path)
    p.add_argument("--paid-authorized",action="store_true")
    a=p.parse_args()
    print(json.dumps(run(case_manifest=a.case_manifest,out_dir=a.out_dir,
                         paid_authorized=a.paid_authorized),ensure_ascii=False))


if __name__=="__main__":
    main()
