"""Run bounded Luna -> optional Sol -> Luna without ANY human story edit.

Paid execution requires new, separately scoped consent plus globally run-bound
one-use claim before this entrypoint. Never use old Writer/Spine authorization.
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

from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SafetyStop
from src.v3_unattended_quality_model_adapter import (
    CoherenceModelCallbacks, CoherenceSequenceGuard, SEQUENCE,
)
from src.v3_unattended_story_quality import QualityStop, qualify

ROOT = Path("evidence/v3-f2-aion-writer-38703469212")
STORY = ROOT / "story-en.txt"
WRITER_RESULT = ROOT / "writer-result.json"
APPROVED = Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f2_approved_for_aion_20261015.json"
)
PROFILE = Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
CASE_ID = "age18.forbidden-cartographer.fantasy.frozen-01"
SPINE_RUN = 38700326961
WRITER_RUN = 38703469212
STORY_SHA = "eb38aea3c43a9e59d748ee0cf6f53475bfaf1d4c412c46e0893c78ccc3874eeb"
WRITER_SHA = "7b92a7f3ebda02b70dbf9d45eab72dfdf35657b3411b1b2cbe198c26287758b0"
APPROVED_SHA = "21f1e4e0c9f25cd1c970cccc2df8d09a0f236c9102321df7da086f85a3dac1a0"
MAX_ADMISSION_CEILING = Decimal("0.20")

# Exact frozen branch to experiment-head delta must contain ONLY listed external
# files. Changes to any 43 frozen source files are forbidden.
ALLOWED_FILES = frozenset("""
.github/workflows/v3-f2-aion-writer-once.yml
.github/workflows/v3-f2-quality-one-attempt.yml
data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json
docs/qualifications/V3_AION_F2_WRITER_QUALIFICATION_20261015.md
docs/qualifications/V3_AION_MINI_WRITER_SINGLE_ATTEMPT.md
docs/qualifications/V3_AUTONOMOUS_COHERENCE_REPAIR_POLICY_20261015.md
docs/qualifications/V3_F2_AION_WRITER_FAILURE_EVIDENCE_20261015.json
docs/qualifications/V3_F2_AION_WRITER_FAILURE_REVIEW_20261015.md
docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_GUARD_V1.md
docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_LIVE_WORKFLOW_TEMPLATE.yml
evidence/v3-f2-aion-writer-38703469212/001-f2_writer_grant_verified.json
evidence/v3-f2-aion-writer-38703469212/002-guard_installed.json
evidence/v3-f2-aion-writer-38703469212/003-post_intent.json
evidence/v3-f2-aion-writer-38703469212/004-http_observed.json
evidence/v3-f2-aion-writer-38703469212/005-provider_observed.json
evidence/v3-f2-aion-writer-38703469212/006-stage_finished.json
evidence/v3-f2-aion-writer-38703469212/007-stage_stop.json
evidence/v3-f2-aion-writer-38703469212/story-en.txt
evidence/v3-f2-aion-writer-38703469212/writer-result.json
experiments/triggers/v3-f2-aion-writer-offline-20261015.json
experiments/triggers/v3-f2-aion-writer-once-20261015.json
experiments/triggers/v3-f2-quality-offline-20261015.json
experiments/triggers/v3-f2-quality-once-20261015.json
experiments/v3_aion_f2_writer_single_attempt_probe.py
experiments/v3_aion_writer_single_attempt_probe.py
experiments/v3_f2_autonomous_quality_probe.py
experiments/v3_single_attempt_spine_probe.py
src/v3_single_attempt_aion_writer_guard.py
src/v3_single_attempt_guard.py
src/v3_unattended_quality_model_adapter.py
src/v3_unattended_story_quality.py
tests/test_v3_aion_f2_writer_single_attempt_probe.py
tests/test_v3_f2_autonomous_quality_probe.py
tests/test_v3_single_attempt_aion_writer_guard.py
tests/test_v3_single_attempt_guard.py
tests/test_v3_unattended_quality_model_adapter.py
tests/test_v3_unattended_story_quality.py
""".split())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_source():
    frozen = verify_frozen_lane(PROFILE)
    for path, required_sha in (
        (STORY, STORY_SHA), (WRITER_RESULT, WRITER_SHA),
        (APPROVED, APPROVED_SHA),
    ):
        if sha(path.read_bytes()) != required_sha:
            raise SafetyStop("ORIGINAL_STORY_OR_SPINE_SOURCE_CHANGED")
    story=STORY.read_text(encoding="utf-8")
    writer=json.loads(WRITER_RESULT.read_text(encoding="utf-8"))
    approved=json.loads(APPROVED.read_text(encoding="utf-8"))
    if (writer.get("source_spine_run_id")!=SPINE_RUN
        or writer.get("writer_model")!="aion-labs/aion-3.5-mini"
        or writer.get("status")!="writer_generated_deterministic_check_failed"
        or writer.get("next_stage_authorized") is not False
        or writer.get("story","").strip()!=story.strip()
        or approved.get("source_run_id")!=SPINE_RUN
        or (approved.get("human_review") or {}).get("verdict")!="APPROVE"
        or (approved.get("gate") or {}).get("decision")!="ACCEPT"):
        raise SafetyStop("AUTHORITATIVE_WRITER_SPINE_LINK_INVALID")
    return story,writer,approved,frozen


def validate_grant(grant_file: Path, claim_dir: Path, evidence_dir: Path):
    grant=json.loads(grant_file.read_text(encoding="utf-8"))
    required={
        "schema":"lumi.v3-f2-autonomous-quality-grant.v1",
        "authorized":True,
        "stage":"ENGLISH_QUALITY",
        "case_id":CASE_ID,
        "writer_run_id":WRITER_RUN,
        "spine_run_id":SPINE_RUN,
        "frozen_runtime_sha":FROZEN_V3_SHA,
        "story_sha256":STORY_SHA,
        "approved_spine_sha256":APPROVED_SHA,
        "models":list(SEQUENCE),
    }
    if any(grant.get(k)!=value for k,value in required.items()):
        raise SafetyStop("QUALITY_GRANT_SCOPE_MISMATCH")
    reference=grant.get("human_paid_authorization_reference")
    if not isinstance(reference,str) or not reference.strip():
        raise SafetyStop("SEPARATE_PAID_QUALITY_AUTHORIZATION_REQUIRED")
    gid=grant.get("grant_id")
    if not isinstance(gid,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid) is None:
        raise SafetyStop("QUALITY_UNIQUE_GRANT_ID_REQUIRED")
    try:
        cap=Decimal(str(grant["max_total_usd"]))
    except (KeyError, InvalidOperation,TypeError) as exc:
        raise SafetyStop("QUALITY_CEILING_INVALID") from exc
    if not cap.is_finite() or cap<=0 or cap>MAX_ADMISSION_CEILING:
        raise SafetyStop("QUALITY_CEILING_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if grant.get("guard_commit_sha")!=head:
        raise SafetyStop("QUALITY_GUARD_COMMIT_MISMATCH")
    if subprocess.run(
        ["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],
        check=False,
    ).returncode:
        raise SafetyStop("QUALITY_FROZEN_ANCESTRY_INVALID")
    changed=set(subprocess.check_output(
        ["git","diff","--name-only",FROZEN_V3_SHA,head],text=True,
    ).splitlines())
    if not changed or not changed.issubset(ALLOWED_FILES):
        raise SafetyStop("QUALITY_NON_GUARD_FILE_CHANGED")
    if subprocess.check_output([
        "git","status","--porcelain","--untracked-files=normal"
    ],text=True).strip():
        raise SafetyStop("QUALITY_DIRTY_CHECKOUT")
    story,writer,approved,frozen=verify_source()
    if not claim_dir.is_absolute() or not evidence_dir.is_absolute():
        raise SafetyStop("QUALITY_EVIDENCE_PATHS_NOT_ABSOLUTE")
    if evidence_dir.exists():
        raise SafetyStop("QUALITY_EVIDENCE_DIRECTORY_ALREADY_EXISTS")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("QUALITY_OPENROUTER_SECRET_MISSING")
    # GitHub Actions must check an externally committed globally unique claim
    # tied to run ID, run attempt 1 and current triggering commit BEFORE here.
    # This local process adds a second durable claim before any provider POST.
    if os.getenv("LUMI_QUALITY_GLOBAL_CLAIM_VERIFIED")!="YES":
        raise SafetyStop("QUALITY_GLOBAL_RUN_CLAIM_NOT_VERIFIED")
    return cap,gid,story,writer,approved


def run(*, grant_file: Path, evidence_dir: Path, claim_dir: Path):
    cap,gid,story,writer,approved=validate_grant(grant_file,claim_dir,evidence_dir)
    claim_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    claim_hash=sha(("quality:"+gid).encode())
    try:
        fd=os.open(claim_dir/(claim_hash+".json"),
                   os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise SafetyStop("QUALITY_GRANT_ALREADY_USED") from exc
    with os.fdopen(fd,"wb") as f:
        f.write((json.dumps({"schema":"lumi.v3-quality-once-claim.v1",
              "claim_sha256":claim_hash,
              "guard_sha":subprocess.check_output(
                  ["git","rev-parse","HEAD"],text=True).strip()})+"\n").encode())
        f.flush()
        os.fsync(f.fileno())
    evidence_dir.mkdir(parents=True,mode=0o700)
    guard=CoherenceSequenceGuard(evidence_dir,cap)
    model=CoherenceModelCallbacks(
        api_key=os.environ["OPENROUTER_API_KEY"],
        approved=approved,evidence_dir=evidence_dir,
    )
    guard.event("QUALITY_GRANT_VERIFIED",case_id=CASE_ID,
                story_sha256=STORY_SHA,spine_sha256=APPROVED_SHA,
                source_writer_run_id=WRITER_RUN,
                max_planning_usd=str(cap))
    try:
        with guard.installed_sequence():
            result=qualify(
                story=story,writer_result=writer,approved=approved,
                audit=model.audit,repair=model.repair,
            )
        if result["status"]!="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED":
            raise SafetyStop("QUALITY_FINAL_STATUS_NOT_ACCEPTED")
        if guard.calls!=len(model.events):
            raise SafetyStop("QUALITY_PROVIDER_EVIDENCE_MISMATCH")
        if guard.calls not in (1,3):
            raise SafetyStop("QUALITY_STAGE_COUNT_INVALID")
        # Only after all model findings and rechecks pass do we publish a
        # NEW output file. The original Aion Writer result is immutable.
        accepted=result.pop("accepted_english_story")
        path=evidence_dir/"english-quality-accepted.txt"
        with path.open("x",encoding="utf-8") as f:
            f.write(accepted)
            f.flush()
            os.fsync(f.fileno())
        result["accepted_story_path"]=path.name
        result["observed_cost_usd"]=str(guard.spent)
        result["model_calls"]=guard.calls
        with (evidence_dir/"qualification.json").open(
            "x",encoding="utf-8"
        ) as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        guard.event("STAGE_FINISHED",status=result["status"],
                    model_posts=guard.calls,reported_cost_usd=str(guard.spent),
                    translation_authorized=False,
                    world_state_commit_authorized=False)
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP",exception_type=type(exc).__name__,
                    model_posts=guard.calls,reported_cost_usd=str(guard.spent))
        raise


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--grant",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--claim-dir",type=Path,required=True)
    options=p.parse_args()
    result=run(grant_file=options.grant,
               evidence_dir=options.evidence_dir,claim_dir=options.claim_dir)
    print(json.dumps({
        "status":result["status"],"model_calls":result["model_calls"],
        "length_warning":result["length_warning"],
        "translation_authorized":False,
        "world_state_commit_authorized":False,
    },ensure_ascii=False))
