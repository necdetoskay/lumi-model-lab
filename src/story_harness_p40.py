"""P4.0: genuine v21 frozen bounded-quality runtime, zero-cost producer preflight.

Original v21 simulation callbacks execute against the original frozen runtime
and adapter in a sandboxed subprocess. Their synthetic ACCEPT is NEVER story
quality acceptance; existing real paid run is explicitly REJECT_PROVIDER_FAILURE.
No English Master seal, Q25 handoff, model provider call or state commit.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from src.story_harness_p32 import qualify as qualify_master_denial
from src.story_harness_p22 import _python_runtime_env
from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA="lumi.story-harness-p40-genuine-v21-producer-preflight.v1"
MANIFEST_PATH="configs/story_harness_p40_v21_producer_preflight.json"
MANIFEST_SHA="51926bb46c3505508212e2e1eb67301ca5c51e1175d27b8b6e2652392a768027"
EXPECTED_SCENARIOS={
 "clean":("ACCEPT",1,0,False,0.01),
 "repair_succeeds":("ACCEPT",3,1,True,0.03),
 "non_convergent":("REJECT_NON_CONVERGENT",3,1,True,0.03),
 "initial_cost_ceiling":("REJECT_COST_CEILING",1,0,False,0.041),
 "repair_cost_ceiling":("REJECT_COST_CEILING",2,1,False,0.046),
 "final_cost_ceiling":("REJECT_COST_CEILING",3,1,True,0.046),
}
HISTORIC_RUN=37230896244
SOURCE_SHA_PATHS=[
 "src/spineforge_v21_quality_runtime.py","src/spineforge_v21_bounded_quality.py",
 "src/spineforge_v21_model_adapter.py","src/spineforge_v21_paid_quality_once.py",
 "src/spineforge_v21_simulation.py","src/spineforge_v21_freeze.py",
 "src/spineforge_v21_constraints.py",
 "data/specifications/story_lab/spineforge_v21_bounded_quality_contract.json",
 "data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json",
 f"evidence/spineforge-v21-paid-quality/{HISTORIC_RUN}/v21-bounded-quality-result.json",
 f"evidence/spineforge-v21-paid-quality/{HISTORIC_RUN}/v21-bounded-quality-envelope.json",
]
SIMULATION_LAUNCHER=r"""
import json
import os
import socket
import tempfile
from pathlib import Path
def forbidden(*a, **kw): raise RuntimeError("P4.0 simulation attempted network")
socket.create_connection=forbidden
socket.socket.connect=forbidden
socket.socket.connect_ex=forbidden
from src.spineforge_v21_freeze import verify_v21_runtime
from src.spineforge_v21_simulation import CASES,simulate_case
freeze=verify_v21_runtime()
with tempfile.TemporaryDirectory(prefix="lumi-p40-v21-",dir=os.environ.get("TMPDIR")) as tmp:
    result=[simulate_case(name,Path(tmp)) for name in CASES]
print(json.dumps({"freeze":{"runtime_revision":freeze["runtime_revision"],
 "profile_sha256":freeze["profile_sha256"]},
 "scenarios":result},sort_keys=True,ensure_ascii=False))
"""


def _must(value, reason):
    if not value:
        raise HarnessStop(reason)


def _manifest(base, override=None):
    raw=secure_artifact(base,MANIFEST_PATH)
    _must(digest(raw)==MANIFEST_SHA,"P4.0 source manifest SHA changed")
    original=load_json(raw)
    _must(override is None or override==original,
          "P4.0 caller attempted to substitute a different manifest")
    _must(set(original)=={
      "schema","source_commit","v21_frozen_runtime_revision",
      "historic_paid_v21_run_id","source_sha256_roles","simulation_scenarios",
      "seal_admission_source","admitted_historical_real_quality_result",
      "admitted_historical_english_master"},
      "P4.0 manifest topology changed")
    _must(original["schema"]=="lumi.story-harness-p40-v21-genuine-producer-preflight.v1"
          and original["source_commit"]==PINNED_SOURCE_COMMIT
          and original["v21_frozen_runtime_revision"]=="SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and original["historic_paid_v21_run_id"]==HISTORIC_RUN,
          "P4.0 pinned run/source/schema changed")
    _must(original["simulation_scenarios"]==list(EXPECTED_SCENARIOS),
          "P4.0 simulation sequence changed")
    _must([x["path"] for x in original["source_sha256_roles"]]==SOURCE_SHA_PATHS,
          "P4.0 original v21 runtime source roles changed")
    _must(original["admitted_historical_real_quality_result"] is None
          and original["admitted_historical_english_master"] is None,
          "Synthetic source was promoted to a real English Master")
    contract=original["seal_admission_source"]
    _must(contract=={
      "required_real_reviewer_decision":"ACCEPT",
      "source_story_must_equal_verified_p32_island_candidate":True,
      "real_quality_receipt_and_model_usage_required":True,
      "simulation_receipts_forbidden":True,
      "full_story_final_audit_forbidden":True,
      "max_initial_audit_calls":1,
      "max_scene_repair_calls":1,
      "max_targeted_final_audit_calls":1,
      "max_quality_calls":3,
      "automatic_retry_forbidden":True,
      "canonical_state_write_forbidden":True,
      "quality_accept_does_not_automatically_seal":True,
      "seal_required_before_q25":True,
    }, "P4.0 seal producer contract weakened")
    return original


def _source_roles(source,manifest):
    result={}
    for row in manifest["source_sha256_roles"]:
        _must(isinstance(row,dict) and set(row)=={"path","sha256"},
              "P4.0 source role malformed")
        path=row["path"]
        _must(isinstance(path,str) and path in SOURCE_SHA_PATHS
              and ".." not in Path(path).parts and not Path(path).is_absolute(),
              "P4.0 unsafe source path")
        target=source
        for part in Path(path).parts:
            target=target/part
            _must(not target.is_symlink(),"P4.0 source crosses symlink")
        _must(target.is_file() and target.resolve().is_relative_to(source)
              and target.stat().st_size < 900000,
              "P4.0 original source unavailable")
        raw=target.read_bytes()
        _must(digest(raw)==row["sha256"],
              "P4.0 original v21 runtime, policy, or paid history was mutated")
        result[path]=raw
    return result


def _real_paid_history(source_bytes):
    path=f"evidence/spineforge-v21-paid-quality/{HISTORIC_RUN}/v21-bounded-quality-result.json"
    observed=load_json(source_bytes[path])
    calls=observed["quality_calls"]
    account=observed["quality_usage_rollup"]
    _must(observed["schema"]=="spineforge-v21-bounded-quality-result.v1"
          and observed["status"]=="REJECT_PROVIDER_FAILURE"
          and observed["failure_reason"]=="FINAL_AUDIT: AdapterResponseError"
          and observed["quality_model_calls"]==3
          and observed["repair_count"]==1
          and observed["initial_blocking_count"]==1
          and observed["final_audit_executed"] is True
          and observed["final_audit_scope"]=="REPAIRED_SCENE_PLUS_BOUNDARIES"
          and observed["accepted_story"] is None
          and observed["accepted_story_sha256"] is None
          and observed["state_commit_executed"] is False
          and observed["automatic_retry_executed"] is False
          and observed["automatic_second_repair_executed"] is False,
          "Historical paid v21 quality failure was rewritten as story acceptance")
    _must([(r["stage"],r["status"]) for r in calls]==[
         ("INITIAL_AUDIT","COMPLETED"),
         ("SCENE_REPAIR","COMPLETED"),
         ("FINAL_AUDIT","FAILED")],
         "Historical paid quality stage failures were hidden")
    _must(account["api_calls"]==3
          and account["accounting_complete"] is True
          and account["cost_usd"]==0.057988
          and account["confirmed_cost_usd"]==0.057988
          and account["total_tokens"]==21870
          and account["latency_seconds"]==21.023,
          "Historical paid v21 token/cost ledger was altered")
    return {
       "historical_run_id":HISTORIC_RUN,
       "historical_quality_status":observed["status"],
       "historical_failure_reason":observed["failure_reason"],
       "historical_calls":3,
       "historical_cost_usd":account["cost_usd"],
       "historical_total_tokens":account["total_tokens"],
       "historical_cost_is_new_spend":False,
       "historical_quality_accept":False,
       "historical_story_sealed":False,
    }


def _original_freeze_contract(source_bytes,master):
    path="data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json"
    profile=load_json(source_bytes[path])
    contract=load_json(source_bytes[
      "data/specifications/story_lab/spineforge_v21_bounded_quality_contract.json"])
    stage=profile["cost_policy"]
    paid=profile["paid_boundary"]
    _must(profile["runtime_freeze"]["runtime_revision"]==
          "SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and profile["source_story"]["story_sha256"]==
          master["terminal_candidate"]["candidate_source_story_sha256"]
          and profile["source_story"]["artifact_id"]==
          master["terminal_candidate"]["candidate_artifact_id"],
          "v21 producer source is different from P3.2 qualified island story")
    _must(paid["paid_execution_authorized"] is False
          and paid["authorization_consumed"] is True
          and paid["authorization_state"]=="NO_GRANT_ISSUED"
          and paid["explicit_user_authorization_required"] is True,
          "Frozen v21 runtime is unexpectedly paid-authorized")
    limits=stage["quality_stage_limits_usd"]
    _must(limits=={"initial_audit":0.04,"scene_repair":0.035,"final_audit":0.025}
          and stage["quality_total_ceiling_usd"]==0.1
          and stage["provider_spend_cap_guaranteed"] is False
          and stage["hard_budget_gate_required_before_paid_e2e"] is True,
          "v21 bounded cost preflight profile was relaxed")
    _must(contract["quality"]["scene_repair"]["max_executions"]==1
          and contract["quality"]["final_audit"]["max_executions"]==1
          and contract["quality"]["automatic_looping"] is False,
          "Old unbounded repair loop has resurfaced")
    return {"runtime_revision":profile["runtime_freeze"]["runtime_revision"],
            "source_story_sha256":profile["source_story"]["story_sha256"],
            "cost_limits_usd":limits,
            "total_cost_target_usd":stage["quality_total_ceiling_usd"],
            "provider_spend_hard_cap_guaranteed":False,
            "no_paid_authorization":True,
            "automatic_repair_loop_forbidden":True}


def _run_real_v21_simulation(source,python_executable):
    with TemporaryDirectory(prefix="lumi-p40-") as temp:
        env=_python_runtime_env(python_executable,Path(temp))
        env["TMPDIR"]=temp
        args=[python_executable,"-c",SIMULATION_LAUNCHER]
        try:
            p=subprocess.run(args,cwd=source,env=env,capture_output=True,
                             text=True,encoding="utf-8",timeout=35,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise HarnessStop("Real v21 fake-transport execution was unavailable") from exc
        _must(p.returncode==0 and len(p.stdout)<22000,
              "Real v21 offline simulation failed: "+p.stderr[-280:].replace("\n"," "))
        try:
            observed=json.loads(p.stdout)
        except ValueError as exc:
            raise HarnessStop("Real v21 offline runner did not emit one valid receipt") from exc
    return observed


def _validate_simulation(data,profile,manifest):
    _must(set(data)=={"freeze","scenarios"},"v21 simulation returned unexpected result fields")
    _must(data["freeze"]["runtime_revision"]==profile["runtime_revision"]
          and len(data["freeze"]["profile_sha256"])==64,
          "Original freeze verifier did not confirm runtime")
    scenarios=data["scenarios"]
    _must(len(scenarios)==6
          and [x.get("scenario") for x in scenarios]==manifest["simulation_scenarios"],
          "Missing real v21 simulation scenario")
    for row in scenarios:
        label=row["scenario"]
        status,n,repairs,final,cost=EXPECTED_SCENARIOS[label]
        _must(set(row)=={
           "scenario","status","calls","repair_count","final_audit",
           "simulated_cost_usd","pass"},
           "Simulation status/ledger fields missing")
        _must(row["status"]==status and row["calls"]==n
              and row["repair_count"]==repairs and row["final_audit"] is final
              and row["simulated_cost_usd"]==cost and row["pass"] is True,
              "Original bounded engine did not respect contract")
    return [{"scenario":row["scenario"],"status":row["status"],
             "calls":row["calls"],"repairs":row["repair_count"],
             "final_audit":row["final_audit"],
             "mocked_provider":True,
             "real_story_quality_accept_proven":False,
             "eligible_for_english_master_seal":False}
            for row in scenarios]


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable,
            override_manifest=None,override_simulation=None):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    manifest=_manifest(base,override_manifest)
    previous=qualify_master_denial(repo_root=base,pinned_source_root=source,
                                   python_executable=python_executable)
    _must(previous["stop_reason"]=="ENGLISH_MASTER_NOT_ADMISSIBLE"
          and previous["historical_english_master_artifact_found"] is False
          and previous["q25_extraction_authorized"] is False,
          "P4.0 cannot bypass earlier same-story English Master DENY gate")
    sources=_source_roles(source,manifest)
    record=_real_paid_history(sources)
    frozen=_original_freeze_contract(sources,previous)
    raw_sim=override_simulation if override_simulation is not None else _run_real_v21_simulation(
        source,python_executable)
    scenarios=_validate_simulation(raw_sim,frozen,manifest)
    return {
      "schema":SCHEMA,"mode":"GENUINE_V21_OFFLINE_MOCK_TRANSPORT_QUALITY_PREFLIGHT",
      "source_commit":PINNED_SOURCE_COMMIT,
      "source_manifest_sha256":MANIFEST_SHA,
      "p32_english_master_denial_receipt_sha256":digest(canonical_bytes(previous)),
      "real_frozen_v21_engine_executed_with_mock_transport":True,
      "real_frozen_v21_profile_verified":True,
      "simulated_case_count":len(scenarios),
      "v21_frozen_contract":frozen,
      "original_six_synthetic_scenarios":scenarios,
      "historical_paid_quality_failure":record,
      "synthetic_ACCEPT_is_genuine_story_quality":False,
      "actual_accepted_english_master_source_present":False,
      "real_authorized_accepted_story_generated":False,
      "english_master_seal_contract_ready_for_separate_positive_qualification":True,
      "english_master_seal_emitted":False,
      "q25_handoff_emitted":False,
      "stop_reason":"REAL_BOUNDED_QUALITY_ACCEPT_MISSING",
      "state":"STOPPED_BEFORE_ENGLISH_MASTER_SEAL",
      "bounded_paid_attempt_authorized":False,
      "english_master_seal_authorized":False,
      "q25_extraction_authorized":False,
      "final_story_state_authorized":False,
      "state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,"provider_cost_usd":"0",
    }


def verify_report(report,*,repo_root,pinned_source_root,python_executable=sys.executable):
    expected=qualify(repo_root=repo_root,pinned_source_root=pinned_source_root,
                     python_executable=python_executable)
    _must(report==expected,"P4.0 signed-off preflight receipt does not match reality")
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    args=p.parse_args()
    base=Path(args.repo_root).resolve(strict=True)
    r=qualify(repo_root=base,pinned_source_root=args.pinned_source_root)
    if args.verify_report:
        _must(load_json(secure_artifact(base,args.verify_report))==r,
              "P4.0 receipt was altered")
    print(json.dumps(r,indent=2,ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()

