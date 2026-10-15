"""P4.3 v21.5 OFFLINE-ONLY single-attempt runner at original provider callback boundary.

No real transport can be selected. The original frozen v21.4 paid runner is
invoked in its fake-callback simulation mode. A separate P4.2 diagnostic
wrapper is installed on the FINAL_AUDIT adapter callback (same call signature
used by real provider calls). This module neither grants nor accepts paid auth.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import socket
from typing import Any

PROFILE_SCHEMA="lumi.v21.5-offline-runner-profile.v1"
RESULT_SCHEMA="lumi.v21.5-offline-runner-result.v1"
EXPECTED_SOURCE_COMMIT="2eb3d825b5baf8f0f16ccb23805f619d433c7236"
PINNED_PROFILE_SHA="37362ae6155b5a319d1776d68a9014c23628d476379dd1621b606267b1199161"
PROFILE_RELPATH="data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json"
SCENARIOS=("repair_succeeds","invalid_final_schema","missing_usage_cost","transport_invalid_json")
RUN_ID=re.compile(r"^[a-z][a-z0-9_-]{2,48}$")
CAPS={"INITIAL_AUDIT":.04,"SCENE_REPAIR":.035,"FINAL_AUDIT":.025}


class RunnerStop(RuntimeError):pass


def _must(cond,why):
    if not cond:raise RunnerStop(why)


def _sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()


def pinned_config(root:Path,relative:str,expected_sha:str):
    base=root.resolve(strict=True)
    _must(".." not in Path(relative).parts and not Path(relative).is_absolute(),
          "Invalid immutable policy path")
    p=base
    for part in Path(relative).parts:
        p=p/part
        _must(not p.is_symlink(),"Symlink policy file denied")
    _must(p.is_file() and p.resolve().is_relative_to(base) and
          _sha(p.read_bytes())==expected_sha,"Unpinned policy or source bytes")
    return json.loads(p.read_text(encoding="utf8"))


def pre_dispatch_gate(conf, original, *, mode="OFFLINE_FAKE_PROVIDER", grant=None,
                      endpoint=None, quoted_input_tokens=None,
                      verified_pricing=None, run_attempt=1):
    """Deny all real spending, even if a caller supplies an apparent grant."""
    _must(conf["schema"]==PROFILE_SCHEMA
          and conf["execution_mode"]=="OFFLINE_FAKE_PROVIDER_ONLY"
          and conf["billing_permitted"] is False
          and conf["provider_network_allowed"] is False
          and conf["automatic_retry_enabled"] is False
          and conf["production_state_writes_allowed"] is False
          and conf["real_english_master_admission_allowed"] is False
          and conf["max_quality_calls"]==3
          and conf["max_repairs"]==1
          and conf["targeted_final_audit_only"] is True
          and conf["quality_stage_caps_usd"]==
              {"INITIAL_AUDIT":.04,"SCENE_REPAIR":.035,"FINAL_AUDIT":.025}
          and conf["quality_target_usd"]==.1
          and conf["provider_spend_hard_cap_guaranteed"] is False,
          "v21.5 offline safety invariants changed")
    _must(original["runtime_freeze"]["runtime_revision"]==
          "SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and original["paid_boundary"]["paid_execution_authorized"] is False
          and original["paid_boundary"]["authorization_consumed"] is True,
          "Frozen runtime unexpectedly allows paid execution")
    _must(original["model_slots"]=={
            "BLOCKING_AUDITOR":"anthropic/claude-sonnet-5.5",
            "SCENE_REPAIRER":"anthropic/claude-sonnet-5.5"},
          "Unapproved or substituted model routing")
    _must(original["cost_policy"]["quality_total_ceiling_usd"]==.1
          and original["cost_policy"]["provider_spend_cap_guaranteed"] is False,
          "Original runtime accounting limits changed")
    _must(run_attempt==1 and conf["allowed_attempts"]==1,
          "Workflow reruns and multi-attempt quality runs forbidden")
    _must(mode=="OFFLINE_FAKE_PROVIDER"
          and grant is None and endpoint is None
          and quoted_input_tokens is None and verified_pricing is None,
          "PAID_DISPATCH_DISABLED: no authentic user grant, verified provider pricing, "
          "routing, or request-time token/spend bound")
    _must(conf["pricing_status"]=="NOT_VERIFIED_REAL_WORLD"
          and conf["provider_endpoint_status"]=="NO_REAL_ENDPOINT_SELECTED"
          and conf["request_token_count_status"]=="UNVERIFIED_REAL_WORLD",
          "Pricing/routing/token estimate falsely certified")
    return {
        "status":"OFFLINE_PRE_DISPATCH_ONLY",
        "real_network_dispatch_possible":False,
        "user_paid_grant_consumed":False,
        "real_price_quote_verified":False,
        "real_request_token_count_verified":False,
        "hard_provider_spend_limit_guaranteed":False,
        "target_quality_budget_usd":.1,
        "stage_caps_usd":CAPS,
        "model_slots":original["model_slots"],
    }


def _claim_once(root:Path,run_id:str):
    _must(RUN_ID.fullmatch(run_id) is not None,"Unsafe or missing run ID")
    _must(not root.is_symlink(),"Symlink output root denied")
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    p=root/("offline-once-"+run_id+".claimed")
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"wb") as out:
        out.write((run_id+"\n").encode())
        out.flush()
        os.fsync(out.fileno())
    return p


def run_offline_once(*,source_root:Path,output_root:Path,run_id:str,scenario:str,
                     offline_config:dict,diag):
    _must(scenario in SCENARIOS,"Unknown synthetic quality-run case")
    # Safety preflight BEFORE claiming any work, opening transport or writing
    # a story. Source tree is pinned by caller and rechecked by v21 verifier.
    from src.spineforge_v21_freeze import AUDIT,verify_v21_runtime
    from src.spineforge_v21_model_adapter import (
        execute_initial_audit_call,execute_scene_repair_call,execute_final_audit_call)
    from src.spineforge_v21_paid_quality_once import execute_paid_quality_once
    original=pinned_config(source_root,PROFILE_RELPATH,PINNED_PROFILE_SHA)
    frozen=verify_v21_runtime()
    gate=pre_dispatch_gate(offline_config,original)
    _must(frozen["runtime_revision"]=="SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4",
          "Original frozen verifier failed")
    _must(original["source_story"]["story_sha256"]==
          offline_config["source_story_sha256"]
          and original["source_story"]["artifact_id"]==
          offline_config["source_story_artifact_id"]
          and original["source_story"]["approved_spine_hash"]==
          offline_config["approved_spine_hash"],
          "P4.3 different story or Spine source")
    _claim_once(output_root,run_id)

    stages=[]
    request_exposure=[]
    secrets=("P43_DO_NOT_RECORD_SECRET","sk-p43sensitive012345678901234")
    source_findings=json.loads(AUDIT.read_text(encoding="utf8"))["findings"]
    findings=[{**f,"repair_scope":"SCENE_REPAIR"
              if f["repair_scope"]=="LOCAL_REPAIR" else f["repair_scope"]}
              for f in source_findings]
    diag_root=output_root/(run_id+"-private-diagnostics")

    def mock_provider(**kwargs):
        # SAME call_fn signature used by the real adapter/provider callback.
        stage=kwargs["request_class"]
        stages.append(stage)
        _must(len(stages)<=3,"Fourth provider request forbidden")
        required_max={"spineforge_v21_initial_blocking_audit":3000,
                      "spineforge_v21_scene_repair":3500,
                      "spineforge_v21_targeted_final_audit":1800}
        _must(stage in required_max and kwargs["max_tokens"]==required_max[stage],
              "Unexpected provider request class/output allowance")
        request_exposure.append({
            "request_class":stage,
            "payload_utf8_bytes":len(kwargs["user_prompt"].encode("utf8")),
            "max_output_tokens":kwargs["max_tokens"],
            "verified_billable_input_token_count":False,
            "verified_live_price_and_endpoint":False,
            "paid_dispatch_guard":"BLOCKED_OFFLINE",
        })
        user_payload=json.loads(kwargs["user_prompt"])
        if "initial" in stage:
            response={"findings":findings,"summary":"mock initial"}
        elif "scene_repair" in stage:
            response={"replacement_scene":
                      "Arda cut the line. Nisa helped him reach solid ground.",
                      "resolved_blocking_finding_indexes":
                        [f["index"] for f in user_payload["blocking_findings"]],
                      "preserved_invariants":[],
                      "summary":"mock repair, NOT a genuine story"}
        else:
            _must("full_story" not in user_payload
                  and "story_segments" not in user_payload
                  and user_payload["routing_policy"]["scope"]==
                     "REPAIRED_SCENE_PLUS_BOUNDARIES",
                  "Final audit violated targeted-only privacy/quality scope")
            response={"findings":[],"summary":"mock final"}
            if scenario=="invalid_final_schema":
                response["injected_unknown_field"]=secrets[0]
            elif scenario=="missing_usage_cost":
                pass
            elif scenario=="transport_invalid_json":
                from src.generate import OpenRouterCallError
                raise OpenRouterCallError("scrubbed_transport_failure",{
                  "stage":"structured_parse",
                  "body":{"choices":[{"message":{"content":secrets[1]}}],
                          "usage":{"prompt_tokens":100,"completion_tokens":20,
                                   "total_tokens":120,"cost":.01}},
                  "request":{"authorization":secrets[1]},
                })
        body={"usage":{"prompt_tokens":100,"completion_tokens":20,
                       "total_tokens":120,"cost":.01},
              "headers":{"authorization":secrets[1]}}
        if "final" in stage and scenario=="missing_usage_cost":
            body["usage"].pop("cost")
        return response,body,{"max_tokens":kwargs["max_tokens"],
                              "response_format":{"type":"json_schema"}},[]

    def make_cb(adapter,stage):
        def wrapped(payload):
            if stage!="FINAL_AUDIT":
                return adapter(api_key="",payload=payload,
                               call_fn=mock_provider,
                               model=original["model_slots"][
                                  "SCENE_REPAIRER" if stage=="SCENE_REPAIR"
                                  else "BLOCKING_AUDITOR"])
            try:
                return adapter(api_key="",payload=payload,
                               call_fn=mock_provider,
                               model=original["model_slots"]["BLOCKING_AUDITOR"])
            except Exception as exc:
                from src.spineforge_v21_constraints import digest_json
                saved=diag.persist_failure(exc,stage="FINAL_AUDIT",
                    input_sha256=digest_json(payload),
                    source_story_sha256=payload["repaired_story_sha256"],
                    run_id=run_id,output_dir=diag_root)
                raise diag.RedactedProviderFailure(exc,saved) from None
        return wrapped

    result,envelope=execute_paid_quality_once(
        api_key="",run_id=run_id,
        output_root=output_root,simulation=True,
        initial_audit_fn=make_cb(execute_initial_audit_call,"INITIAL_AUDIT"),
        scene_repair_fn=make_cb(execute_scene_repair_call,"SCENE_REPAIR"),
        final_audit_fn=make_cb(execute_final_audit_call,"FINAL_AUDIT"))
    _must(len(stages)==3 and result["quality_model_calls"]<=3
          and [x["stage"] for x in result["quality_calls"]]==[
              "INITIAL_AUDIT","SCENE_REPAIR","FINAL_AUDIT"]
          and result["automatic_retry_executed"] is False
          and result["automatic_second_repair_executed"] is False
          and result["state_commit_executed"] is False
          and envelope["explicit_paid_authorization"] is False
          and envelope["simulation"] is True,
          "Original bounded runtime violated P4.3 limits")
    failed=scenario!="repair_succeeds"
    _must(result["status"]==
          ("REJECT_PROVIDER_FAILURE" if failed else "ACCEPT"),
          "Actual mock result not expected status")
    if failed:
        _must(result["final_audit_validated"] is False and
              result["accepted_story_sha256"] is None,
              "Malformed final response was promoted to successful quality")
    row={
      "schema":RESULT_SCHEMA,
      "run_id":run_id,"scenario":scenario,"original_runtime_revision":frozen["runtime_revision"],
      "offline_pre_dispatch":gate,
      "source_story_artifact_id":envelope["source_story_artifact_id"],
      "source_story_sha256":envelope["source_story_sha256"],
      "stage_order":stages,
      "request_budget_exposure":request_exposure,
      "model_call_attempts":len(stages),
      "usage_reported_api_calls":result["quality_usage_rollup"]["api_calls"],
      "quality_status_from_original_runtime":result["status"],
      "original_runtime_accept_is_simulation_only":True,
      "real_story_quality_accepted":False,
      "provider_network_requests":0,
      "new_real_provider_spend_usd":"0",
      "auto_retry_executed":False,
      "english_master_seal_authorized":False,
      "q25_extraction_authorized":False,
      "state_commit_authorized":False,
      "quality_ledger_stage_order":[v["stage"] for v in result["quality_calls"]],
      "final_diagnostic_present":failed,
      "diagnostic_phase":None,
      "diagnostic_classification":None,
      "diagnostic_accounting_complete":None,
      "redacted_response_sha256":None,
    }
    if failed:
        raw=(diag_root/"targeted-final-audit-diagnostic.json").read_bytes()
        d=json.loads(raw)
        _must(d["schema"]==diag.SCHEMA and
              d["raw_sensitive_text_stored"] is False and
              d["q25_execution_authorized"] is False and
              d["state_commit_authorized"] is False,
              "Experimental diagnostic was not safe")
        _must(len(_sha(raw))==64, "Private diagnostic missing bytes")
        row.update({
            "diagnostic_phase":d["phase"],
            "diagnostic_classification":d["validation_diagnostic"]["category"],
            "diagnostic_accounting_complete":d["usage"]["accounting_complete"],
            "redacted_response_sha256":d["parsed_response_sha256"],
        })
    # Avoid cross-run secrets escaping archived results/ledgers/diagnostics.
    for path in (output_root/run_id).rglob("*"):
        if path.is_file() and path.suffix in (".json",".jsonl",".txt"):
            text=path.read_text(encoding="utf8")
            _must(all(secret not in text for secret in secrets),
                  "Unredacted mock/provider secret escaped into v21 output")
    if failed:
        raw=(diag_root/"targeted-final-audit-diagnostic.json").read_text()
        _must(all(secret not in raw for secret in secrets),
              "Sensitive mock text in immutable diagnostic evidence")
    return row

