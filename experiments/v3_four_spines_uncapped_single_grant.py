"""Paid Spine-only four-genre Final V3 UNCAPPED qualification wrapper.

User-authorized aggregate planning ceiling: $2, four exact age-18 cases.
No Writer, no invented human creative approval, no retries, no fallback,
no story repair/publication/world-state changes. One grant / one run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.frozen_lane_stage import run as frozen_stage_run
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest
from src.v3_single_attempt_guard import (
    FROZEN_V3_SHA, SPINE_MODELS, SafetyStop, SingleAttemptSpineGuard
)

ROOT=Path("data/specifications/story_lab/four_genre_v3_inputs")
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v3_uncapped.json")
MATRIX=Path("data/specifications/story_lab/v3_four_genre_stress_matrix_20261015.json")
ORDER=("closed_platform","orbit_rescue","council_seal","mirror_marsh")
TOTAL_LIMIT=Decimal("2.00")
CASE_LIMIT=Decimal("0.50")
GRANT_SCHEMA="lumi.v3-four-spine-uncapped-paid-once.v1"


def _read(path:Path)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict):
        raise SafetyStop("INVALID_JSON_OBJECT")
    return data


def _paid_grant(grant:dict)->None:
    if grant.get("schema")!=GRANT_SCHEMA or grant.get("authorized") is not True:
        raise SafetyStop("MISSING_EXPLICIT_BATCH_AUTHORIZATION")
    if grant.get("stage")!="SPINE_ONLY" or grant.get("models")!=list(SPINE_MODELS):
        raise SafetyStop("GRANT_STAGE_OR_MODEL_MISMATCH")
    if grant.get("frozen_v3_sha")!=FROZEN_V3_SHA or grant.get("runtime_revision")!="AGE18-V3-UNCAPPED-v1":
        raise SafetyStop("GRANT_FROZEN_SOURCE_OR_NEW_REVISION_MISMATCH")
    if grant.get("case_order")!=list(ORDER):
        raise SafetyStop("FOUR_EXACT_CASES_REQUIRED")
    if grant.get("total_ceiling_usd")!="2.00" or grant.get("per_case_ceiling_usd")!="0.50":
        raise SafetyStop("GRANT_BUDGET_MISMATCH")
    if grant.get("maximum_provider_posts")!=8 or grant.get("no_auto_retry") is not True:
        raise SafetyStop("GRANT_CALL_BOUNDARY_MISMATCH")
    if grant.get("writer_authorized") is not False or grant.get("human_spine_approval") is not False:
        raise SafetyStop("WRITER_OR_CREATIVE_APPROVAL_UNAUTHORIZED")
    if grant.get("reference")!="user 2026-10-15 continue four Spine trials on uncapped V3 under prior 2 USD envelope":
        raise SafetyStop("AUTHORIZATION_REFERENCE_MISMATCH")
    gid=grant.get("grant_id")
    if not isinstance(gid,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid) is None:
        raise SafetyStop("ONE_USE_GRANT_ID_INVALID")
    approved_sha=grant.get("approved_run_commit_sha")
    if not isinstance(approved_sha,str) or re.fullmatch(r"[0-9a-f]{40}",approved_sha) is None:
        raise SafetyStop("APPROVED_CODE_SHA_MISSING")


def _check_source(grant:dict)->list[tuple[str,Path]]:
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if head!=grant["approved_run_commit_sha"]:
        raise SafetyStop("RUN_COMMIT_NOT_EXACTLY_APPROVED")
    if subprocess.run(["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],check=False).returncode:
        raise SafetyStop("FROZEN_V3_NOT_ANCESTOR")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():
        raise SafetyStop("SOURCE_CHECKOUT_DIRTY")
    snapshot=verify_frozen_lane(PROFILE)
    if snapshot.get("verified_files")!=43 or snapshot.get("verified") is not True or snapshot.get("runtime_revision")!="AGE18-V3-UNCAPPED-v1":
        raise SafetyStop("FROZEN_V3_SOURCE_VERIFICATION_FAILED")
    matrix=_read(MATRIX)
    if matrix.get("provider_dispatch_authorized") is not False or len(matrix.get("cases",[]))!=4:
        raise SafetyStop("MATRIX_SOURCE_AUTHORITY_MISMATCH")
    out=[]
    for slug,entry in zip(ORDER,matrix["cases"]):
        if entry["case_id"].split(".")[1].replace("-","_")!=slug:
            raise SafetyStop("MATRIX_ORDER_MISMATCH")
        if entry.get("saga_input_status")!="CREATED_SCHEMA_VALID" or not entry.get("real_spine_eligible"):
            raise SafetyStop("CASE_SCHEMA_QUALIFICATION_MISSING")
        path=ROOT/f"{slug}_case_manifest_v1.json"
        case=load_case_manifest(path)
        if case.get("case_id")!=entry["case_id"] or case.get("paid_spine_authorized") is not False or case.get("lane_profile")!=str(PROFILE):
            raise SafetyStop("CASE_MANIFEST_MISMATCH")
        if case.get("human_spine_approval") is not False:
            raise SafetyStop("PREAPPROVAL_FORBIDDEN")
        if case["inputs"]["spine"]!=entry["input_files"]["saga_spine"]:
            raise SafetyStop("CASE_SPINE_SOURCE_MISMATCH")
        out.append((slug,path))
    return out


def _durable_json(path:Path,obj:dict):
    data=(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())


def _claim_once(claim_dir:Path, grant:dict):
    if not claim_dir.is_absolute():
        raise SafetyStop("PERSISTENT_ABSOLUTE_CLAIM_DIR_REQUIRED")
    claim_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    digest=hashlib.sha256(grant["grant_id"].encode("utf-8")).hexdigest()
    _durable_json(claim_dir/f"{digest}.json",{
        "schema":"lumi.v3-four-spine-uncapped-paid-claim.v1",
        "grant_id_sha256":digest,
        "approved_run_commit_sha":grant["approved_run_commit_sha"],
    })


def run(*,grant_path:Path,claim_dir:Path,evidence_dir:Path)->dict:
    grant=_read(grant_path)
    _paid_grant(grant)
    cases=_check_source(grant)
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SafetyStop("PROVIDER_KEY_MISSING")
    if not evidence_dir.is_absolute() or evidence_dir.exists():
        raise SafetyStop("UNIQUE_ABSOLUTE_EVIDENCE_DIRECTORY_REQUIRED")
    # Durable once-only claim is consumed even on provider timeout / unknown charge.
    _claim_once(claim_dir,grant)
    evidence_dir.mkdir(parents=True,mode=0o700)
    total=Decimal("0")
    results=[]
    try:
        for slug,case in cases:
            if total>=TOTAL_LIMIT:
                raise SafetyStop("GLOBAL_BUDGET_EXHAUSTED")
            budget=min(CASE_LIMIT,TOTAL_LIMIT-total)
            folder=evidence_dir/slug
            folder.mkdir(mode=0o700)
            trigger=folder/"trigger.json"
            _durable_json(trigger,{
                "schema_version":"frozen-lane-stage-trigger.v1",
                "stage":"SPINE",
                "paid_authorized":True,
                "case_manifest":str(case),
            })
            guard=SingleAttemptSpineGuard(folder,budget)
            status="STOP_UNSETTLED"
            try:
                with guard.installed():
                    result=frozen_stage_run(trigger_path=trigger,out_dir=folder/"stage")
                status=str(result.get("result_status") or "UNKNOWN")
            except BaseException:
                # Cost must be counted even when structured JSON is unusable.
                # Provider observation is recorded before response parsing.
                status="STOP_FAILED_SPINE_STAGE"
                raise
            finally:
                total+=guard.spent
                _durable_json(folder/"cost-receipt.json",{
                    "case":slug,"model_posts":guard.calls,
                    "reported_cost_usd":str(guard.spent),
                    "aggregate_cost_usd":str(total),
                    "status":status,
                    "human_approval_required":True,
                    "writer_dispatched":False,
                })
                results.append({"case":slug,"status":status,"posts":guard.calls,
                                "cost_usd":str(guard.spent)})
            # A valid non-ACCEPT gate is a qualified case failure; do not
            # automatically regenerate/replan the same case. Continue only
            # if the independent stage returned normally with settled cost.
    except BaseException as exc:
        try:
            _durable_json(evidence_dir/"stopped.json",{
                "reason_type":type(exc).__name__,
                "reason_code":str(exc)[:150] if isinstance(exc,SafetyStop) else "STAGE_STOPPED",
                "completed_cases":results,
                "aggregate_confirmed_usd":str(total),
                "unfinished_cases":list(ORDER[len(results):]),
                "no_automatic_retry":True,
            })
        except Exception:
            pass
        raise
    summary={
        "schema":"lumi.v3-four-spine-uncapped-paid-result.v1",
        "status":"FOUR_SPINE_ATTEMPTS_FINISHED_WRITER_BLOCKED",
        "results":results,"aggregate_confirmed_usd":str(total),
        "total_approved_usd":"2.00",
        "human_approval_required_for_each_writer":True,
        "english_repair_not_run":True,"turkish_translation_not_run":True,
        "production_canon_writes":0
    }
    _durable_json(evidence_dir/"summary.json",summary)
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--grant",type=Path,required=True)
    p.add_argument("--claim-dir",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(run(grant_path=a.grant,claim_dir=a.claim_dir,
                         evidence_dir=a.evidence_dir),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
