"""Frozen-V3 F2 English -> Turkish literary translation and fidelity trial.

Two allowed provider POSTs in order: Gemini translation, then Luna fidelity.
If hard semantic findings occur, STOP before Luna. If Luna finds serious
meaning shifts, STOP, retaining both full original translation and audit.
No automatic retries, model substitutions, manual prose edits or publishing.
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

from src import v3_single_attempt_guard as guardmod
from src.deterministic_translation_semantic_guards import run_translation_semantic_guards
from src.episode_translation_v1 import (
    DEFAULT_MODEL as TRANSLATOR,
    run as frozen_translate,
)
from src.episode_fidelity_v1 import (
    DEFAULT_MODEL as FIDELITY,
    run as frozen_fidelity,
)
from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_guard import (
    FROZEN_V3_SHA, SafetyStop, SingleAttemptSpineGuard, _safe_cost,
)
from src.episode_translation_v1 import DEFAULT_PROMPT as TRANSLATE_PROMPT
from src.episode_fidelity_v1 import DEFAULT_PROMPT as FIDELITY_PROMPT

CASE_ID="age18.forbidden-cartographer.fantasy.frozen-01"
SOURCE_RUN=38712035968
WRITER_RUN=38703469212
TRANSLATION_MODELS=(TRANSLATOR,FIDELITY)
STORY=Path("evidence/v3-f2-final-luna-recheck-38712035968/english-quality-accepted.txt")
QUALIFICATION=Path("evidence/v3-f2-final-luna-recheck-38712035968/qualification.json")
APPROVED=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
SOURCE_SHA="990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8"
APPROVED_SHA="21f1e4e0c9f25cd1c970cccc2df8d09a0f236c9102321df7da086f85a3dac1a0"
MAX_CEILING=Decimal("0.15")
FROZEN_PARENT="ac3f27a8fb24e7e7cf1137212b97ad63594ebc05"
ALLOWED_CHANGED=frozenset({
    "experiments/v3_f2_turkish_translation_and_fidelity_once.py",
    "tests/test_v3_f2_turkish_translation_and_fidelity_once.py",
    "docs/qualifications/V3_F2_TURKISH_TRANSLATION_FIDELITY_20261015.md",
})


def file_sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class F2TranslationGuard(SingleAttemptSpineGuard):
    """Extends the proven one-post safety and accounting to frozen translation."""

    def event(self,kind,**kwargs):
        if kind=="GUARD_INSTALLED":
            kwargs.update(
                permitted_models=list(TRANSLATION_MODELS),
                provider_post_limit=2,
                attempts_per_model=1,
            )
        return super().event(kind,**kwargs)

    def _observed_translation(self,**kwargs):
        output=self._original_translation(**kwargs)
        _translation,body,_request=output
        if not isinstance(body,dict):
            raise SafetyStop("TRANSLATION_INVALID_PROVIDER_BODY")
        cost=_safe_cost(body)
        generation=body.get("id")
        if not isinstance(generation,str) or not generation.startswith("gen-"):
            raise SafetyStop("TRANSLATION_GENERATION_ID_MISSING")
        usage=body.get("usage") or {}
        self.event("PROVIDER_OBSERVED",call_number=self.calls,
                   model=kwargs.get("model"),generation_id=generation,
                   reported_cost_usd=str(cost),
                   input_tokens=usage.get("prompt_tokens"),
                   output_tokens=usage.get("completion_tokens"))
        self.spent+=cost
        if self.spent>self.max_cost:
            self.event("POLICY_STOP",reason="CUMULATIVE_COST_CEILING_REACHED",
                       observed_cost_usd=str(self.spent))
            raise SafetyStop("CUMULATIVE_COST_CEILING_REACHED")
        return output

    @contextmanager
    def installed_translation_and_fidelity(self):
        from src import episode_translation_v1 as t
        from src.storyforge import runtime as runtime
        self._original_translation=t.call_openrouter
        with patch.object(guardmod,"SPINE_MODELS",TRANSLATION_MODELS):
            with super().installed():
                with patch.object(t,"call_openrouter",self._observed_translation):
                    with patch.object(runtime,"call_structured_json_with_retry",
                                      self._no_parse_retry):
                        yield self


def preflight(*,grant_file:Path,claim_dir:Path,evidence_dir:Path):
    grant=json.loads(grant_file.read_text(encoding="utf-8"))
    expected={
        "schema":"lumi.v3-f2-english-to-turkish-grant.v1",
        "authorized":True,
        "stage":"TURKISH_TRANSLATION_FIDELITY",
        "case_id":CASE_ID,
        "source_quality_run_id":SOURCE_RUN,
        "source_english_sha256":SOURCE_SHA,
        "approved_spine_sha256":APPROVED_SHA,
        "frozen_runtime_sha":FROZEN_V3_SHA,
        "models":list(TRANSLATION_MODELS),
    }
    if any(grant.get(k)!=v for k,v in expected.items()):
        raise SafetyStop("TRANSLATION_GRANT_SCOPE_INVALID")
    gid=grant.get("grant_id")
    if not isinstance(gid,str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid) is None:
        raise SafetyStop("TRANSLATION_GRANT_ID_INVALID")
    authorizer=grant.get("human_paid_authorization_reference")
    if not isinstance(authorizer,str) or not authorizer.strip():
        raise SafetyStop("TRANSLATION_SEPARATE_PAID_APPROVAL_REQUIRED")
    try:
        ceiling=Decimal(str(grant["max_total_usd"]))
    except (KeyError,ValueError,TypeError,InvalidOperation) as exc:
        raise SafetyStop("TRANSLATION_CEILING_INVALID") from exc
    if not ceiling.is_finite() or not Decimal("0")<ceiling<=MAX_CEILING:
        raise SafetyStop("TRANSLATION_CEILING_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if grant.get("guard_commit_sha")!=head:
        raise SafetyStop("TRANSLATION_PINNED_GUARD_MISMATCH")
    if subprocess.run(["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],
                      check=False).returncode:
        raise SafetyStop("TRANSLATION_FROZEN_V3_ANCESTRY_INVALID")
    changed=set(subprocess.check_output(["git","diff","--name-only",FROZEN_PARENT,head],text=True).splitlines())
    if not changed or not changed.issubset(ALLOWED_CHANGED):
        raise SafetyStop("TRANSLATION_UNREVIEWED_SOURCE_CHANGE")
    if subprocess.check_output(["git","status","--porcelain","--untracked-files=normal"],text=True).strip():
        raise SafetyStop("TRANSLATION_DIRTY_CHECKOUT")
    frozen=verify_frozen_lane(PROFILE)
    if file_sha(STORY)!=SOURCE_SHA or file_sha(APPROVED)!=APPROVED_SHA:
        raise SafetyStop("TRANSLATION_SOURCE_HASH_MISMATCH")
    qualification=json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    if (qualification.get("status")!="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
        or qualification.get("accepted_story_sha256")!=SOURCE_SHA
        or qualification.get("source_writer_run")!=WRITER_RUN
        or qualification.get("source_quality_run")!=38709109136
        or qualification.get("translation_authorized") is not False
        or qualification.get("world_state_commit_authorized") is not False):
        raise SafetyStop("TRANSLATION_ENGLISH_MASTER_NOT_VERIFIED")
    approved=json.loads(APPROVED.read_text(encoding="utf-8"))
    if (approved.get("human_review",{}).get("verdict")!="APPROVE"
        or approved.get("gate",{}).get("decision")!="ACCEPT"):
        raise SafetyStop("TRANSLATION_SPINE_NOT_APPROVED")
    profile=json.loads(PROFILE.read_text(encoding="utf-8"))
    assert [profile["runtime"][x]["model"] for x in ("translation","fidelity")]==list(TRANSLATION_MODELS)
    if not TRANSLATE_PROMPT.is_file() or not FIDELITY_PROMPT.is_file():
        raise SafetyStop("FROZEN_PROMPTS_NOT_FOUND")
    if not claim_dir.is_absolute() or not evidence_dir.is_absolute():
        raise SafetyStop("TRANSLATION_CLAIM_PATHS_NOT_ABSOLUTE")
    if evidence_dir.exists():
        raise SafetyStop("TRANSLATION_EVIDENCE_DIR_REUSE")
    if os.getenv("LUMI_F2_TR_GLOBAL_CLAIM_VERIFIED")!="YES":
        raise SafetyStop("TRANSLATION_RUN_BOUND_GLOBAL_CLAIM_MISSING")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("TRANSLATION_ACTIONS_PROVIDER_SECRET_MISSING")
    return ceiling,gid,qualification,frozen


def run(*,grant_file:Path,claim_dir:Path,evidence_dir:Path):
    ceiling,gid,qualification,frozen=preflight(
        grant_file=grant_file,claim_dir=claim_dir,evidence_dir=evidence_dir
    )
    claim_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    token=hashlib.sha256(("f2-translation:"+gid).encode()).hexdigest()
    try:
        fd=os.open(claim_dir/(token+".json"),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise SafetyStop("TRANSLATION_GRANT_ALREADY_USED") from exc
    with os.fdopen(fd,"wb") as f:
        f.write((json.dumps({"schema":"lumi.v3-f2-translation-claim.v1",
                             "grant_sha256":token})+"\n").encode())
        f.flush()
        os.fsync(f.fileno())
    evidence_dir.mkdir(parents=True,mode=0o700)
    guard=F2TranslationGuard(evidence_dir,ceiling)
    guard.event("TRANSLATION_GRANT_VERIFIED",
                case_id=CASE_ID,source_sha256=SOURCE_SHA,
                frozen_verified=frozen["verified_files"],
                planning_ceiling_usd=str(ceiling))
    # This is merely a read-only compatibility envelope for the
    # preexisting frozen translator, not a fabricated model output.
    envelope={
        "schema_version":"f2-accepted-master-for-translation.v1",
        "accepted_english_master":STORY.read_text(encoding="utf-8").strip(),
        "source_quality_run_id":SOURCE_RUN,
        "original_sha256":SOURCE_SHA,
        "pipeline_usage_rollup":{"calls":[]},
        "next_stage_authorized":False,
    }
    source_path=evidence_dir/"accepted-master-source.json"
    with source_path.open("x",encoding="utf-8") as f:
        json.dump(envelope,f,ensure_ascii=False,indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    try:
        with guard.installed_translation_and_fidelity():
            tr=frozen_translate(
                source_path=source_path,approved_path=APPROVED,
                out_path=evidence_dir/"translation-result.json",
                tr_out_path=evidence_dir/"translation-tr.txt",
                api_key=os.environ["OPENROUTER_API_KEY"],
            )
            if tr["status"]!="semantic_guard_clean" or tr["translation_semantic_findings"]:
                raise SafetyStop("TRANSLATION_HARD_SEMANTIC_GUARDS_BLOCKED")
            if guard.calls!=1:
                raise SafetyStop("TRANSLATION_STAGE_CALL_COUNT_INVALID")
            fidelity=frozen_fidelity(
                source_path=evidence_dir/"translation-result.json",
                out_path=evidence_dir/"fidelity-result.json",
                api_key=os.environ["OPENROUTER_API_KEY"],
            )
        if guard.calls!=2:
            raise SafetyStop("FIDELITY_STAGE_CALL_COUNT_INVALID")
        if (fidelity["status"]!="clean"
            or fidelity.get("publication_ready") is not True
            or fidelity.get("deterministic_findings")
            or fidelity.get("fidelity_findings")
            or fidelity.get("confirmed_fidelity_findings")):
            raise SafetyStop("TURKISH_FIDELITY_FINDINGS_STOP")
        # We accept translation as a *quality-checked candidate* only;
        # no public release, no world state commit and no global promotion.
        result={
            "schema":"lumi.v3-f2.turkish-fidelity-qualification.v1",
            "status":"AUTOMATED_TURKISH_FIDELITY_CLEAN",
            "source_english_sha256":SOURCE_SHA,
            "translation_sha256":file_sha(evidence_dir/"translation-tr.txt"),
            "source_quality_run_id":SOURCE_RUN,
            "models":list(TRANSLATION_MODELS),
            "model_posts":guard.calls,
            "new_cost_usd":str(guard.spent),
            "semantic_guard_findings":0,
            "fidelity_findings":0,
            "human_text_edits":0,
            "translation_verified":True,
            "publication_authorized":False,
            "world_state_commit_authorized":False,
        }
        with (evidence_dir/"qualification.json").open("x",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        guard.event("STAGE_FINISHED",status=result["status"],model_posts=guard.calls,
                    observed_cost_usd=str(guard.spent),publication_authorized=False,
                    world_state_commit_authorized=False)
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP",exception_type=type(exc).__name__,
                    model_posts=guard.calls,observed_cost_usd=str(guard.spent))
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--grant",type=Path,required=True)
    parser.add_argument("--claim-dir",type=Path,required=True)
    parser.add_argument("--evidence-dir",type=Path,required=True)
    args=parser.parse_args()
    result=run(grant_file=args.grant,claim_dir=args.claim_dir,
               evidence_dir=args.evidence_dir)
    print(json.dumps({"status":result["status"],"models":result["models"],
                      "model_posts":result["model_posts"],
                      "publication_authorized":False},ensure_ascii=False))
