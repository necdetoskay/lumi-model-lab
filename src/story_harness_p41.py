"""P4.1: English Master positive-mechanics contract, real story acceptance DENIED.

The genuine pinned v21 quality engine yields synthetic clean/repaired ACCEPTs.
Both test a typed seal *preview* and ledger; neither can become a real seal.
Real story quality requires independent authenticated review evidence and a
separate pinned trust registry version, currently empty. No Q25 handoff.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from src.story_harness_p22 import _python_runtime_env
from src.story_harness_p30 import PINNED_SOURCE_COMMIT
from src.story_harness_p40 import qualify as qualify_bounded
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA="lumi.story-harness-p41-seal-positive-mechanics.v1"
REGISTRY="configs/story_harness_p41_seal_trust_registry.json"
REGISTRY_SHA="173930084062b72241afe097bbe0ec137a8b9130f82cb69fa6081304fa641756"
CANDIDATE_SCHEMA="lumi.english-master-seal-candidate.v1"
Q25_SCHEMA="lumi.q25-source-request.v1"
SYNTHETIC_ORIGIN="OFFLINE_MOCK_TRANSPORT_ONLY"
REAL_ORIGIN="REAL_PROVIDER_WITH_AUTHENTICATED_INDEPENDENT_REVIEW"
AUDIT_FAMILIES=(
    "physical_feasibility", "causal_logic", "state_continuity",
    "spatial_continuity", "temporal_continuity", "epistemic_continuity",
    "response_obligation", "closure_obligation", "canon_consistency",
    "age_appropriateness", "spine_obligation", "narrative_quality",
)
CASE_NAMES=("clean","repair_succeeds")
STAGES=("INITIAL_AUDIT","SCENE_REPAIR","FINAL_AUDIT")
STAGE_LIMIT={"INITIAL_AUDIT":"0.04","SCENE_REPAIR":"0.035","FINAL_AUDIT":"0.025"}
_SYNTHETIC_SCRIPT=r"""
import hashlib,json,os,socket,tempfile
from pathlib import Path
def deny(*a,**kw): raise RuntimeError("P4.1 network forbidden")
socket.create_connection=deny
socket.socket.connect=deny
socket.socket.connect_ex=deny
from src.spineforge_v21_freeze import verify_v21_runtime
from src.spineforge_v21_simulation import simulate_case
from src.spineforge_v21_constraints import digest_json
freeze=verify_v21_runtime()
out=[]
with tempfile.TemporaryDirectory(prefix="p41-original-v21-",dir=os.environ.get("TMPDIR")) as tmp:
 for case in ["clean","repair_succeeds"]:
  row=simulate_case(case,Path(tmp))
  r=json.loads((Path(tmp)/case/"v21-bounded-quality-result.json").read_text())
  e=json.loads((Path(tmp)/case/"v21-bounded-quality-envelope.json").read_text())
  assert r["accepted_story"] is not None
  assert r["accepted_story_sha256"]==hashlib.sha256(r["accepted_story"].encode()).hexdigest()
  calls=[]
  for q in r["quality_calls"]:
   assert q["input_sha256"]==digest_json(q["input"])
   assert q["response_sha256"]==digest_json(q["response"])
   assert isinstance(q["usage"]["latency_seconds"],(float,int))
   assert q["usage"]["latency_seconds"]>=0
   stable_usage={k:v for k,v in q["usage"].items() if k!="latency_seconds"}
   calls.append({"stage":q["stage"],"status":q["status"],
     "digest_integrity_verified_in_original_runtime":True,
     "usage":stable_usage,"origin":"MOCK",
     "source_artifact_id":q["input"].get("source_story_artifact_id"),
     "source_story_sha256":q["input"].get("source_story_sha256"),
     "approved_spine_hash":q["input"].get("approved_spine_hash"),
     "final_audit_payload_keys": sorted(q["input"]) if q["stage"]=="FINAL_AUDIT" else []})
  out.append({
   "case":case,
   "actual_runtime_quality_result_schema":r["schema"],
   "stable_quality_projection_sha256":hashlib.sha256(json.dumps({
      "schema":r["schema"],"status":r["status"],
      "accepted_story_sha256":r["accepted_story_sha256"],
      "source_story_sha256":e["source_story_sha256"],
      "quality_usage_rollup":{k:v for k,v in r["quality_usage_rollup"].items() if k!="latency_seconds"},
      "quality_model_calls":r["quality_model_calls"],
      "call_stages": [{"stage":c["stage"],"status":c["status"],
                       "usage":c["usage"]} for c in calls],
   },ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
   "actual_runtime_result_status":r["status"],
   "source_story_artifact_id":e["source_story_artifact_id"],
   "source_story_sha256":e["source_story_sha256"],
   "accepted_story_sha256":r["accepted_story_sha256"],
   "accepted_story_bytes":len(r["accepted_story"].encode("utf8")),
   "quality_model_calls":r["quality_model_calls"],
   "repair_count":r["repair_count"],
   "final_audit_executed":r["final_audit_executed"],
   "final_audit_scope":r["final_audit_scope"],
   "final_audit_validated":r["final_audit_validated"],
   "rewrite_outside_cluster_unchanged":r["rewrite"]["outside_cluster_unchanged"] if r["rewrite"] else None,
   "quality_usage_rollup":{k:v for k,v in r["quality_usage_rollup"].items() if k!="latency_seconds"},
   "call_records":calls,
   "envelope_simulation":e["simulation"],
   "envelope_paid_authorization":e["explicit_paid_authorization"],
   "envelope_state_commit_executed":e["state_commit_executed"],
   "original_scenario_status":row["status"]
  })
print(json.dumps({"runtime_revision":freeze["runtime_revision"],
"synthetic_cases":out},sort_keys=True,ensure_ascii=False))
"""


def _must(ok,reason):
    if not ok: raise HarnessStop(reason)


def _verify_registry(root,override=None):
    raw=secure_artifact(root,REGISTRY)
    _must(digest(raw)==REGISTRY_SHA,"P4.1 immutable seal trust registry was changed")
    r=load_json(raw)
    _must(override is None or override==r,"Supplied trust roots differ from source-pinned registry")
    _must(r["schema"]=="lumi.story-harness-p41-seal-trust-registry.v1"
          and r["source_commit"]==PINNED_SOURCE_COMMIT
          and r["reader_exact_age"]==12
          and r["runtime_revision"]=="SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4"
          and r["max_quality_model_calls"]==3 and r["max_scene_repairs"]==1
          and r["per_stage_spend_limits_usd"]=={
              "initial_audit":0.04,"scene_repair":0.035,"final_audit":0.025},
          "P4.1 seal contract metadata differs from frozen quality source")
    _must(set(r["original_v21_stable_projection_sha256_by_case"])==set(CASE_NAMES)
          and all(isinstance(v,str) and len(v)==64
                  for v in r["original_v21_stable_projection_sha256_by_case"].values()),
          "P4.1 real v21 mock-positive baseline hashes are not pinned")
    for key in ("trusted_real_quality_receipt_sha256s",
                "trusted_independent_reviewer_attestation_sha256s",
                "registered_english_master_seal_sha256s",
                "registered_q25_source_sha256s"):
        _must(r[key]==[], "A real seal or review trust root was fabricated in the P4.1 cohort")
    for key in ("synthetic_fixtures_can_authorize_real_sealing",
                "synthetic_fixtures_can_authorize_q25",
                "automatic_paid_execution_authorized",
                "production_story_state_write_authorized"):
        _must(r[key] is False,"P4.1 source registry grants forbidden execution authority")
    _must(r["real_signature_or_external_review_verification_required"] is True,
          "P4.1 removed independent attestation requirement")
    return r


def _isolated_synthetic_quality(source,python_executable):
    with TemporaryDirectory(prefix="lumi-p41-",) as td:
        env=_python_runtime_env(python_executable,Path(td))
        env["TMPDIR"]=td
        try:
            p=subprocess.run([python_executable,"-c",_SYNTHETIC_SCRIPT],
                             cwd=source,env=env,stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,encoding="utf-8",
                             timeout=40,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise HarnessStop("Original frozen v21 simulation could not be executed") from exc
        _must(p.returncode==0 and len(p.stdout)<64000,
              "Frozen positive-mechanics simulation rejected: "+p.stderr[-250:].replace("\n"," "))
        try: result=json.loads(p.stdout)
        except ValueError as exc: raise HarnessStop("Synthetic quality output not JSON") from exc
    return result


def _decimal(x):
    _must(type(x) in (int,float,str) and not isinstance(x,bool),
          "Non-numeric usage value")
    try: result=Decimal(str(x))
    except InvalidOperation as exc: raise HarnessStop("Invalid usage amount") from exc
    _must(result.is_finite() and result>=0,"Invalid negative/nonfinite usage")
    return result


def _verify_synthetic_runtime_case(item,trust):
    _must(item["case"] in CASE_NAMES
          and item["actual_runtime_quality_result_schema"]=="spineforge-v21-bounded-quality-result.v2"
          and item["actual_runtime_result_status"]=="ACCEPT"
          and item["original_scenario_status"]=="ACCEPT"
          and item["envelope_simulation"] is True
          and item["envelope_paid_authorization"] is False
          and item["envelope_state_commit_executed"] is False,
          "Fixture is not a legitimate non-authorizing original v21 result")
    _must(item["stable_quality_projection_sha256"]==
          trust["original_v21_stable_projection_sha256_by_case"][item["case"]],
          "Original v21 synthetic quality-result fingerprint changed")
    _must(item["source_story_artifact_id"]==trust["source_story_artifact_id"]
          and item["source_story_sha256"]==trust["source_story_sha256"],
          "Synthetic original v21 source does not match frozen island")
    _must(isinstance(item["accepted_story_sha256"],str)
          and len(item["accepted_story_sha256"])==64
          and isinstance(item["stable_quality_projection_sha256"],str)
          and len(item["stable_quality_projection_sha256"])==64
          and type(item["accepted_story_bytes"]) is int
          and item["accepted_story_bytes"]>1000,
          "Story SHA or text-size source evidence is missing")
    calls=item["call_records"]
    expected_stages=["INITIAL_AUDIT"] if item["case"]=="clean" else list(STAGES)
    _must([r["stage"] for r in calls]==expected_stages
          and item["quality_model_calls"]==len(calls)
          and item["repair_count"]==(0 if item["case"]=="clean" else 1)
          and item["final_audit_executed"] is (item["case"]!="clean")
          and item["final_audit_validated"] is (item["case"]!="clean"),
          "Unexpected stage count, second repair or skipped final audit")
    if item["case"]=="clean":
        _must(item["accepted_story_sha256"]==trust["source_story_sha256"]
              and item["final_audit_scope"] is None
              and item["rewrite_outside_cluster_unchanged"] is None,
              "Clean path forged new story bytes")
    else:
        _must(item["accepted_story_sha256"]!=trust["source_story_sha256"]
              and item["final_audit_scope"]=="REPAIRED_SCENE_PLUS_BOUNDARIES"
              and item["rewrite_outside_cluster_unchanged"] is True,
              "Repaired path did not preserve outside-cluster source")
    account=item["quality_usage_rollup"]
    _must(account["accounting_complete"] is True
          and account["api_calls"]==len(calls)
          and account["total_tokens"]==sum(r["usage"]["total_tokens"] for r in calls)
          and account["input_tokens"]==sum(r["usage"]["input_tokens"] for r in calls)
          and account["output_tokens"]==sum(r["usage"]["output_tokens"] for r in calls),
          "Synthetic cost/token totals are inconsistent")
    _must(_decimal(account["cost_usd"])==sum(
          (_decimal(r["usage"]["cost_usd"]) for r in calls),Decimal(0))
          and _decimal(account["confirmed_cost_usd"])==_decimal(account["cost_usd"])
          and _decimal(account["cost_usd"])<=Decimal("0.10"),
          "Cost rollup invalid or total ceiling violated")
    for row in calls:
        stage=row["stage"]
        u=row["usage"]
        _must(row["status"]=="COMPLETED" and row["origin"]=="MOCK"
              and u["stage"]==stage and u["api_calls"]==1
              and row["digest_integrity_verified_in_original_runtime"] is True
              and type(u["total_tokens"]) is int
              and u["total_tokens"]==u["input_tokens"]+u["output_tokens"]
              and _decimal(u["cost_usd"])<=Decimal(STAGE_LIMIT[stage])
              and "latency_seconds" not in u,
              "Original call ledger fails stage budget or evidence contract")
        if stage=="INITIAL_AUDIT":
            _must(row["source_artifact_id"]==trust["source_story_artifact_id"]
                  and row["source_story_sha256"]==trust["source_story_sha256"]
                  and row["approved_spine_hash"]==trust["approved_spine_hash"],
                  "Original initial audit was not grounded in approved same-story source")
        if stage=="FINAL_AUDIT":
            _must("full_story" not in row["final_audit_payload_keys"]
                  and "story_segments" not in row["final_audit_payload_keys"],
                  "Full-story final audit is forbidden after one scene repair")
    return True


def _make_preview(item,trust):
    return {
      "schema":CANDIDATE_SCHEMA,
      "evidence_class":"SYNTHETIC_MECHANICAL_ONLY",
      "source":{
        "source_commit":trust["source_commit"],
        "source_story_artifact_id":item["source_story_artifact_id"],
        "source_story_sha256":item["source_story_sha256"],
        "approved_spine_hash":trust["approved_spine_hash"],
        "approval_id":trust["approval_id"],
        "context_pack_id":trust["context_pack_id"],
        "context_fingerprint":trust["context_fingerprint"],
        "reader_exact_age":12,
      },
      "proposed_english_text":{
        "sha256":item["accepted_story_sha256"],
        "bytes":item["accepted_story_bytes"],
        "immutable_verified_in_real_provider_archive":False,
      },
      "quality":{
        "source":"REAL_ORIGINAL_V21_ENGINE_WITH_FAKE_TRANSPORT",
        "status":"ACCEPT",
        "stable_quality_projection_sha256":item["stable_quality_projection_sha256"],
        "model_call_count":item["quality_model_calls"],
        "repair_count":item["repair_count"],
        "final_audit_executed":item["final_audit_executed"],
        "final_audit_scope":item["final_audit_scope"],
        "call_evidence_digest_sha256":digest(canonical_bytes(item["call_records"])),
        "simulated_usage":deepcopy(item["quality_usage_rollup"]),
      },
      "independent_review":{
        "schema":"lumi.english-master-review-attestation.v1",
        "origin":"SYNTHETIC_NO_REAL_REVIEWER",
        "blocking_families_expected":list(AUDIT_FAMILIES),
        "same_story_source_hash":item["source_story_sha256"],
        "same_story_accepted_hash":item["accepted_story_sha256"],
        "real_reviewer_signature_verified":False,
        "real_semantic_quality_confirmed":False,
      },
      "provenance":{
        "provider_origin":SYNTHETIC_ORIGIN,
        "real_provider_response_authenticated":False,
        "real_token_cost_ledger_authenticated":False,
        "production_state_mutation":False,
      },
      "seal":{
        "status":"PREVIEW_NOT_A_SEAL",
        "immutable_seal_artifact_id":None,
        "trusted_seal_signature":None,
      },
    }


def validate_positive_mechanics(candidate,truth,trust):
    _must(candidate==_make_preview(truth,trust),
          "Synthetic English Master candidate fields, usage or lineage were tampered with")
    _verify_synthetic_runtime_case(truth,trust)
    return {
      "candidate_schema":CANDIDATE_SCHEMA,
      "synthetic_contract_shape_valid":True,
      "synthetic_quality_status":"ACCEPT",
      "synthetic_quality_call_count":truth["quality_model_calls"],
      "preview_story_sha256":candidate["proposed_english_text"]["sha256"],
      "real_quality_evidence_verified":False,
      "real_semantic_reviewer_authenticated":False,
      "english_master_seal_admitted":False,
      "q25_source_admitted":False,
    }


def build_q25_source_request_preview(candidate,trust):
    """Typed and intentionally DENIED read-only schema rehearsal, not a handoff."""
    _must(candidate["schema"]==CANDIDATE_SCHEMA
          and candidate["evidence_class"]=="SYNTHETIC_MECHANICAL_ONLY"
          and candidate["seal"]["status"]=="PREVIEW_NOT_A_SEAL"
          and candidate["seal"]["immutable_seal_artifact_id"] is None
          and candidate["source"]["source_story_sha256"]==trust["source_story_sha256"]
          and candidate["source"]["approved_spine_hash"]==trust["approved_spine_hash"],
          "Q25 preview may not use a foreign or self-sealed source")
    return {
      "schema":Q25_SCHEMA,
      "mode":"READ_ONLY_DENIAL_PREVIEW",
      "admission_status":"DENIED_NOT_A_REAL_SEAL",
      "source_commit":trust["source_commit"],
      "approved_spine_hash":trust["approved_spine_hash"],
      "context_pack_id":trust["context_pack_id"],
      "context_fingerprint":trust["context_fingerprint"],
      "source_story_artifact_id":trust["source_story_artifact_id"],
      "preview_story_sha256":candidate["proposed_english_text"]["sha256"],
      "verified_english_master_seal_artifact_id":None,
      "actual_english_master_verified":False,
      "q25_extraction_authorized":False,
      "paid_provider_dispatch_authorized":False,
      "canonical_state_commit_authorized":False,
    }


def validate_q25_request_preview(request,candidate,trust):
    _must(request==build_q25_source_request_preview(candidate,trust)
          and request["admission_status"]=="DENIED_NOT_A_REAL_SEAL"
          and request["q25_extraction_authorized"] is False,
          "Forged Q25 admission request or source authority")
    return True


def verify_actual_english_master_seal(candidate,trust,*,source_preflight=None):
    """A future registered positive seal must be independently trust-rooted.

    The current frozen registry is intentionally empty. Caller-supplied fake
    trust dictionaries cannot be used: checked via pin to the source cohort.
    """
    _must(source_preflight is not None and
          source_preflight["stop_reason"]=="REAL_BOUNDED_QUALITY_ACCEPT_MISSING",
          "Real-seal verifier requires authentic P4.0 prereq")
    _must(candidate.get("schema")==CANDIDATE_SCHEMA
          and candidate.get("provenance",{}).get("provider_origin")==REAL_ORIGIN,
          "A mock fixture or forged origin may not authorize an English Master seal")
    # Before a future real positive-capable version, require actual externally
    # reviewed trust roots. Never infer trust from self-reported signed=true.
    _must(trust["trusted_real_quality_receipt_sha256s"]
          and trust["trusted_independent_reviewer_attestation_sha256s"]
          and trust["registered_english_master_seal_sha256s"],
          "No verified real provider, reviewer and English Master trust roots registered")
    raise HarnessStop("Authenticated reviewer signature and real source seal verifier not yet qualified")


def build_q25_source_request(*,verified_real_seal,trust):
    """Separate read-only Q25 gate, intentionally closed for this history."""
    _must(trust["registered_q25_source_sha256s"],
          "No actual pinned Q25 admission authority registered")
    _must(verified_real_seal.get("schema")=="lumi.english-master-verified-seal.v1"
          and verified_real_seal.get("real_quality_verified") is True,
          "Q25 must consume a verified real English Master, not a candidate")
    raise HarnessStop("Real Q25 seal-bound request verifier not yet qualified")


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable,
            candidate_override=None,registry_override=None):
    base=Path(repo_root).resolve(strict=True)
    source=Path(pinned_source_root).resolve(strict=True)
    trust=_verify_registry(base,registry_override)
    prev=qualify_bounded(repo_root=base,pinned_source_root=source,
                         python_executable=python_executable)
    _must(prev["stop_reason"]=="REAL_BOUNDED_QUALITY_ACCEPT_MISSING"
          and prev["synthetic_ACCEPT_is_genuine_story_quality"] is False
          and prev["provider_calls"]==0,
          "P4.0 same-story producer preflight failed")
    _must(trust["source_story_artifact_id"]==
          load_json(secure_artifact(base,
          "evidence/story_harness_p32/pinned-english-master-denial-receipt.json"))[
          "terminal_candidate"]["candidate_artifact_id"]
          and trust["source_story_sha256"]==
          prev["v21_frozen_contract"]["source_story_sha256"],
          "English Master trust registry did not bind the same island source")
    observed=_isolated_synthetic_quality(source,python_executable)
    _must(observed["runtime_revision"]==trust["runtime_revision"]
          and [r["case"] for r in observed["synthetic_cases"]]==list(CASE_NAMES),
          "Authentic v21 positive fixture source or scenarios diverged")
    previews=[]
    for idx,item in enumerate(observed["synthetic_cases"]):
        _verify_synthetic_runtime_case(item,trust)
        expected=_make_preview(item,trust)
        candidate=(candidate_override if idx==0 and candidate_override is not None else expected)
        verified=validate_positive_mechanics(candidate,item,trust)
        q25_preview=build_q25_source_request_preview(candidate,trust)
        _must(validate_q25_request_preview(q25_preview,candidate,trust),
              "Invalid typed Q25 denial preview")
        previews.append({
          "q25_denial_request_preview_sha256":digest(canonical_bytes(q25_preview)),
          "q25_denial_request_preview_verified":True,
          "synthetic_case":item["case"],
          "candidate_sha256":digest(canonical_bytes(candidate)),
          "quality_result_sha256":item["stable_quality_projection_sha256"],
          "validation":verified,
          "seal_issued":False,
        })
    return {
      "schema":SCHEMA,
      "mode":"SYNTHETIC_POSITIVE_SEAL_MECHANICS_NEVER_AUTHORIZING",
      "source_commit":PINNED_SOURCE_COMMIT,
      "trust_registry_sha256":REGISTRY_SHA,
      "p40_real_v21_preflight_receipt_sha256":digest(canonical_bytes(prev)),
      "trusted_real_quality_evidence_registered":False,
      "authenticated_reviewer_attestation_registered":False,
      "independently_verified_seal_registered":False,
      "trusted_q25_admission_registered":False,
      "synthetic_positive_case_count":2,
      "synthetic_previews":previews,
      "actual_positive_model_quality_evidence_present":False,
      "actual_reviewer_semantic_accept_present":False,
      "real_english_master_seal_verified":False,
      "real_english_master_seal_emitted":False,
      "q25_source_request_produced":False,
      "q25_source_request_schema":Q25_SCHEMA,
      "q25_read_only_handoff_contract_defined":True,
      "stop_reason":"REAL_ENGLISH_MASTER_EVIDENCE_UNAVAILABLE",
      "state":"STOPPED_REAL_SEAL_AND_Q25_NOT_QUALIFIED",
      "paid_execution_authorized":False,
      "english_master_seal_authorized":False,
      "q25_admission_authorized":False,
      "state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,
      "provider_cost_usd":"0",
    }


def verify_report(candidate,*,repo_root,pinned_source_root,python_executable=sys.executable):
    actual=qualify(repo_root=repo_root,pinned_source_root=pinned_source_root,
                   python_executable=python_executable)
    _must(candidate==actual,"P4.1 stored seal mechanical proof differs from pinned source")
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--pinned-source-root",required=True)
    p.add_argument("--verify-report")
    a=p.parse_args()
    root=Path(a.repo_root).resolve(strict=True)
    report=qualify(repo_root=root,pinned_source_root=a.pinned_source_root)
    if a.verify_report:
        _must(load_json(secure_artifact(root,a.verify_report))==report,
              "P4.1 stored receipt was altered")
    print(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()

