"""P4.2 no-cost v21.5 diagnostic preflight using original frozen v21.4 runtime.

Original failure source is immutable historical v21.3 and cannot be recovered.
New experimental wrapper persists a sanitized failed final response BEFORE
rethrowing; runtime never retries. Zero provider calls and no state mutation.
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
from src.story_harness_p41 import qualify as qualify_seal
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA="lumi.story-harness-p42-targeted-final-audit-diagnostic.v1"
CASES=(
 "unexpected_field","missing_required","invalid_findings_type",
 "invalid_json_transport","provider_exception_with_usage",
 "usage_missing","usage_nonfinite",
)
SOURCE_CODE_PATH="src/story_harness_p42_diagnostics.py"
RECORD_SCHEMA="lumi.v21-p42-redacted-failure-diagnostic.v1"
LAUNCHER=r"""
import importlib.util,json,os,socket,sys,tempfile
from pathlib import Path
def no_network(*a,**kw):raise RuntimeError("P4.2 provider access forbidden")
socket.create_connection=no_network
socket.socket.connect=no_network
socket.socket.connect_ex=no_network
spec=importlib.util.spec_from_file_location("p42diag",sys.argv[1])
diag=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diag)
import src.spineforge_v21_simulation as simulation
from src.spineforge_v21_constraints import digest_json
from src.generate import OpenRouterCallError
from src.spineforge_v21_freeze import verify_v21_runtime
freeze=verify_v21_runtime()
orig=simulation.execute_final_audit_call
CASES=("unexpected_field","missing_required","invalid_findings_type",
 "invalid_json_transport","provider_exception_with_usage",
 "usage_missing","usage_nonfinite")
SECRETS=("NEVER_STORE_THIS","sk-demo-secret-ABCD1234567890123",
 "Bearer sk-injected_987654321")
rows=[]
with tempfile.TemporaryDirectory(prefix="lumi-p42-",dir=os.environ.get("TMPDIR")) as tmp:
 for case in CASES:
  output=Path(tmp)/case
  diag_dir=Path(tmp)/("diagnostic-"+case)
  def fake_final(*,api_key,payload,call_fn,model="anthropic/claude-sonnet-5.5"):
   def transport(**kw):
    if case in ("invalid_json_transport","provider_exception_with_usage"):
     raise OpenRouterCallError(SECRETS[0],{
      "stage":"structured_parse" if case=="invalid_json_transport" else "transport",
      "body":{"choices":[{"message":{"content":"{not JSON " + SECRETS[1]}}],
              "usage":{"prompt_tokens":100,"completion_tokens":20,
                       "total_tokens":120,"cost":0.01}},
      "request":{"secret":SECRETS[2]},
     })
    raw,body,req,failed=call_fn(**kw)
    raw=dict(raw)
    if case=="unexpected_field":
     raw["UNTRUSTED_FIELD"]=SECRETS[1]
     raw["summary"]=SECRETS[2]
    if case=="missing_required":raw.pop("summary",None)
    if case=="invalid_findings_type":raw["findings"]=SECRETS[2]
    if case=="usage_missing":body["usage"].pop("cost",None)
    if case=="usage_nonfinite":body["usage"]["cost"]=float("nan")
    body["choices"]=[{"message":{"content":"untrusted "+SECRETS[1]}}]
    body["headers"]={"authorization":SECRETS[2]}
    return raw,body,req,failed
   try:
    return orig(api_key=api_key,payload=payload,call_fn=transport,model=model)
   except Exception as exc:
    record=diag.persist_failure(
      exc,stage="FINAL_AUDIT",run_id=case,
      input_sha256=digest_json(payload),
      source_story_sha256=payload["repaired_story_sha256"],
      output_dir=diag_dir)
    raise diag.RedactedProviderFailure(exc,record) from None
  simulation.execute_final_audit_call=fake_final
  try:
   simulation.simulate_case("repair_succeeds",output)
   raise AssertionError("Synthetic invalid final-audit result unexpectedly accepted")
  except AssertionError as exc:
   # Original simulation expects ACCEPT; our deliberate failure must be the
   # only reason for its mismatch, and all genuine output files must exist.
   result_path=output/"repair_succeeds"/"v21-bounded-quality-result.json"
   if not result_path.is_file():raise
  result=json.loads(result_path.read_text())
  record_path=diag_dir/"targeted-final-audit-diagnostic.json"
  record=json.loads(record_path.read_text())
  ledger=(output/"repair_succeeds"/"quality-call-ledger.jsonl").read_text()
  for secret in SECRETS:
   assert secret not in json.dumps(result)
   assert secret not in json.dumps(record)
   assert secret not in ledger
  assert result["status"]=="REJECT_PROVIDER_FAILURE"
  assert len(result["quality_calls"])==3
  assert [c["stage"] for c in result["quality_calls"]]==[
    "INITIAL_AUDIT","SCENE_REPAIR","FINAL_AUDIT"]
  assert result["quality_calls"][-1]["status"]=="FAILED"
  assert result["accepted_story"] is None
  assert result["state_commit_executed"] is False
  assert result["automatic_retry_executed"] is False
  assert result["automatic_second_repair_executed"] is False
  assert result["final_audit_validated"] is False
  assert record["raw_response_redacted"] is True
  assert record["story_quality_accepted"] is False
  assert record["english_master_seal_authorized"] is False
  assert record["q25_execution_authorized"] is False
  assert record["state_commit_authorized"] is False
  assert record_path.stat().st_mode & 0o777==0o600
  assert record["source_story_sha256"]==(
      result["quality_calls"][-1]["input"]["repaired_story_sha256"])
  # O_EXCL means no diagnostic overwrite/retry may alter this record.
  try:
   diag.persist_failure(RuntimeError("blocked"),
       stage="FINAL_AUDIT",run_id=case,input_sha256="x",
       source_story_sha256="x",output_dir=diag_dir)
   raise AssertionError("Replayed failure overwrote the original immutable record")
  except FileExistsError:
   pass
  final=result["quality_calls"][-1]
  rows.append({
   "case":case,
   "phase":record["phase"],
   "error_category":record["validation_diagnostic"]["category"],
   "schema_path":record["validation_diagnostic"]["schema_path"],
   "parsed_response_sha256":record["parsed_response_sha256"],
   "request_input_sha256":record["request_input_sha256"],
   "source_story_sha256":record["source_story_sha256"],
   "provider_response_sha256":record["provider_response_sha256"],
   "safe_response_shape":record["parsed_response_safe_shape"],
   "usage_accounting_complete":record["usage"]["accounting_complete"],
   "missing_usage_fields":record["usage"]["missing_fields"],
   "recorded_final_cost_usd":(
       record["usage"]["values"]["cost_usd"] if record["usage"]["values"] else None),
   "recorded_final_input_tokens":(
       record["usage"]["values"]["input_tokens"] if record["usage"]["values"] else None),
   "recorded_final_output_tokens":(
       record["usage"]["values"]["output_tokens"] if record["usage"]["values"] else None),
   "recorded_final_latency_nonnegative":(
       record["usage"]["values"]["latency_seconds"] is not None
       if record["usage"]["values"] else False),
   "model_call_attempts":len(result["quality_calls"]),
   "accounted_model_calls":result["quality_model_calls"],
   "quality_status":result["status"],
   "failed_stage":final["stage"],
   "provider_evidence_is_redacted":final["provider_evidence"]["raw_sensitive_text_stored"] is False,
   "raw_response_redacted":record["raw_response_redacted"],
   "immutable_record_preserved":True,
   "no_secrets_persisted":True,
  })
print(json.dumps({"runtime_revision":freeze["runtime_revision"],
"cases":rows},sort_keys=True,ensure_ascii=False,allow_nan=False))
"""


def _must(p,message):
    if not p:raise HarnessStop(message)


def run_original_diagnostics(*,repo_root,pinned_source_root,
                             python_executable=sys.executable):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    path=base/SOURCE_CODE_PATH
    _must(path.is_file() and not path.is_symlink()
          and path.resolve().is_relative_to(base),
          "Experimental P4.2 diagnostic adapter source missing")
    with TemporaryDirectory(prefix="story-harness-p42-") as temp:
        env=_python_runtime_env(python_executable,Path(temp))
        env["TMPDIR"]=temp
        try:
            p=subprocess.run([python_executable,"-c",LAUNCHER,str(path)],
                 cwd=source,env=env,capture_output=True,text=True,
                 encoding="utf-8",timeout=70,check=False)
        except (OSError,subprocess.TimeoutExpired) as e:
            raise HarnessStop("Original frozen v21.4 diagnostic runner unavailable") from e
        _must(p.returncode==0 and len(p.stdout)<26000,
             "P4.2 real v21 diagnostic flow failed: "+p.stderr[-350:].replace("\n"," "))
        try:result=json.loads(p.stdout)
        except ValueError as e: raise HarnessStop("Diagnostic runner returned invalid JSON") from e
    return result


def _validate_rows(value,earlier,qualified_positive):
    _must(value["runtime_revision"]=="SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and [r["case"] for r in value["cases"]]==list(CASES),
          "Incomplete v21 diagnostic scenarios")
    allowed={
      "unexpected_field":("response_validation","UNEXPECTED_FIELD"),
      "missing_required":("response_validation","MISSING_FIELD"),
      "invalid_findings_type":("response_validation","INVALID_TYPE"),
      "invalid_json_transport":("structured_parse","UNSPECIFIED"),
      "provider_exception_with_usage":("transport","UNSPECIFIED"),
      "usage_missing":("usage_validation","INVALID_USAGE"),
      "usage_nonfinite":("usage_validation","INVALID_USAGE"),
    }
    _must(len(value["cases"])==len(CASES),"P4.2 wrong test count")
    repaired_story_sha=qualified_positive["synthetic_previews"][1]["validation"]["preview_story_sha256"]
    results=[]
    for row in value["cases"]:
        label=row["case"]
        phase,category=allowed[label]
        _must(row["phase"]==phase and row["error_category"]==category
              and row["model_call_attempts"]==3
              and row["accounted_model_calls"]<=3
              and row["quality_status"]=="REJECT_PROVIDER_FAILURE"
              and row["failed_stage"]=="FINAL_AUDIT"
              and row["source_story_sha256"]==repaired_story_sha
              and row["source_story_sha256"]!=earlier["v21_frozen_contract"]["source_story_sha256"]
              and row["provider_evidence_is_redacted"] is True
              and row["raw_response_redacted"] is True
              and row["immutable_record_preserved"] is True
              and row["no_secrets_persisted"] is True,
              "P4.2 failed to quarantine final-audit unsafe response")
        expected_complete=label not in ("usage_missing","usage_nonfinite")
        _must(row["usage_accounting_complete"] is expected_complete
              and ("cost_usd" in row["missing_usage_fields"]) is (not expected_complete),
              "P4.2 invalid/missing provider usage incorrectly counted as zero")
        _must(row["recorded_final_cost_usd"] is
              (None if not expected_complete else row["recorded_final_cost_usd"]),
              "Missing/invalid final cost falsely accounted")
        if expected_complete:
            _must(row["recorded_final_cost_usd"]==0.01
                  and row["recorded_final_input_tokens"]==100
                  and row["recorded_final_output_tokens"]==20
                  and row["recorded_final_latency_nonnegative"] is True,
                  "Exact synthetic stage token/cost/latency ledger mismatch")
        else:
            _must(row["recorded_final_cost_usd"] is None,
                  "Incomplete stage spending was invented")
        if label in ("unexpected_field","missing_required","invalid_findings_type"):
            _must(isinstance(row["parsed_response_sha256"],str)
                  and len(row["parsed_response_sha256"])==64,
                  "P4.2 failed to retain SHA of schema-invalid returned raw")
        _must(isinstance(row["request_input_sha256"],str)
              and len(row["request_input_sha256"])==64,
              "P4.2 no source-bound final audit request hash")
        results.append(row)
    return results


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    p41=qualify_seal(repo_root=base,pinned_source_root=source,
                     python_executable=python_executable)
    _must(p41["stop_reason"]=="REAL_ENGLISH_MASTER_EVIDENCE_UNAVAILABLE"
          and p41["provider_calls"]==0,
          "P4.1 English Master denial prerequisite was bypassed")
    p40=load_json(secure_artifact(base,
       "evidence/story_harness_p40/pinned-v21-producer-preflight.json"))
    actual=run_original_diagnostics(repo_root=base,pinned_source_root=source,
                                    python_executable=python_executable)
    rows=_validate_rows(actual,p40,p41)
    return {
      "schema":SCHEMA,"source_commit":PINNED_SOURCE_COMMIT,
      "mode":"EXPERIMENTAL_V21_5_REDACTED_FAILURE_ONLY",
      "frozen_v21_4_source_modified":False,
      "original_v21_4_adapter_and_runtime_exercised":True,
      "experimental_diagnostic_adapter_sha256":digest((base/SOURCE_CODE_PATH).read_bytes()),
      "historical_v21_3_failed_provider_response_recovered":False,
      "real_paid_history_preserved_as_rejected":True,
      "p41_quality_denial_receipt_sha256":digest(canonical_bytes(p41)),
      "diagnostic_case_count":len(rows),
      "failure_diagnostics":rows,
      "all_failure_receipts_immutable_redacted":True,
      "raw_provider_payload_or_secret_persisted":False,
      "provider_failure_auto_retried":False,
      "old_unbounded_repair_loop_restored":False,
      "last_quality_status":"REJECT_PROVIDER_FAILURE",
      "real_story_quality_accepted":False,
      "english_master_seal_authorized":False,
      "q25_extraction_authorized":False,
      "state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,"provider_cost_usd":"0",
      "stop_reason":"REAL_QUALITY_NOT_ACCEPTED_DIAGNOSTIC_READY",
      "state":"STOPPED_WITH_REDACTED_FAILURE_EVIDENCE",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    a=p.parse_args()
    base=Path(a.repo_root).resolve(strict=True)
    result=qualify(repo_root=base,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(base,a.verify_report))==result,
              "P4.2 immutable diagnostic summary changed")
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":main()

