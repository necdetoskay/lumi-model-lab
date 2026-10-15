"""Resume exactly one final Luna recheck from real archived Luna/Sol results.

No repeated Luna initial audit, no repeated Sol model call, no manual repair.
Only the archived model-authored Sol replacement is mechanically applied.
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
from unittest.mock import patch

from experiments import v3_f2_autonomous_quality_probe as base
from src import v3_single_attempt_guard as guard_mod
from src.generate import count_words
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.storyforge.runtime import _apply_local_repairs, _normalize_audit
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SafetyStop, SingleAttemptSpineGuard
from src.v3_unattended_quality_model_adapter import CoherenceModelCallbacks
from src.v3_unattended_story_quality import (
    AUDIT_MODEL, AUDIT_INSTRUCTIONS, _model_patch_is_within_reported_quote,
    _safe_hard, QualityStop, fingerprint, _semantic_audit,
)

RUN=Path("evidence/v3-f2-autonomous-quality-38709109136")
LUNA_FILE=RUN/"model-01-initial_coherence_audit.json"
SOL_FILE=RUN/"model-02-bounded_model_repair.json"
LUNA_SHA="7d2a67f89372fe1c65868b8f3dd64dea946685c161536e0af2cc45af958ac189"
SOL_SHA="3865c48f43929da6f10b577a72a00d2d81cc0d7a4bee3219c74b3e775946d0b3"
SOURCE_QUALITY_RUN=38709109136
MAX_RECHECK_PLANNING_USD=Decimal("0.03")
EXTENDED_ALLOWLIST=base.ALLOWED_FILES | frozenset("""
.github/workflows/v3-f2-quality-recheck-once.yml
docs/qualifications/V3_F2_LIVE_LUNA_SOL_REPAIR_EVIDENCE_20261015.md
docs/qualifications/V3_F2_ONE_LUNA_RECHECK_20261015.md
experiments/v3_f2_quality_luna_recheck_probe.py
experiments/triggers/v3-f2-quality-recheck-offline-20261015.json
experiments/triggers/v3-f2-quality-recheck-once-20261015.json
src/v3_unattended_story_quality.py
tests/test_v3_real_model_repair_evidence.py
tests/test_v3_f2_quality_luna_recheck_probe.py
evidence/v3-f2-autonomous-quality-38709109136/001-quality_grant_verified.json
evidence/v3-f2-autonomous-quality-38709109136/002-guard_installed.json
evidence/v3-f2-autonomous-quality-38709109136/003-post_intent.json
evidence/v3-f2-autonomous-quality-38709109136/004-http_observed.json
evidence/v3-f2-autonomous-quality-38709109136/005-provider_observed.json
evidence/v3-f2-autonomous-quality-38709109136/006-post_intent.json
evidence/v3-f2-autonomous-quality-38709109136/007-http_observed.json
evidence/v3-f2-autonomous-quality-38709109136/008-provider_observed.json
evidence/v3-f2-autonomous-quality-38709109136/009-stage_stop.json
evidence/v3-f2-autonomous-quality-38709109136/model-01-initial_coherence_audit.json
evidence/v3-f2-autonomous-quality-38709109136/model-02-bounded_model_repair.json
""".split())


class SingleLunaRecheckGuard(SingleAttemptSpineGuard):
    def event(self, kind, **safe_fields):
        if kind=="GUARD_INSTALLED":
            safe_fields["permitted_models"]=[AUDIT_MODEL]
            safe_fields["provider_post_limit"]=1
            safe_fields["attempts_per_model"]=1
        return super().event(kind, **safe_fields)


def verify_recorded_model_evidence():
    """Build a new candidate using ORIGINAL story and REAL provider patches."""
    story,writer,approved,verified=base.verify_source()
    if (hashlib.sha256(LUNA_FILE.read_bytes()).hexdigest()!=LUNA_SHA
        or hashlib.sha256(SOL_FILE.read_bytes()).hexdigest()!=SOL_SHA):
        raise SafetyStop("ARCHIVED_MODEL_EVIDENCE_SHA_MISMATCH")
    a=json.loads(LUNA_FILE.read_text(encoding="utf-8"))
    b=json.loads(SOL_FILE.read_text(encoding="utf-8"))
    if (
        a.get("model")!="openai/gpt-5.6-luna"
        or a.get("call_number")!=1
        or a.get("generation_id")!="gen-1792054531-1njIAYUaOK7SoxqISQGb"
        or b.get("model")!="openai/gpt-5.6-sol"
        or b.get("call_number")!=2
        or b.get("generation_id")!="gen-1792054551-g29kkJqfM6xwTzjL5ZIY"
    ):
        raise SafetyStop("ARCHIVED_PROVIDER_GENERATIONS_INVALID")
    events=[json.loads(p.read_text()) for p in sorted(RUN.glob("[0-9][0-9][0-9]-*.json"))]
    provider=[e for e in events if e.get("kind")=="PROVIDER_OBSERVED"]
    intents=[e for e in events if e.get("kind")=="POST_INTENT"]
    if len(provider)!=2 or len(intents)!=2:
        raise SafetyStop("PRIOR_PAID_MODEL_POST_COUNT_INVALID")
    if any(provider[i].get("generation_id")!=p.get("generation_id")
           for i,p in enumerate((a,b))):
        raise SafetyStop("MODEL_EVIDENCE_GENERATION_MISMATCH")
    if not any(e.get("kind")=="STAGE_STOP" and e.get("model_posts")==2 for e in events):
        raise SafetyStop("PRIOR_STOP_EVIDENCE_MISSING")
    if any(e.get("kind")=="STAGE_FINISHED" for e in events):
        raise SafetyStop("PRIOR_WRONG_SUCCESS_EVIDENCE")
    prior_cost=sum(
        (Decimal(str(e["reported_cost_usd"])) for e in provider),
        Decimal("0"),
    )
    if prior_cost!=Decimal("0.0844978"):
        raise SafetyStop("PRIOR_MODEL_COST_MISMATCH")
    packet=build_story_authority_packet_v2(approved)
    hard, dismissed=_safe_hard(story,packet)
    findings=_normalize_audit(a["model_json"],segment_story(story))
    if hard or len(findings)!=1 or findings[0].get("repair_scope")!="local":
        raise SafetyStop("ARCHIVED_AUDIT_NOT_ONE_LOCAL_DEFECT")
    proposal=b["model_json"]
    rows=proposal.get("repairs")
    if not isinstance(rows,list) or len(rows)!=1:
        raise SafetyStop("ARCHIVED_SOL_REPAIR_COUNT_INVALID")
    row=rows[0]
    if (
        not isinstance(row.get("old"),str) or not isinstance(row.get("new"),str)
        or max(len(row["old"]),len(row["new"]))>250
        or abs(count_words(row["new"])-count_words(row["old"]))>25
        or not _model_patch_is_within_reported_quote(
            story=story,row=row,findings=findings,segments=segment_story(story)
        )
    ):
        raise SafetyStop("ARCHIVED_SOL_REPAIR_NOT_LOCAL")
    try:
        candidate,applied=_apply_local_repairs(story,proposal)
    except RuntimeError as exc:
        raise SafetyStop("ARCHIVED_SOL_PATCH_APPLICATION_UNSAFE") from exc
    if len(applied)!=1 or candidate==story:
        raise SafetyStop("ARCHIVED_SOL_REPAIR_DID_NOT_CHANGE_STORY")
    remaining,_=_safe_hard(candidate,packet)
    if remaining:
        raise SafetyStop("PRE_RECHECK_DETERMINISTIC_FINDINGS")
    return candidate,writer,approved,packet,prior_cost,verified


def preflight(*, grant_file:Path,evidence_dir:Path,claim_dir:Path):
    grant=json.loads(grant_file.read_text(encoding="utf-8"))
    required={
        "schema":"lumi.v3-f2-final-luna-recheck-grant.v1",
        "authorized":True,
        "stage":"ENGLISH_QUALITY_RECHECK",
        "case_id":base.CASE_ID,
        "source_writer_run_id":base.WRITER_RUN,
        "source_quality_run_id":SOURCE_QUALITY_RUN,
        "original_story_sha256":base.STORY_SHA,
        "archived_luna_sha256":LUNA_SHA,
        "archived_sol_sha256":SOL_SHA,
        "model":AUDIT_MODEL,
        "frozen_runtime_sha":FROZEN_V3_SHA,
    }
    if any(grant.get(k)!=v for k,v in required.items()):
        raise SafetyStop("RECHECK_GRANT_SCOPE_MISMATCH")
    if not isinstance(grant.get("human_paid_authorization_reference"),str) or not grant["human_paid_authorization_reference"].strip():
        raise SafetyStop("SEPARATE_LUNA_RECHECK_APPROVAL_REQUIRED")
    gid=grant.get("grant_id")
    if not isinstance(gid,str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid
    ):
        raise SafetyStop("RECHECK_UNIQUE_GRANT_REQUIRED")
    try:
        cap=Decimal(str(grant["max_total_usd"]))
    except (KeyError,TypeError,InvalidOperation) as exc:
        raise SafetyStop("RECHECK_CEILING_INVALID") from exc
    if not cap.is_finite() or not Decimal("0")<cap<=MAX_RECHECK_PLANNING_USD:
        raise SafetyStop("RECHECK_CEILING_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if grant.get("guard_commit_sha")!=head:
        raise SafetyStop("RECHECK_APPROVED_GUARD_COMMIT_MISMATCH")
    if subprocess.run([
        "git","merge-base","--is-ancestor",FROZEN_V3_SHA,head
    ],check=False).returncode!=0:
        raise SafetyStop("RECHECK_ORIGINAL_V3_ANCESTRY_INVALID")
    changed=set(subprocess.check_output([
        "git","diff","--name-only",FROZEN_V3_SHA,head
    ],text=True).splitlines())
    if not changed or not changed.issubset(EXTENDED_ALLOWLIST):
        raise SafetyStop("RECHECK_NON_GUARD_SOURCE_CHANGE")
    if subprocess.check_output([
        "git","status","--porcelain","--untracked-files=normal"
    ],text=True).strip():
        raise SafetyStop("RECHECK_DIRTY_CHECKOUT")
    candidate,writer,approved,packet,prior_cost,verified=verify_recorded_model_evidence()
    if not evidence_dir.is_absolute() or not claim_dir.is_absolute():
        raise SafetyStop("RECHECK_ABSOLUTE_EVIDENCE_CLAIM_REQUIRED")
    if evidence_dir.exists():
        raise SafetyStop("RECHECK_EVIDENCE_DIR_ALREADY_EXISTS")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("RECHECK_PROVIDER_SECRET_MISSING")
    if os.getenv("LUMI_RECHECK_GLOBAL_CLAIM_VERIFIED")!="YES":
        raise SafetyStop("RECHECK_GLOBAL_ONCE_CLAIM_NOT_VERIFIED")
    return cap,gid,candidate,approved,packet,prior_cost


def run(*,grant_file:Path,evidence_dir:Path,claim_dir:Path):
    cap,gid,candidate,approved,packet,prior_cost=preflight(
        grant_file=grant_file,evidence_dir=evidence_dir,claim_dir=claim_dir
    )
    claim_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    claim_hash=hashlib.sha256(("luna-recheck:"+gid).encode()).hexdigest()
    try:
        fd=os.open(claim_dir/(claim_hash+".json"),
                   os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise SafetyStop("RECHECK_GRANT_ALREADY_CONSUMED") from exc
    with os.fdopen(fd,"wb") as f:
        f.write((json.dumps({"schema":"lumi.v3-final-recheck-claim.v1",
                             "grant_sha256":claim_hash})+"\n").encode())
        f.flush()
        os.fsync(f.fileno())
    evidence_dir.mkdir(parents=True,mode=0o700)
    guard=SingleLunaRecheckGuard(evidence_dir,cap)
    adapter=CoherenceModelCallbacks(
        api_key=os.environ["OPENROUTER_API_KEY"],
        approved=approved,
        evidence_dir=evidence_dir,
    )
    # Two initial paid model responses are immutable historical evidence.
    # Only the third LOGICAL model stage is a NEW, single billable POST.
    adapter.stage_index=2
    guard.event("RECHECK_GRANT_VERIFIED",
                prior_quality_run=SOURCE_QUALITY_RUN,
                prior_spend_usd=str(prior_cost),
                archived_luna_sha256=LUNA_SHA,
                archived_sol_sha256=SOL_SHA,
                candidate_sha256=fingerprint(candidate),
                new_max_planning_usd=str(cap))
    try:
        with patch.object(guard_mod,"SPINE_MODELS",(AUDIT_MODEL,)):
            with guard.installed():
                findings=_semantic_audit(candidate,packet,adapter.audit)
        if findings:
            raise QualityStop("REAL_LUNA_RECHECK_FOUND_BLOCKING_DEFECT")
        if guard.calls!=1 or len(adapter.events)!=1:
            raise SafetyStop("REAL_LUNA_RECHECK_CALL_EVIDENCE_MISMATCH")
        if adapter.events[0]["stage"]!="post_repair_coherence_reaudit":
            raise SafetyStop("WRONG_RECHECK_MODEL_STAGE")
        original=base.STORY.read_text(encoding="utf-8")
        if original==candidate:
            raise SafetyStop("RECHECK_SOURCE_WAS_NOT_MODEL_REPAIRED")
        # Save accepted ENGLISH DRAFT only AFTER an actual real Luna PASS.
        with (evidence_dir/"english-quality-accepted.txt").open(
            "x",encoding="utf-8"
        ) as f:
            f.write(candidate)
            f.flush()
            os.fsync(f.fileno())
        result={
            "schema":"lumi.v3.autonomous-english-quality-acceptance.v1",
            "status":"AUTOMATED_ENGLISH_COHERENCE_ACCEPTED",
            "source_writer_run":base.WRITER_RUN,
            "source_quality_run":SOURCE_QUALITY_RUN,
            "final_luna_generation_id":adapter.events[0]["generation_id"],
            "accepted_story_sha256":fingerprint(candidate),
            "original_story_sha256":base.STORY_SHA,
            "word_count":count_words(candidate),
            "length_warning":True,
            "length_blocking":False,
            "model_authored_local_edits":1,
            "live_recheck_calls":1,
            "new_recheck_cost_usd":str(guard.spent),
            "prior_audit_repair_cost_usd":str(prior_cost),
            "no_manual_story_edit":True,
            "translation_authorized":False,
            "world_state_commit_authorized":False,
        }
        with (evidence_dir/"qualification.json").open(
            "x",encoding="utf-8"
        ) as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        guard.event("STAGE_FINISHED",status=result["status"],
                    provider_posts=1,
                    reported_cost_usd=str(guard.spent),
                    translation_authorized=False,
                    world_state_commit_authorized=False)
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP",
                    exception_type=type(exc).__name__,
                    model_posts=guard.calls,
                    reported_cost_usd=str(guard.spent))
        raise


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--grant",type=Path,required=True)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--claim-dir",type=Path,required=True)
    args=p.parse_args()
    result=run(grant_file=args.grant,
               evidence_dir=args.evidence_dir,claim_dir=args.claim_dir)
    print(json.dumps({
        "status":result["status"],
        "recheck_model":AUDIT_MODEL,
        "model_post_count":1,
        "length_warning":True,
        "translation_authorized":False,
    }))
