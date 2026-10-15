"""Frozen 10-story Harness driver: one shared model profile, no retries/fixes.

GitHub workflow_dispatch is the only paid entrypoint. Default CLI can run a
complete local OFFLINE mock rehearsal. A claimed ACCEPT is *not* independent
literary release acceptance. No production state writes.

The $20 ceiling applies to this LUMI study, including a conservative historic
LUMI hold. A shared inference API key has other consumers; this application
ledger cannot guarantee OpenRouter account-wide spending bounds.
"""
from __future__ import annotations

import argparse
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from src.story_harness_cohort_pipeline_v1 import (
    STAGE_MAX, ProviderCostUnknown, run_one_case_with_injected_transport)
from src.story_harness_cohort_generation_receipt_v1 import read_and_verify_generation
from src.story_harness_frozen_cohort_v1 import (
    IDS, CAP, TRIAL_CAP, DOCUMENTED_RESERVATION)
from src.story_harness_frozen_round_v1 import simulate_seal, check_lock
from src.story_harness_runtime_v1 import create_harness
from src.story_harness_p417_live_pilot import https_post_once
from src.story_harness_p414 import read_current_key, money as provider_key_money
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-frozen-batch-runner.v1"
RUN_ID = "baseline-v1"
PAID_CONFIRMATION = "AUTHORIZE_LUMI_TEN_NO_RETRY_4_40_RESERVE_20_TOTAL"
BRANCH = "refs/heads/experiment/story-harness-control-plane-v1"
ACTOR = "necdetoskay"
ORDER = ("SPINEFORGE", "WRITER", "QUALITY", "Q25")

def require(ok, why):
    if not ok: raise HarnessStop("COHORT_BATCH_STOP_" + why)

def usd(value):
    require(type(value) is str and 0 < len(value) <= 25, "BAD_CURRENCY")
    try: money = Decimal(value)
    except Exception: raise HarnessStop("COHORT_BATCH_STOP_INVALID_USD") from None
    require(money.is_finite() and money >= 0 and money.as_tuple().exponent >= -6,
            "INVALID_USD")
    return money

def write_new(path, payload):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical_json(payload)+b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    par = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(par)
    finally: os.close(par)

def head(repo):
    result = subprocess.run(["git","rev-parse","HEAD"],cwd=str(repo),
                            capture_output=True,text=True,timeout=5)
    require(result.returncode == 0 and
            re.fullmatch("[a-f0-9]{40}",result.stdout.strip()) is not None,
            "HEAD_UNAVAILABLE")
    return result.stdout.strip()

def authorize_paid(repo):
    """No paid transport callable exists outside manual exact-SHA GH job."""
    require(os.getenv("GITHUB_ACTIONS") == "true" and
            os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch" and
            os.getenv("GITHUB_REF") == BRANCH and
            os.getenv("GITHUB_ACTOR") == ACTOR and
            os.getenv("GITHUB_SHA") == head(repo) and
            os.getenv("GITHUB_RUN_ATTEMPT") == "1" and
            os.getenv("LUMI_TEN_PAID_CONFIRMATION") == PAID_CONFIRMATION and
            os.getenv("GITHUB_RUN_ID", "").isdigit(),
            "NO_TRUSTED_SINGLE_GITHUB_DISPATCH")
    key = os.environ.get("OPENROUTER_API_KEY","")
    require(key.startswith("sk-or-") and 10 <= len(key) <= 256
            and not any(x.isspace() for x in key), "MISSING_SHARED_API_KEY")
    # Authenticated key read only; unlike separate-key metadata analyzer,
    # deliberately does NOT compare lifetime shared-key usage to this
    # study's $20 budget. Per-study accounting is enforced in stage intent.
    data = read_current_key(api_key=key)["data"]
    try:
        remaining = provider_key_money(data.get("limit_remaining"), "limit_remaining")
    except HarnessStop:
        raise HarnessStop("COHORT_BATCH_STOP_UNKNOWN_PROVIDER_REMAINING") from None
    require(remaining >= Decimal("4.40") and
            data.get("is_free_tier") is False and
            data.get("is_management_key") is False,
            "SHARED_KEY_CREDIT_OR_TYPE")
    return key

class Batch:
    def __init__(self, repo, claims_parent, *, offline, historical_hold):
        self.repo = Path(repo).resolve()
        self.parent = Path(claims_parent).resolve()
        require(self.parent.is_dir() and not self.parent.is_symlink()
                and not self.parent.is_relative_to(self.repo),
                "UNSAFE_CLAIMS_PARENT")
        self.offline = offline
        self.historical = usd(historical_hold)
        require(self.historical >= DOCUMENTED_RESERVATION and
                self.historical + Decimal(len(IDS))*TRIAL_CAP <= CAP,
                "TEN_RESERVATIONS_EXCEED_20")
        # A stable run directory is deliberately NEVER reusable even if B01
        # failed: operator re-running same manual job cannot bill twice.
        self.root = self.parent / RUN_ID
        self.root.mkdir(mode=0o700,exist_ok=False)
        self.lock = simulate_seal(self.repo)
        check_lock(self.repo,self.lock)
        self.events = self.root / "stage-events"
        self.events.mkdir(mode=0o700)
        self.claims = self.root / "stories"
        self.claims.mkdir(mode=0o700)
        self.reported = Decimal("0")
        self.attempts = []
        self.global_stop = False
        write_new(self.root/"00-full-round-reserve.json",{
            "schema":SCHEMA,"git_sha":head(self.repo),
            "seal_sha256":hashlib.sha256(canonical_json(self.lock)).hexdigest(),
            "case_ids":list(IDS),"all_ten_reserved_before_b01":True,
            "historical_conservative_hold_usd":format(self.historical,"f"),
            "new_ten_reserved_usd":format(10*TRIAL_CAP,"f"),
            "total_user_ceiling_usd":format(CAP,"f"),
            "offline_simulation_only":offline,"zero_retries":True,
            "no_mid_cohort_mutations":True,
            "production_write_authorized":False,
            "provider_account_wide_spend_guaranteed":False,
        })

    def event(self, case_id, phase, stage, payload):
        check_lock(self.repo,self.lock)
        require(stage in STAGE_MAX and phase in ("intent","settled")
                and case_id in IDS, "UNREGISTERED_EVENT")
        code = ORDER.index(stage)+1
        file = self.events/f"{case_id}-{code:02d}-{stage.lower()}-{phase}.json"
        if phase=="intent":
            require(not file.exists() and
                    not (self.events/f"{case_id}-{code:02d}-{stage.lower()}-settled.json").exists(),
                    "DUPLICATE_STAGE")
            # Remaining reserved cases are never treated as free budget.
            unattempted = len(IDS)-len(self.attempts)
            require(self.historical+self.reported+
                    unattempted*TRIAL_CAP <= CAP,
                    "CUMULATIVE_20_RESERVATION")
        else:
            require((self.events/f"{case_id}-{code:02d}-{stage.lower()}-intent.json").exists(),
                    "STAGE_SETTLEMENT_WITHOUT_INTENT")
            price=usd(payload["provider_reported_cost_usd"])
            require(price <= STAGE_MAX[stage],"STAGE_CHARGE_CAP")
        write_new(file,{
            "schema":SCHEMA,"case_id":case_id,
            "phase":phase,"stage":stage,
            "frozen_harness_commit":self.lock["harness_commit"],
            "details":payload,
            "real_provider_evidence":not self.offline,
            "no_retry":True,
        })

    def run(self, transport_factory, checker_factory):
        require(callable(transport_factory) and callable(checker_factory),
                "MISSING_PROVIDER_ADAPTER")
        for case in IDS:
            check_lock(self.repo,self.lock)
            harness=create_harness(self.repo,case)
            write_new(self.root/f"{case}-00-attempt.json",{
                "schema":SCHEMA,"case_id":case,
                "git_sha":self.lock["harness_commit"],
                "memory_sha256":harness.memory_snapshot_sha256,
                "reserved_usd":format(TRIAL_CAP,"f"),
                "no_retry":True,
            })
            try:
                result=run_one_case_with_injected_transport(
                    str(self.repo),case,self.claims,
                    transport=transport_factory(case),
                    harness=harness,
                    generation_receipt_checker=checker_factory(case),
                    stage_event=lambda phase,stage,data:
                        self.event(case,phase,stage,data))
                require(result["status"] in (
                    "ACCEPT_CLAIMED","REJECT","OPERATIONAL_STOP"),
                    "INVALID_RESULT")
                price=usd(result["provider_reported_total_usd"])
                receipts=[]
                for stage in ORDER:
                    match=list(self.events.glob(
                        f"{case}-??-{stage.lower()}-settled.json"))
                    if match:
                        require(len(match)==1,"RECEIPT_DUPLICATE")
                        payload=json.loads(match[0].read_text())
                        receipts.append(usd(payload["details"][
                            "provider_reported_cost_usd"]))
                # An ordinary manuscript/schema failure can continue, but
                # ONLY if every attempted network call has a settled receipt.
                intents=list(self.events.glob(f"{case}-*-intent.json"))
                require(len(intents)==len(receipts),"UNSETTLED_POST_CHARGE")
                require(sum(receipts,Decimal("0"))==price and
                        price <= TRIAL_CAP and
                        self.historical+self.reported+price <= CAP,
                        "RECEIPTS_AND_BUDGET_DISAGREE")
                self.reported += price
                row={
                    "schema":SCHEMA,"case_id":case,"status":result["status"],
                    "provider_cost_usd":format(price,"f"),
                    "model_posts":result["model_call_envelopes_observed"],
                    "stage_receipts":len(receipts),
                    "no_story_fixes":True,"automatic_retries":0,
                    "certified_quality_pass":False,
                }
                write_new(self.root/f"{case}-01-result.json",row)
                self.attempts.append(row)
            except Exception as exc:
                # A transport timeout, missing generation receipt, corrupt
                # journal or file I/O is NEVER converted into a skipped
                # fabricated case. Leave failed attempt consumed.
                self.global_stop=True
                write_new(self.root/f"{case}-99-global-stop.json",{
                    "schema":SCHEMA,"case_id":case,
                    "reason":"UNKNOWN_PROVIDER_CHARGE_OR_INTEGRITY_FAILURE",
                    "halted":True,"no_retry":True,
                    "uncompleted_cases":list(IDS[len(self.attempts):]),
                })
                raise HarnessStop("COHORT_BATCH_STOP_UNKNOWN_OR_INTEGRITY") from None
        summary={
            "schema":SCHEMA,"status":"TEN_ATTEMPTS_RECORDED",
            "case_ids":[a["case_id"] for a in self.attempts],
            "case_results":[{"case_id":a["case_id"],"status":a["status"],
                             "cost_usd":a["provider_cost_usd"]}
                            for a in self.attempts],
            "simulated_offline_only":self.offline,
            "provider_reported_cost_usd":format(self.reported,"f"),
            "conservative_lumi_total_usd":
                format(self.historical+self.reported,"f"),
            "model_quality_certified":False,
            "retry_count":0,"harness_mid_cohort_edits":0,
            "production_write":False,
        }
        write_new(self.root/"99-cohort-result.json",summary)
        return summary

def run_ten(repo, parent, *, paid=False, historical_hold="3.249558"):
    if paid:
        key=authorize_paid(repo)
        def provider(_):return lambda body:https_post_once(key,body)
        def verify(_):
            def checker(**arg):
                receipt=read_and_verify_generation(api_key=key,**arg)
                require(receipt["provider_origin_independently_attested"] is True,
                        "UNAUTHENTICATED_PROVIDER_COST_GET")
                return receipt
            return checker
    else:
        # The fake provider is test-only, never loaded in paid mode.
        from tests.test_story_harness_cohort_pipeline_v1 import MockProvider
        def provider(case):return MockProvider(case,reject=(case=="B04"))
        from src.story_harness_cohort_generation_receipt_v1 import validate_generation
        from src.story_harness_p417_live_pilot import MODEL,PROVIDER
        def verify(_):
            def checker(**arg):
                gen={"data":{"id":arg["generation_id"],"model":MODEL,
                    "provider_name":PROVIDER,"cancelled":False,
                    "finish_reason":"stop","is_byok":False,
                    "tokens_prompt":arg["prompt_tokens"],
                    "tokens_completion":arg["completion_tokens"],
                    "total_cost":arg["reported_cost_usd"]}}
                return validate_generation(gen,**arg)
            return checker
    batch=Batch(repo,parent,offline=not paid,historical_hold=historical_hold)
    return batch.run(provider,verify)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--rehearse-ten",action="store_true")
    modes.add_argument("--paid-ten",action="store_true")
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--claims-parent",required=True)
    parser.add_argument("--historic-hold-usd",default="3.249558")
    args=parser.parse_args()
    result=run_ten(args.repo_root,args.claims_parent,
                   paid=args.paid_ten,historical_hold=args.historic_hold_usd)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":main()
