"""One paid read-only Luna evidence judgment; never commits state or publishes.

Frozen Final V3 remains unchanged. Model extracts exact quotes for the five
Spine-derived persistent outcomes. Historical bilingual package is immutable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import patch

from src import v3_single_attempt_guard as base_guard
from src import english_story_pipeline as provider
from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_guard import SafetyStop, SingleAttemptSpineGuard
from experiments.v3_f2_world_outcome_evidence_gate import (
    STAGED, EXPECTED_EN, EXPECTED_TR, validate_judge_output,
)
from experiments.v3_f2_final_delivery_stage import verify_sources

MODEL="openai/gpt-5.6-luna"
CASE_ID="age18.forbidden-cartographer.fantasy.frozen-01"
FROZEN_V3_SHA="63e1e3ce82c244bc5bb02b0463a9a1a6715c941b"
PARENT_SHA="3aa9af4f02154f7652d3f9844e194202efc8a936"
MAX_ADMISSION_USD=Decimal("0.03")
PROMPT=Path("prompts/v3_f2_world_outcome_evidence_judge_v1_generic.md")
APPROVED=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")
ALLOWED_CHANGED=frozenset("""
experiments/v3_f2_world_outcome_one_judge.py
tests/test_v3_f2_world_outcome_one_judge.py
docs/qualifications/V3_F2_WORLD_OUTCOME_ONE_LUNA_20261015.md
""".split())


def digest(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(ok:bool,code:str):
    if not ok:
        raise SafetyStop(code)


class SingleWorldJudgeGuard(SingleAttemptSpineGuard):
    def event(self,kind,**fields):
        if kind=="GUARD_INSTALLED":
            fields["permitted_models"]=[MODEL]
            fields["provider_post_limit"]=1
            fields["attempts_per_model"]=1
        return super().event(kind,**fields)

    @contextmanager
    def installed_single_judge(self):
        with patch.object(base_guard,"SPINE_MODELS",(MODEL,)):
            with super().installed():
                yield self


def input_packet()->dict:
    data=json.loads((STAGED/"delivery-manifest.json").read_text(encoding="utf-8"))
    proposals=json.loads((STAGED/"state-proposals.json").read_text(encoding="utf-8"))
    approved=json.loads(APPROVED.read_text(encoding="utf-8"))
    return {
        "case_id":CASE_ID,
        "english_story":(STAGED/"story.en.txt").read_text(encoding="utf-8"),
        "source_story_sha256":EXPECTED_EN,
        "approved_branch_options":approved["episode_spine"]["decision_point"]["branches"],
        "original_spine_constraints":approved["episode_spine"]["constraints"],
        "original_saga_milestone":approved["episode_spine"]["saga_progression"],
        "persistent_outcome_candidates":[{
            "candidate_id":x["candidate_id"],
            "kind":x["kind"],
            "description":x["source_description"],
            "commit_condition":x["source_commit_condition"],
        } for x in proposals["candidate_operations"]],
        "delivery_status":data["status"],
        "published":False,
        "world_state_committed":False,
    }


def preflight(grant_file:Path,claim_dir:Path,evidence_dir:Path):
    grant=json.loads(grant_file.read_text(encoding="utf-8"))
    required={
        "schema":"lumi.v3-f2-world-outcome-judge-grant.v1",
        "authorized":True,
        "stage":"WORLD_OUTCOME_EVIDENCE_ONLY",
        "case_id":CASE_ID,
        "english_story_sha256":EXPECTED_EN,
        "turkish_story_sha256":EXPECTED_TR,
        "model":MODEL,
        "frozen_runtime_sha":FROZEN_V3_SHA,
        "source_delivery_commit":PARENT_SHA,
    }
    _require(all(grant.get(k)==v for k,v in required.items()),
             "WORLD_JUDGE_GRANT_SCOPE_INVALID")
    gid=grant.get("grant_id")
    _require(isinstance(gid,str) and re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid) is not None,
        "WORLD_JUDGE_GRANT_ID_INVALID")
    ref=grant.get("human_paid_authorization_reference")
    _require(isinstance(ref,str) and bool(ref.strip()),
             "WORLD_JUDGE_SEPARATE_PAID_GRANT_REQUIRED")
    try: cap=Decimal(str(grant["max_total_usd"]))
    except (KeyError,InvalidOperation,ValueError,TypeError) as exc:
        raise SafetyStop("WORLD_JUDGE_CEILING_INVALID") from exc
    _require(cap.is_finite() and Decimal(0)<cap<=MAX_ADMISSION_USD,
             "WORLD_JUDGE_CEILING_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    _require(grant.get("guard_commit_sha")==head,"WORLD_JUDGE_GUARD_SHA_MISMATCH")
    _require(subprocess.run(["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],
                            check=False).returncode==0,"WORLD_JUDGE_FROZEN_ANCESTRY_INVALID")
    changed=set(subprocess.check_output(
        ["git","diff","--name-only",PARENT_SHA,head],text=True
    ).splitlines())
    _require(bool(changed) and changed.issubset(ALLOWED_CHANGED),
             "WORLD_JUDGE_UNREVIEWED_FILE_CHANGE")
    _require(not subprocess.check_output(
        ["git","status","--porcelain","--untracked-files=normal"],text=True
    ).strip(),"WORLD_JUDGE_DIRTY_CHECKOUT")
    verify_sources()
    frozen=verify_frozen_lane(Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json"))
    _require(frozen["verified_files"]==43,"WORLD_JUDGE_FROZEN_43_FAIL")
    _require((STAGED/"story.en.txt").is_file() and digest(STAGED/"story.en.txt")==EXPECTED_EN,
             "WORLD_JUDGE_ENGLISH_HASH_INVALID")
    _require((STAGED/"story.tr.txt").is_file() and digest(STAGED/"story.tr.txt")==EXPECTED_TR,
             "WORLD_JUDGE_TURKISH_HASH_INVALID")
    _require(claim_dir.is_absolute() and evidence_dir.is_absolute() and not evidence_dir.exists(),
             "WORLD_JUDGE_ABSOLUTE_NEW_EVIDENCE_DIR_REQUIRED")
    _require(os.getenv("LUMI_WORLD_JUDGE_GLOBAL_CLAIM_VERIFIED")=="YES",
             "WORLD_JUDGE_GLOBAL_RUN_BOUND_CLAIM_MISSING")
    _require(bool(os.getenv("OPENROUTER_API_KEY")),
             "WORLD_JUDGE_OPENROUTER_SECRET_MISSING")
    return cap,gid


def _exclusive_json(path:Path,obj:dict):
    with path.open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def run(*,grant_file:Path,claim_dir:Path,evidence_dir:Path)->dict:
    cap,gid=preflight(grant_file,claim_dir,evidence_dir)
    claim_dir.mkdir(parents=True,mode=0o700,exist_ok=True)
    token=hashlib.sha256(("world-judge:"+gid).encode()).hexdigest()
    try:fd=os.open(claim_dir/(token+".json"),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise SafetyStop("WORLD_JUDGE_GRANT_REPLAY_BLOCKED") from exc
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump({"schema":"lumi.world-judge.one-claim.v1","sha256":token},f)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())

    evidence_dir.mkdir(parents=True,mode=0o700)
    guard=SingleWorldJudgeGuard(evidence_dir,cap)
    guard.event("WORLD_JUDGE_GRANT_VERIFIED",
                case_id=CASE_ID,source_story_sha256=EXPECTED_EN,
                max_planning_usd=str(cap))
    try:
        with guard.installed_single_judge():
            payload,body,_request,_parse_failures=provider.call_structured_json_with_retry(
                api_key=os.environ["OPENROUTER_API_KEY"],
                model=MODEL,
                system_prompt=PROMPT.read_text(encoding="utf-8"),
                user_prompt=json.dumps(input_packet(),ensure_ascii=False),
                temperature=0.0,
                max_tokens=3200,
                seed=2026101507,
                request_class="editorial_audit",
                max_parse_attempts=1,
            )
        _require(guard.calls==1,"WORLD_JUDGE_ONE_PROVIDER_POST_REQUIRED")
        generation=body.get("id")
        _require(isinstance(generation,str) and generation.startswith("gen-"),
                 "WORLD_JUDGE_GENERATION_ID_MISSING")
        # Always record the actual model conclusion BEFORE validating quoted
        # evidence. Malformed or inconsistent model decisions remain reviewable
        # but MUST NOT become an evaluated state delta.
        usage=body.get("usage") or {}
        raw={
            "schema":"lumi.v3-f2.world-outcome-live-model-evidence.v1",
            "model":MODEL,
            "generation_id":generation,
            "source_story_sha256":EXPECTED_EN,
            "reported_cost_usd":str(guard.spent),
            "input_tokens":usage.get("prompt_tokens"),
            "output_tokens":usage.get("completion_tokens"),
            "model_json":payload,
        }
        _exclusive_json(evidence_dir/"judge-model-response.json",raw)
        outcome=validate_judge_output(payload)
        _require(outcome["status"]=="MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED",
                 "WORLD_JUDGE_RESULT_NOT_NONCOMMITTING")
        _exclusive_json(evidence_dir/"world-outcome-proposal.json",outcome)
        result={
            "schema":"lumi.v3-f2.world-outcome-judge-completed.v1",
            "status":"MODEL_WORLD_OUTCOME_REVIEW_STAGED_NOT_COMMITTED",
            "source_english_sha256":EXPECTED_EN,
            "source_turkish_sha256":EXPECTED_TR,
            "provider_model":MODEL,
            "generation_id":generation,
            "provider_posts":guard.calls,
            "reported_new_cost_usd":str(guard.spent),
            "judge_model_response_sha256":digest(evidence_dir/"judge-model-response.json"),
            "proposal_sha256":digest(evidence_dir/"world-outcome-proposal.json"),
            "selected_branch":outcome["model_selected_branch"],
            "candidate_count":len(outcome["approved_persistent_candidates"]),
            "earned_candidate_count":sum(x["model_condition_verdict"]=="EARNED"
                                         for x in outcome["approved_persistent_candidates"]),
            "publication_authorized":False,
            "world_state_committed":False,
            "world_state_commit_authorized":False,
            "applied_operations":[],
        }
        _exclusive_json(evidence_dir/"qualification.json",result)
        guard.event("STAGE_FINISHED",
                    status=result["status"],model_posts=1,
                    reported_cost_usd=str(guard.spent),
                    world_state_committed=False,publication_authorized=False)
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP",
                    exception_type=type(exc).__name__,
                    model_posts=guard.calls,
                    reported_cost_usd=str(guard.spent),
                    world_state_committed=False,
                    publication_authorized=False)
        raise


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--grant",type=Path,required=True)
    p.add_argument("--claim-dir",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    a=p.parse_args()
    result=run(grant_file=a.grant,claim_dir=a.claim_dir,evidence_dir=a.evidence_dir)
    print(json.dumps({
        "status":result["status"],
        "branch":result["selected_branch"],
        "candidate_count":result["candidate_count"],
        "earned_candidate_count":result["earned_candidate_count"],
        "model_posts":result["provider_posts"],
        "world_state_committed":False,
        "publication_authorized":False,
    },ensure_ascii=False))
