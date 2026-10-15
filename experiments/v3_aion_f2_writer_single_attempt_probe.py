"""One authorized Aion Mini Writer POST for frozen Final V3 F2 age-18 case.

Exactly one paid model request; no alternate model, retries, Writer repair,
judge, translation or world-state commit. This does not modify frozen V3.
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

from src.episode_writer_v2_generate import _validate_source, generate, WRITER_MODEL
from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_aion_writer_guard import SingleAttemptAionWriterGuard
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SafetyStop

PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
APPROVED=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")
APPROVED_SHA256="21f1e4e0c9f25cd1c970cccc2df8d09a0f236c9102321df7da086f85a3dac1a0"
SOURCE_F2_SHA256="d54a747ace23f15ea3af5ef37d25e40b1e48d24ba905083e2f1c32e7b49473af"
PROMPT=Path("prompts/episode_writer_v3_generic.md")
CASE_ID="age18.forbidden-cartographer.fantasy.frozen-01"
SOURCE_SPINE_RUN_ID=38700326961
MAX_USD=Decimal("0.10")
ALLOWED_SOURCE_CHANGES={
    "src/v3_single_attempt_guard.py",
    "src/v3_single_attempt_aion_writer_guard.py",
    "experiments/v3_single_attempt_spine_probe.py",
    "experiments/v3_aion_writer_single_attempt_probe.py",
    "experiments/v3_aion_f2_writer_single_attempt_probe.py",
    "tests/test_v3_single_attempt_guard.py",
    "tests/test_v3_single_attempt_aion_writer_guard.py",
    "tests/test_v3_aion_f2_writer_single_attempt_probe.py",
    "docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_GUARD_V1.md",
    "docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_LIVE_WORKFLOW_TEMPLATE.yml",
    "docs/qualifications/V3_AION_MINI_WRITER_SINGLE_ATTEMPT.md",
    "docs/qualifications/V3_AION_F2_WRITER_QUALIFICATION_20261015.md",
    str(APPROVED),
}


def validate_source():
    verified=verify_frozen_lane(PROFILE)
    source_bytes=APPROVED.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest()!=APPROVED_SHA256:
        raise SafetyStop("F2_WRITER_APPROVED_INPUT_SHA_MISMATCH")
    approved=json.loads(source_bytes)
    _validate_source(approved)
    if approved.get("source_run_id")!=SOURCE_SPINE_RUN_ID:
        raise SafetyStop("F2_WRITER_SOURCE_RUN_MISMATCH")
    provenance=approved.get("qualification_provenance") or {}
    if provenance.get("source_archived_sha256")!=SOURCE_F2_SHA256 or provenance.get("case_id")!=CASE_ID:
        raise SafetyStop("F2_WRITER_SOURCE_PROVENANCE_MISMATCH")
    if approved.get("gate",{}).get("decision")!="ACCEPT" or any(
        d.get("blocking_failure") for d in approved.get("gate",{}).get("dimensions",[])
    ):
        raise SafetyStop("F2_WRITER_GATE_NOT_ACCEPTED")
    if approved.get("human_review",{}).get("verdict")!="APPROVE":
        raise SafetyStop("F2_WRITER_HUMAN_APPROVAL_MISSING")
    if WRITER_MODEL!=json.loads(PROFILE.read_text())["runtime"]["writer"]["model"]:
        raise SafetyStop("AION_MODEL_MISMATCH")
    spine=approved["episode_spine"]
    if spine.get("exact_age")!=18:
        raise SafetyStop("F2_AGE_MISMATCH")
    expected=["vellum_hall","greyfen","ashen_gate","greyfen","vellum_hall"]
    beat_locations=[]
    for beat in spine["beats"]:
        if not beat_locations or beat_locations[-1]!=beat["location_ref"]:
            beat_locations.append(beat["location_ref"])
    if spine["logistics_plan"]["location_sequence"]!=expected or beat_locations!=expected:
        raise SafetyStop("F2_SPATIAL_CONTRACT_MISMATCH")
    return verified


def run(*, grant_file:Path, evidence_dir:Path, claim_dir:Path):
    grant=json.loads(grant_file.read_text(encoding="utf-8"))
    required={
        "schema":"lumi.v3-aion-f2-writer-paid-grant.v1",
        "authorized":True,
        "stage":"WRITER",
        "case_id":CASE_ID,
        "model":WRITER_MODEL,
        "frozen_runtime_sha":FROZEN_V3_SHA,
        "approved_spine_sha256":APPROVED_SHA256,
        "source_spine_run_id":SOURCE_SPINE_RUN_ID,
        "max_total_usd":"0.10",
    }
    if any(grant.get(k)!=v for k,v in required.items()):
        raise SafetyStop("F2_WRITER_GRANT_SCOPE_MISMATCH")
    if not isinstance(grant.get("human_paid_authorization_reference"),str) or not grant["human_paid_authorization_reference"].strip():
        raise SafetyStop("F2_WRITER_EXPLICIT_AUTHORIZATION_MISSING")
    uid=grant.get("grant_id")
    if not isinstance(uid,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",uid):
        raise SafetyStop("F2_WRITER_UNIQUE_GRANT_REQUIRED")
    try:
        ceiling=Decimal(str(grant["max_total_usd"]))
    except (TypeError,KeyError,InvalidOperation) as exc:
        raise SafetyStop("F2_WRITER_CEILING_INVALID") from exc
    if not ceiling.is_finite() or ceiling<=0 or ceiling>MAX_USD:
        raise SafetyStop("F2_WRITER_CEILING_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if grant.get("guard_commit_sha")!=head:
        raise SafetyStop("F2_WRITER_UNAPPROVED_GUARD_SHA")
    if subprocess.run(["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],check=False).returncode:
        raise SafetyStop("F2_WRITER_FROZEN_RUNTIME_ANCESTRY_INVALID")
    changes=set(subprocess.check_output(["git","diff","--name-only",FROZEN_V3_SHA,head],text=True).splitlines())
    if not changes or not changes.issubset(ALLOWED_SOURCE_CHANGES):
        raise SafetyStop("F2_WRITER_NON_GUARD_SOURCE_CHANGE")
    if subprocess.check_output(["git","status","--porcelain","--untracked-files=normal"],text=True).strip():
        raise SafetyStop("F2_WRITER_DIRTY_CHECKOUT")
    validate_source()
    if not claim_dir.is_absolute() or not evidence_dir.is_absolute():
        raise SafetyStop("F2_WRITER_ABSOLUTE_CLAIM_EVIDENCE_PATHS_REQUIRED")
    if evidence_dir.exists():
        raise SafetyStop("F2_WRITER_EVIDENCE_DIR_REUSE_FORBIDDEN")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("F2_WRITER_ACTIONS_SECRET_MISSING")
    claim_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    claim_hash=hashlib.sha256(("aion-f2-writer:"+uid).encode()).hexdigest()
    path=claim_dir/(claim_hash+".json")
    try:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError as exc:
        raise SafetyStop("F2_WRITER_GRANT_ALREADY_CONSUMED") from exc
    with os.fdopen(fd,"wb") as stream:
        stream.write((json.dumps({"schema":"lumi.v3-aion-f2-writer-claim.v1","grant_sha256":claim_hash,"guard_sha":head,"approved_sha":APPROVED_SHA256},sort_keys=True)+"\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    evidence_dir.mkdir(parents=True,mode=0o700)
    guard=SingleAttemptAionWriterGuard(evidence_dir,ceiling)
    guard.event("F2_WRITER_GRANT_VERIFIED",case_id=CASE_ID,
                approved_spine_sha256=APPROVED_SHA256,
                source_spine_run_id=SOURCE_SPINE_RUN_ID,model=WRITER_MODEL,
                planning_ceiling_usd=str(ceiling))
    try:
        with guard.installed_writer():
            result=generate(
                approved_path=APPROVED,prompt_path=PROMPT,
                out_path=evidence_dir/"writer-result.json",
                story_out_path=evidence_dir/"story-en.txt",
                api_key=os.environ["OPENROUTER_API_KEY"],
                authority_packet_version="v2",
            )
        guard.event("STAGE_FINISHED",status=result["status"],post_count=guard.calls,
                    accounted_cost_usd=str(guard.spent),next_stage_authorized=False)
        if result["status"]!="writer_generated":
            raise SafetyStop("F2_WRITER_DETERMINISTIC_CHECK_FAILED")
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP",error_type=type(exc).__name__,post_count=guard.calls,
                    accounted_cost_usd=str(guard.spent))
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--grant",type=Path,required=True)
    parser.add_argument("--claim-dir",type=Path,required=True)
    parser.add_argument("--evidence-dir",type=Path,required=True)
    args=parser.parse_args()
    result=run(grant_file=args.grant,claim_dir=args.claim_dir,evidence_dir=args.evidence_dir)
    print(json.dumps({"stage":"WRITER","model":WRITER_MODEL,
                      "status":result["status"],"next_stage_authorized":False}))
