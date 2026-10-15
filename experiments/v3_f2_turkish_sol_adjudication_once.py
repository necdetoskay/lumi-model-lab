"""One guarded Sol adjudication of archived, real Luna translation findings.

No human fixes. If ALL flagged meaning shifts are rejected, raw Gemini
translation can be accepted; confirmed defects STOP before any repair.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,subprocess
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from src import v3_single_attempt_guard as base
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SafetyStop,SingleAttemptSpineGuard
from src.frozen_lane_verify import verify_frozen_lane
from src.episode_fidelity_adjudication_v1 import run as sol_adjudicate,DEFAULT_MODEL
from src.deterministic_translation_semantic_guards import run_translation_semantic_guards

ROOT=Path("evidence/v3-f2-turkish-luna-findings-38713969969")
LUNA=ROOT/"fidelity-result.json"
GEMINI=ROOT/"translation-result.json"
TURKISH=ROOT/"translation-tr.txt"
ENGLISH=Path("evidence/v3-f2-final-luna-recheck-38712035968/english-quality-accepted.txt")
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
ROOT_BASE="ffd3e88f6374179c816c1bd78a305cbb69e9edf6"
MODEL="openai/gpt-5.6-sol"
MAX_COST=Decimal("0.12")
EXPECTED={
 LUNA:"40cf924ce239050fd9ed046f3d9199af0f262c57d0296cf44cc4a8ab918be591",
 GEMINI:"6df79265c14040e050a6cdf5f3c781d58069faa489b7b8074978ee9f08549a8d",
 TURKISH:"a163d9cbde430bd2023bb9e673d0e8ff4b380c7567aa84c4b476252dd2ddca19",
 ENGLISH:"990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8",
}
ALLOWED={
 "experiments/v3_f2_turkish_sol_adjudication_once.py",
 "tests/test_v3_f2_turkish_sol_adjudication_once.py",
 "docs/qualifications/V3_F2_TURKISH_SOL_ADJUDICATION_20261015.md",
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Guard(SingleAttemptSpineGuard):
    def event(self,kind,**fields):
        if kind=="GUARD_INSTALLED":
            fields.update(permitted_models=[MODEL],provider_post_limit=1,attempts_per_model=1)
        return super().event(kind,**fields)

    @contextmanager
    def installed_sol(self):
        from src.storyforge import runtime
        with patch.object(base,"SPINE_MODELS",(MODEL,)):
            with super().installed():
                with patch.object(runtime,"call_structured_json_with_retry",self._no_parse_retry):
                    yield self

def verify_sources():
    frozen=verify_frozen_lane(PROFILE)
    if any(sha(p)!=expected for p,expected in EXPECTED.items()):
        raise SafetyStop("SOL_ARCHIVED_SOURCE_SHA_CHANGED")
    luna=json.loads(LUNA.read_text())
    gemini=json.loads(GEMINI.read_text())
    findings=luna.get("fidelity_findings") or []
    if (luna.get("status")!="findings_need_adjudication"
        or len(findings)!=3 or luna.get("fidelity_model")!="openai/gpt-5.6-luna"
        or gemini.get("status")!="semantic_guard_clean"
        or gemini.get("translation_model")!="google/gemini-3.8-flash"
        or gemini["translation_semantic_findings"]
        or luna["accepted_english_master"]!=gemini["accepted_english_master"]
        or luna["turkish_delivery"]!=gemini["turkish_delivery"]
        or luna["turkish_delivery"].strip()!=TURKISH.read_text().strip()
        or luna["accepted_english_master"].strip()!=ENGLISH.read_text().strip()):
        raise SafetyStop("SOL_ARCHIVED_LUNA_GEMINI_MISMATCH")
    return frozen,luna,gemini

def preflight(grant_file,claim_dir,evidence_dir):
    grant=json.loads(grant_file.read_text())
    required={
        "schema":"lumi.v3-f2-tr-sol-adjudication-grant.v1",
        "authorized":True,
        "stage":"TR_FIDELITY_ADJUDICATION",
        "case_id":"age18.forbidden-cartographer.fantasy.frozen-01",
        "source_run_id":38713969969,
        "source_luna_sha256":EXPECTED[LUNA],
        "source_turkish_sha256":EXPECTED[TURKISH],
        "model":MODEL,
        "frozen_runtime_sha":FROZEN_V3_SHA,
    }
    if any(grant.get(k)!=value for k,value in required.items()):
        raise SafetyStop("SOL_GRANT_SCOPE_MISMATCH")
    gid=grant.get("grant_id")
    if not isinstance(gid,str) or not re.fullmatch("[A-Za-z0-9][A-Za-z0-9_-]{7,79}",gid):
        raise SafetyStop("SOL_GRANT_ID_INVALID")
    ref=grant.get("human_paid_authorization_reference")
    if not isinstance(ref,str) or not ref.strip():
        raise SafetyStop("SOL_SEPARATE_PERMISSION_REQUIRED")
    try:cap=Decimal(str(grant["max_total_usd"]))
    except Exception as exc:raise SafetyStop("SOL_BUDGET_INVALID") from exc
    if not cap.is_finite() or not Decimal("0")<cap<=MAX_COST:
        raise SafetyStop("SOL_BUDGET_INVALID")
    head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if grant.get("guard_commit_sha")!=head:
        raise SafetyStop("SOL_GUARD_SHA_MISMATCH")
    if subprocess.run(["git","merge-base","--is-ancestor",FROZEN_V3_SHA,head],check=False).returncode:
        raise SafetyStop("SOL_FROZEN_SOURCE_ANCESTRY_INVALID")
    diff=set(subprocess.check_output(["git","diff","--name-only",ROOT_BASE,head],text=True).splitlines())
    if not diff or not diff.issubset(ALLOWED):
        raise SafetyStop("SOL_UNREVIEWED_SOURCE_CHANGE")
    if subprocess.check_output(["git","status","--porcelain","--untracked-files=normal"],text=True).strip():
        raise SafetyStop("SOL_DIRTY_CHECKOUT")
    frozen,luna,gemini=verify_sources()
    if not claim_dir.is_absolute() or not evidence_dir.is_absolute() or evidence_dir.exists():
        raise SafetyStop("SOL_EVIDENCE_CLAIM_PATHS_INVALID")
    if os.getenv("LUMI_TR_SOL_GLOBAL_CLAIM_VERIFIED")!="YES":
        raise SafetyStop("SOL_GLOBAL_RUN_CLAIM_NOT_VERIFIED")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("SOL_PROVIDER_SECRET_NOT_INJECTED")
    return cap,gid,luna

def run(*,grant_file,claim_dir,evidence_dir):
    cap,gid,luna=preflight(grant_file,claim_dir,evidence_dir)
    claim_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
    hash_id=hashlib.sha256(("tr-sol-adjudication:"+gid).encode()).hexdigest()
    try:fd=os.open(claim_dir/(hash_id+".json"),os.O_WRONLY|os.O_EXCL|os.O_CREAT,0o600)
    except FileExistsError as exc:raise SafetyStop("SOL_GRANT_ALREADY_CONSUMED") from exc
    with os.fdopen(fd,"w") as f:
        json.dump({"schema":"tr-sol-claim.v1","digest":hash_id},f)
        f.flush();os.fsync(f.fileno())
    evidence_dir.mkdir(mode=0o700,parents=True)
    guard=Guard(evidence_dir,cap)
    guard.event("SOL_ADJUDICATION_GRANT_VERIFIED",source_run=38713969969,
                source_luna_sha256=EXPECTED[LUNA],cap_usd=str(cap))
    try:
        with guard.installed_sol():
            adjudicated=sol_adjudicate(
                source_path=LUNA,
                out_path=evidence_dir/"sol-adjudication.json",
                api_key=os.environ["OPENROUTER_API_KEY"],
            )
        if guard.calls!=1:raise SafetyStop("SOL_PROVIDER_POST_COUNT_INVALID")
        confirmed=adjudicated["confirmed_fidelity_findings"]
        if adjudicated["status"]=="clean_after_adjudication" and not confirmed:
            if run_translation_semantic_guards(ENGLISH.read_text(),TURKISH.read_text()):
                raise SafetyStop("TR_SEMANTIC_GUARDS_STILL_BLOCKING")
            out=evidence_dir/"turkish-quality-accepted.txt"
            with out.open("x",encoding="utf-8") as f:
                f.write(TURKISH.read_text());f.flush();os.fsync(f.fileno())
            status="AUTOMATED_TURKISH_FIDELITY_ACCEPTED"
        elif adjudicated["status"]=="confirmed_fidelity_findings" and confirmed:
            status="CONFIRMED_FINDINGS_AWAIT_MODEL_REPAIR"
        else:raise SafetyStop("SOL_ADJUDICATION_CONTRACT_MISMATCH")
        final={
            "status":status,"model":MODEL,"model_posts":guard.calls,
            "confirmed_findings":len(confirmed),
            "observed_cost_usd":str(guard.spent),
            "turkish_accepted":status=="AUTOMATED_TURKISH_FIDELITY_ACCEPTED",
            "manual_text_edits":0,
            "publication_authorized":False,"world_state_commit_authorized":False,
        }
        with (evidence_dir/"adjudication-outcome.json").open("x",encoding="utf-8") as f:
            json.dump(final,f,ensure_ascii=False,indent=2)
            f.write("\n");f.flush();os.fsync(f.fileno())
        guard.event("STAGE_FINISHED",status=status,confirmed_findings=len(confirmed),
                    model_posts=1,cost_usd=str(guard.spent))
        return final
    except BaseException as exc:
        guard.event("STAGE_STOP",exception_type=type(exc).__name__,
                    model_posts=guard.calls,cost_usd=str(guard.spent))
        raise

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--grant",type=Path,required=True)
    parser.add_argument("--claim-dir",type=Path,required=True)
    parser.add_argument("--evidence-dir",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(grant_file=args.grant,claim_dir=args.claim_dir,
                         evidence_dir=args.evidence_dir),ensure_ascii=False))
