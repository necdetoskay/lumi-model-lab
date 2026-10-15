"""One-use paid FULL V4 EN->TR Mara case, detached from V3.

The grant must be explicit, version-bound, commit-bound, and consumed before
the first paid model call. The provider ledger accounts for failures too.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from decimal import Decimal
from pathlib import Path

from src.v4_full_pipeline import run as run_pipeline
from src.v4_paid_guard import V4PaidStop, V4ProviderLedger, verify_v4_source_pin
from src.story_stage_common import write_json

SCHEMA="lumi.v4.one-case-full-en-tr-once.v1"
CASE_ID="age18.closed-platform.mystery.stress-01"
CASE_PATH="data/specifications/story_lab/four_genre_v3_inputs/closed_platform_case_manifest_v4.json"
REFERENCE="user approved 2026-10-15: build V4 then replay Mara story through complete EN-TR line"
STAGE="FULL_EN_TR"
OBSERVED_SPEND_LIMIT="2.00"
MAX_POSTS=12


def validate(grant:dict)->None:
    fixed={
        "schema":SCHEMA,"authorized":True,"stage":STAGE,
        "case_id":CASE_ID,"case_manifest":CASE_PATH,
        "runtime_revision":"AGE18-V4-DERIVED-LOGISTICS-v1",
        "observed_spend_stop_usd":OBSERVED_SPEND_LIMIT,
        "maximum_provider_posts":MAX_POSTS,
        "client_output_token_limit":None,
        "human_review_fabrication":False,
        "no_manual_repairs":True,
        "no_world_commit":True,
        "no_publication":True,
        "reference":REFERENCE,
    }
    if any(grant.get(k)!=v for k,v in fixed.items()):
        raise V4PaidStop("V4_GRANT_SCOPE_INVALID")
    if not isinstance(grant.get("grant_id"),str) or not re.fullmatch(r"[A-Za-z0-9_-]{12,80}",grant["grant_id"]):
        raise V4PaidStop("V4_GRANT_ID_INVALID")
    if not isinstance(grant.get("approved_code_sha"),str) or not re.fullmatch("[0-9a-f]{40}",grant["approved_code_sha"]):
        raise V4PaidStop("V4_APPROVED_SOURCE_SHA_INVALID")


def run(*,grant_path:Path,claim_dir:Path,evidence_dir:Path)->dict:
    grant=json.loads(grant_path.read_text(encoding="utf-8"))
    validate(grant)
    verify_v4_source_pin(grant["approved_code_sha"])
    if not os.getenv("OPENROUTER_API_KEY"):
        raise V4PaidStop("OPENROUTER_API_KEY_MISSING")
    if not claim_dir.is_absolute() or not evidence_dir.is_absolute() or evidence_dir.exists():
        raise V4PaidStop("V4_DURABLE_DIR_INVALID")
    claim_dir.mkdir(parents=True,exist_ok=True)
    name=hashlib.sha256(grant["grant_id"].encode()).hexdigest()
    claim=claim_dir/(name+".json")
    fd=os.open(claim,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump({"grant_id_sha256":name,"approved_code_sha":grant["approved_code_sha"]},f)
        f.flush();os.fsync(f.fileno())
    evidence_dir.mkdir(parents=True)
    ledger=V4ProviderLedger(evidence_dir=evidence_dir/"provider_events",
                            max_reported_usd=Decimal(OBSERVED_SPEND_LIMIT))
    try:
        with ledger.installed():
            result=run_pipeline(case_manifest=Path(CASE_PATH),
                                out_dir=evidence_dir/"full_line",paid_authorized=True)
        merged={**result,**ledger.summary(),"status":result["status"]}
        write_json(evidence_dir/"verified_result.json",merged)
        return merged
    except BaseException as exc:
        write_json(evidence_dir/"stopped.json",{
            "status":"FAILED_NO_PUBLICATION",
            "reason_type":type(exc).__name__,"reason":str(exc)[:600],
            **ledger.summary(),"no_automatic_external_retry":True,
            "previous_v3_claim_reused":False,
        })
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--grant",required=True,type=Path)
    p.add_argument("--claim-dir",required=True,type=Path)
    p.add_argument("--evidence-dir",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(run(grant_path=args.grant,claim_dir=args.claim_dir,
                         evidence_dir=args.evidence_dir),ensure_ascii=False))


if __name__=="__main__":
    main()
