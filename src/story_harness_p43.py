"""P4.3: source-bound v21.5 fake-transport runner and paid kill-switch proof.

Runs P4.2 and original pinned v21.4 integrity verifiers first. A separate
experiment v21.5 offline runner drives ORIGINAL adapter callback signatures
through a real v21 bounded-quality runner. All actual paid network requests
are structurally unavailable. Rejected original story remains rejected.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_p22 import _python_runtime_env
from src.story_harness_p42 import qualify as qualify_diagnostics
from src.story_harness_v1 import HarnessStop,canonical_bytes,digest,load_json,secure_artifact

SCHEMA="lumi.story-harness-p43-offline-gated-runner.v1"
CONFIG="configs/story_harness_p43_offline_runner.json"
CONFIG_SHA="f02ad3ecfaf12a7a4d9b502618d65c25df5302fb38c3de8e6b7245d8da15d051"
RUNNER="src/story_harness_p43_runner.py"
RUNNER_SHA="3254f970fb20dc8c4257333adad33a3dc46bcd517293a3d226f20dcde5253ed2"
DIAGNOSTIC="src/story_harness_p42_diagnostics.py"
CASES=("repair_succeeds","invalid_final_schema","missing_usage_cost","transport_invalid_json")
_SCRIPT=r"""
import importlib.util,json,os,socket,sys,tempfile
from pathlib import Path
def no_network(*a,**kw):
 raise RuntimeError("P4.3 hardware/HTTP network kill switch: blocked")
socket.create_connection=no_network
socket.socket.connect=no_network
socket.socket.connect_ex=no_network
def load_module(path,name):
 s=importlib.util.spec_from_file_location(name,path)
 o=importlib.util.module_from_spec(s)
 s.loader.exec_module(o)
 return o
r=load_module(sys.argv[1],"offline_p43_runner")
d=load_module(sys.argv[2],"offline_p42_diagnostic")
cfg=json.loads(Path(sys.argv[3]).read_text())
from src.spineforge_v21_paid_quality_once import PROFILE_PATH
frozen=json.loads(PROFILE_PATH.read_text())
records=[]
with tempfile.TemporaryDirectory(prefix="p43-offline-private-",dir=os.environ.get("TMPDIR")) as td:
 root=Path(td)
 for case in r.SCENARIOS:
  row=r.run_offline_once(source_root=Path.cwd(),output_root=root,
       run_id="offline-"+case,scenario=case,offline_config=cfg,diag=d)
  assert row["schema"]==r.RESULT_SCHEMA
  assert row["provider_network_requests"]==0
  # Consume-once negative replay, same once-token cannot re-run.
  try:
   r.run_offline_once(source_root=Path.cwd(),output_root=root,
       run_id="offline-"+case,scenario=case,offline_config=cfg,diag=d)
   raise AssertionError("single-shot replay unexpectedly succeeded")
  except FileExistsError:
   pass
  records.append(row)
 # A paid-mode request is rejected BEFORE even touching the mock transport.
 rejections={}
 for key,options in [
  ("real_mode",{"mode":"REAL_PROVIDER"}),
  ("fake_grant",{"grant":{"user":"forged"}}),
  ("endpoint",{"endpoint":"https://openrouter.ai/api/v1/chat/completions"}),
  ("price_quote",{"verified_pricing":{"model":"foo","cost":0}}),
  ("token_count",{"quoted_input_tokens":123}),
  ("workflow_rerun",{"run_attempt":2}),
 ]:
  try:
   r.pre_dispatch_gate(cfg,frozen,**options)
   raise AssertionError("paid preflight forged success: "+key)
  except r.RunnerStop:rejections[key]=True
 # An arbitrary modified profile may not flip the paid kill switch.
 for field,value in [
  ("billing_permitted",True),("provider_network_allowed",True),
  ("automatic_retry_enabled",True),("max_quality_calls",7),
  ("targeted_final_audit_only",False),
  ("production_state_writes_allowed",True),
  ("provider_spend_hard_cap_guaranteed",True)]:
  change=dict(cfg);change[field]=value
  try:
   r.pre_dispatch_gate(change,frozen)
   raise AssertionError("fake profile relaxed: "+field)
  except r.RunnerStop:rejections[field]=True
print(json.dumps({"cases":records,"pre_dispatch_negative_rejections":rejections},
 sort_keys=True,ensure_ascii=False))
"""


def _must(ok,why):
    if not ok:raise HarnessStop(why)


def _source_conf(base):
    _must(digest((base/RUNNER).read_bytes())==RUNNER_SHA,
          "Experimental v21.5 callback runner source drifted")
    cfg=load_json(secure_artifact(base,CONFIG))
    _must(digest(secure_artifact(base,CONFIG))==CONFIG_SHA,
          "P4.3 offline trust policy changed")
    _must(cfg["schema"]=="lumi.v21.5-offline-runner-profile.v1"
          and cfg["source_commit"]==PINNED_SOURCE_COMMIT
          and cfg["p42_diagnostic_source_sha256"]==
              digest((base/DIAGNOSTIC).read_bytes())
          and cfg["original_v21_profile_sha256"]==
              "37362ae6155b5a319d1776d68a9014c23628d476379dd1621b606267b1199161",
          "P4.3 source guard changed")
    return cfg


def _exec_callbacks(base,source,python_executable):
    with TemporaryDirectory(prefix="lumi-p43-") as td:
        env=_python_runtime_env(python_executable,Path(td))
        env["TMPDIR"]=td
        script_args=[python_executable,"-c",_SCRIPT,str((base/RUNNER).resolve(strict=True)),
                     str((base/DIAGNOSTIC).resolve(strict=True)),
                     str((base/CONFIG).resolve(strict=True))]
        try:
            p=subprocess.run(script_args,cwd=source,env=env,
                     capture_output=True,encoding="utf8",text=True,
                     timeout=45,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise HarnessStop("P4.3 original callback sandbox unavailable") from exc
        _must(p.returncode==0 and len(p.stdout)<30000,
              "P4.3 offline original callback failure: "+p.stderr[-350:].replace("\n"," "))
        try:return json.loads(p.stdout)
        except ValueError as exc:raise HarnessStop("Bad P4.3 proof JSON") from exc


def _validate_observed(data,earlier,conf):
    _must(set(data)=={"cases","pre_dispatch_negative_rejections"} and
          [r["scenario"] for r in data["cases"]]==list(CASES),
          "Not all original callback integration cases ran")
    _must(set(data["pre_dispatch_negative_rejections"])=={
        "real_mode","fake_grant","endpoint","price_quote","token_count",
        "workflow_rerun","billing_permitted","provider_network_allowed",
        "automatic_retry_enabled","max_quality_calls",
        "targeted_final_audit_only","production_state_writes_allowed",
        "provider_spend_hard_cap_guaranteed",
    } and all(data["pre_dispatch_negative_rejections"].values()),
       "P4.3 paid kill-switch negative cases missing")
    safe=[]
    for row in data["cases"]:
        expected_failure=row["scenario"]!="repair_succeeds"
        _must(row["schema"]=="lumi.v21.5-offline-runner-result.v1"
              and row["offline_pre_dispatch"]["status"]=="OFFLINE_PRE_DISPATCH_ONLY"
              and row["offline_pre_dispatch"]["real_network_dispatch_possible"] is False
              and row["model_call_attempts"]==3
              and len(row["stage_order"])==3
              and len(row["request_budget_exposure"])==3
              and [r["max_output_tokens"] for r in row["request_budget_exposure"]]==
                  [3000,3500,1800]
              and all(r["payload_utf8_bytes"]>100 and
                       r["verified_billable_input_token_count"] is False and
                       r["verified_live_price_and_endpoint"] is False and
                       r["paid_dispatch_guard"]=="BLOCKED_OFFLINE"
                       for r in row["request_budget_exposure"])
              and row["usage_reported_api_calls"]<=3
              and row["quality_ledger_stage_order"]==[
                     "INITIAL_AUDIT","SCENE_REPAIR","FINAL_AUDIT"]
              and row["quality_status_from_original_runtime"]==
                ("REJECT_PROVIDER_FAILURE" if expected_failure else "ACCEPT")
              and row["source_story_sha256"]==conf["source_story_sha256"]
              and row["source_story_artifact_id"]==conf["source_story_artifact_id"]
              and row["original_runtime_accept_is_simulation_only"] is True
              and row["real_story_quality_accepted"] is False
              and row["provider_network_requests"]==0
              and row["new_real_provider_spend_usd"]=="0"
              and row["auto_retry_executed"] is False
              and row["english_master_seal_authorized"] is False
              and row["q25_extraction_authorized"] is False
              and row["state_commit_authorized"] is False
              and row["final_diagnostic_present"] is expected_failure,
              "P4.3 fake ACCEPT improperly promoted or stages missing")
        if expected_failure:
            _must(row["diagnostic_phase"] in {
                  "response_validation","usage_validation","structured_parse"}
                  and row["diagnostic_classification"] in {
                  "UNEXPECTED_FIELD","INVALID_USAGE","UNSPECIFIED"}
                  and row["diagnostic_accounting_complete"] is
                    (row["scenario"]!="missing_usage_cost"),
                  "P4.3 redacted provider final diagnostic missing or cost forged")
        else:
            _must(row["diagnostic_phase"] is None
                  and row["diagnostic_classification"] is None,
                  "Clean simulated final audit incorrectly treated as failure")
        safe.append(row)
    return safe


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    policy=_source_conf(base)
    prev=qualify_diagnostics(repo_root=base,pinned_source_root=source,
                             python_executable=python_executable)
    _must(prev["stop_reason"]=="REAL_QUALITY_NOT_ACCEPTED_DIAGNOSTIC_READY"
          and prev["provider_calls"]==0,
          "P4.3 bypassed frozen offline diagnostic evidence gate")
    result=_exec_callbacks(base,source,python_executable)
    rows=_validate_observed(result,prev,policy)
    return {
      "schema":SCHEMA,
      "source_commit":PINNED_SOURCE_COMMIT,
      "mode":"OFFLINE_SINGLE_ATTEMPT_V21_5_RUNNER_ONLY",
      "offline_profile_sha256":CONFIG_SHA,
      "experimental_runner_sha256":digest((base/RUNNER).read_bytes()),
      "experimental_diagnostic_sha256":digest((base/DIAGNOSTIC).read_bytes()),
      "p42_failure_diagnostic_receipt_sha256":digest(canonical_bytes(prev)),
      "original_v21_4_source_modified":False,
      "original_v21_4_source_and_adapter_executed":True,
      "original_provider_callback_shape_injected":True,
      "mock_provider_boundary_used":True,
      "offline_qualification_once_claim_consumed":True,
      "real_paid_user_authorization_granted":False,
      "real_provider_pricing_or_token_bound_verified":False,
      "real_provider_spend_hard_cap_guaranteed":False,
      "kill_switch_premode_negative_case_count":len(result["pre_dispatch_negative_rejections"]),
      "offline_provider_callback_cases":rows,
      "old_unbounded_repair_loop_restored":False,
      "historical_failed_story_still_rejected":True,
      "actual_english_master_accepted":False,
      "english_master_seal_emitted":False,
      "q25_handoff_emitted":False,
      "production_state_write_executed":False,
      "provider_calls":0,"provider_cost_usd":"0",
      "stop_reason":"REAL_PAID_DISPATCH_DISABLED_OFFLINE_RUNNER_QUALIFIED",
      "state":"STOPPED_BEFORE_ANY_REAL_PROVIDER_EXECUTION",
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--pinned-source-root",required=True)
    parser.add_argument("--verify-report")
    a=parser.parse_args()
    base=Path(a.repo_root).resolve(strict=True)
    report=qualify(repo_root=base,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(base,a.verify_report))==report,
              "P4.3 offline runner receipt has been forged or changed")
    print(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":main()

