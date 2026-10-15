"""P4.4 zero-cost genuine island story forensic + bounded paid dispatch readiness.

Exercises P4.3 first. It quotes original immutable 2,407-word story and the
genuinely failed paid v21 repair, then calculates cost *exposure* with published
REFERENCE prices. No inferences, payment, reviewer ACCEPT, seal or Q25.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_FLOOR
import hashlib
import json
from pathlib import Path
import re
import sys

from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_p43 import qualify as qualify_offline_runner
from src.story_harness_v1 import HarnessStop,canonical_bytes,digest,load_json,secure_artifact

SCHEMA="lumi.story-harness-p44-source-anchored-story-and-cost-preflight.v1"
MANIFEST="configs/story_harness_p44_story_quality_preflight.json"
MANIFEST_SHA="68f47098ceedf2392eb6f1d4f4758664b8ddcbb35b5f45ed7370ab33d6ae3d22"
REAL_FAILURE_STATUS="REJECT_PROVIDER_FAILURE"
REASON="NOT_READY_FOR_REAL_BOUNDED_QUALITY_ATTEMPT"
_EXPECTED_FINDING_IDS=("MECH-001","MECH-002","MECH-003","MECH-004",
                        "MECH-005","ART-001","NARR-001")
_STAGE_NAMES=("INITIAL_AUDIT","SCENE_REPAIR","FINAL_AUDIT")


def _must(value, reason):
    if not value:raise HarnessStop(reason)


def _dec(value):
    _must(type(value) in (str,int,float) and not isinstance(value,bool),
          "Invalid price or accounting value type")
    x=Decimal(str(value))
    _must(x.is_finite() and x>=0,"Negative/nonfinite price or tokens")
    return x


def _source_bytes(root,role):
    _must(isinstance(role,dict) and set(role)=={"path","sha256"},
          "Missing source role")
    name=role["path"]
    _must(isinstance(name,str) and name.startswith("evidence/")
          and ".." not in Path(name).parts and "\\" not in name
          and not Path(name).is_absolute(),
          "Unsafe source artifact path")
    p=root
    for part in Path(name).parts:
        p=p/part
        _must(not p.is_symlink(),"Symlink historical evidence refused")
    _must(p.is_file() and p.resolve().is_relative_to(root)
          and p.stat().st_size<550000,
          "Historical evidence file missing or oversized")
    buf=p.read_bytes()
    _must(digest(buf)==role["sha256"],
          "Original archived text or paid review SHA was mutated")
    return buf


def _policy(root):
    b=secure_artifact(root,MANIFEST)
    _must(digest(b)==MANIFEST_SHA,"Source-anchored P4.4 review/price registry changed")
    m=load_json(b)
    _must(set(m)=={
      "schema","source_commit","story_source","original_paid_v21_result",
      "original_paid_review","expected_story_sha256",
      "failed_paid_replacement_scene_sha256","approved_spine_hash",
      "source_story_artifact_id","reader_age","min_story_words",
      "max_story_words","editorial_review_trust","manual_source_anchored_findings",
      "current_provider_price_reference","allowed_original_runtime_output_caps",
      "post_usage_stage_caps_usd","target_quality_total_usd",
      "max_model_calls","max_scene_repairs","real_dispatch_enabled",
      "real_budget_authorization_id","provider_credentials_may_be_used",
      "english_master_or_q25_enabled","automatic_retries_enabled",
      "original_story_mutation_authorized","quality_target_overrun_user_permitted",
      "quality_target_overrun_permission_scope",
      "authorized_paid_spend_ceiling_usd",
      "paid_spend_ceiling_must_be_defined_before_dispatch",
      "user_permission_is_unlimited_spend",
      "provider_price_reference_verification",
    },"Wrong P4.4 immutable profile schema")
    _must(m["schema"]=="lumi.story-harness-p44-semantic-preflight-registry.v1"
          and m["source_commit"]==PINNED_SOURCE_COMMIT
          and m["reader_age"]==12
          and m["min_story_words"]==1600 and m["max_story_words"]==2500
          and m["editorial_review_trust"]=="UNSIGNED_PRELIMINARY_HUMAN_READ_NOT_QUALITY_ACCEPT"
          and m["max_model_calls"]==3 and m["max_scene_repairs"]==1
          and m["real_dispatch_enabled"] is False
          and m["real_budget_authorization_id"] is None
          and m["provider_credentials_may_be_used"] is False
          and m["english_master_or_q25_enabled"] is False
          and m["automatic_retries_enabled"] is False
          and m["original_story_mutation_authorized"] is False
          and m["quality_target_overrun_user_permitted"] is True
          and m["quality_target_overrun_permission_scope"]==
              "SINGLE_ATTEMPT_OVERRUN_CONSENT_NOT_AN_API_EXECUTION_GRANT"
          and m["authorized_paid_spend_ceiling_usd"] is None
          and m["paid_spend_ceiling_must_be_defined_before_dispatch"] is True
          and m["user_permission_is_unlimited_spend"] is False,
          "User-approved $0.10 overrun cannot be treated as unlimited spending or a paid run grant")
    _must(m["allowed_original_runtime_output_caps"]==
        {"INITIAL_AUDIT":3000,"SCENE_REPAIR":3500,"FINAL_AUDIT":1800}
       and m["post_usage_stage_caps_usd"]==
        {"INITIAL_AUDIT":0.04,"SCENE_REPAIR":0.035,"FINAL_AUDIT":0.025}
       and m["target_quality_total_usd"]==0.1,
       "Historical 3-call topology and stage budget were rewritten")
    quote=m["current_provider_price_reference"]
    _must(quote["provider"]=="OpenRouter"
          and quote["model"]=="anthropic/claude-sonnet-5.5"
          and quote["observed_on"]=="2026-10-13"
          and quote["public_page"]==
            "https://openrouter.ai/anthropic/claude-sonnet-5.5/providers"
          and quote["input_usd_per_1m"]==2.0
          and quote["output_usd_per_1m"]==10.0
          and quote["quote_status"]=="PUBLIC_REFERENCE_ONLY_NOT_RUNTIME_VERIFIED"
          and quote["cache_tier_and_reasoning_provider_fees_not_contractually_capped"] is True,
          "Indicative public provider price was promoted to verified paid grant")
    return m


def _validate_source_anchored_findings(m,story,repaired):
    fs=m["manual_source_anchored_findings"]
    _must([f["id"] for f in fs]==list(_EXPECTED_FINDING_IDS),
          "Required source-anchored quality findings missing")
    resolutions=[]
    for row in fs:
        origin=row["source"]
        _must(origin in ("original_story_c10","failed_v21_paid_scene_repair"),
              "Foreign story/editorial annotation")
        s=story if origin=="original_story_c10" else repaired
        start,end=row["char_start"],row["char_end"]
        _must(type(start) is int and type(end) is int
              and 0<=start<end<=len(s)
              and row["quote"]==s[start:end]
              and digest((s+"\n").encode("utf8") if
                        origin=="original_story_c10" else s.encode("utf8"))==
                    row["evidence_source_sha256"]
              and len(row["finding"])>=55
              and len(row["minimum_acceptance_obligation"])>=50,
              "Stale, non-source-anchored, or ungrounded editorial quote")
        _must(row["classification"] in ("BLOCKING","ADVISORY")
              and row["family"] in ("PHYSICAL_CAUSAL",
                                    "SPATIAL_CONTINUITY",
                                    "STATE_CONTINUITY","AGE_NARRATIVE"),
              "Unreviewed blocker taxonomy")
        resolutions.append({
          "id":row["id"],"classification":row["classification"],
          "source":origin,"family":row["family"],
          "quote_sha256":digest(row["quote"].encode("utf8")),
          "quote_char_start":start,"quote_char_end":end,
          "acceptance_obligation":row["minimum_acceptance_obligation"],
          "independent_semantic_accept_proven":False,
        })
    _must(sum(x["classification"]=="BLOCKING" for x in resolutions)==5,
          "Bridge causal/spatial defects incorrectly dismissed")
    return resolutions


def _genuine_history(m,src):
    path="evidence/spineforge-v21-paid-quality/37230896244/v21-bounded-quality-result.json"
    _must(m["original_paid_v21_result"]["path"]==path,
          "Wrong real paid quality attempt substituted")
    paid=load_json(_source_bytes(src,m["original_paid_v21_result"]))
    storypath="evidence/spineforge-v20-paid-writer/37204419845/age12-island-v20-story-quality-repair-c10-story.txt"
    _must(m["story_source"]["path"]==storypath,
          "Different island story source substituted")
    original=_source_bytes(src,m["story_source"]).decode("utf8").rstrip("\n")
    _must(digest(original.encode("utf8"))==m["expected_story_sha256"],
          "Incorrect island prose text SHA")
    actual_words=len(original.split())
    _must(m["min_story_words"]<=actual_words<=m["max_story_words"],
          "Frozen story does not match target age word range")
    _must(paid["status"]==REAL_FAILURE_STATUS
          and paid["failure_reason"]=="FINAL_AUDIT: AdapterResponseError"
          and paid["quality_model_calls"]==3
          and paid["repair_count"]==1
          and paid["final_audit_executed"] is True
          and paid["accepted_story"] is None
          and paid["accepted_story_sha256"] is None
          and paid["state_commit_executed"] is False,
          "Real paid story-quality failure was reclassified as accepted")
    calls=paid["quality_calls"]
    _must([(r["stage"],r["status"]) for r in calls]==[
        ("INITIAL_AUDIT","COMPLETED"),
        ("SCENE_REPAIR","COMPLETED"),
        ("FINAL_AUDIT","FAILED")],
        "Historical real 3-stage trace rewritten")
    first=calls[0]
    _must(first["input"]["source_story_sha256"]==m["expected_story_sha256"]
          and first["input"]["approved_spine_hash"]==m["approved_spine_hash"]
          and len(first["response"]["findings"])==1
          and first["response"]["findings"][0]["family"]=="physical_feasibility"
          and first["response"]["findings"][0]["repair_scope"]=="SCENE_REPAIR"
          and first["response"]["findings"][0]["span_ids"]==
              ["S167","S172","S173","S175"]
          and first["response"]["findings"][0]["severity"]=="serious",
          "Original real paid initial physical audit no longer matches evidence")
    changed=calls[1]
    _must(changed["input"]["source_story_sha256"]==m["expected_story_sha256"]
          and changed["input"]["approved_spine_hash"]==m["approved_spine_hash"]
          and changed["input"]["scene_cluster"]["start_span_id"]=="S159"
          and changed["input"]["scene_cluster"]["end_span_id"]=="S177"
          and changed["input"]["entry_boundary"]["span_id"]=="S158"
          and changed["input"]["exit_boundary"]["span_id"]=="S178",
          "Original bounded scene repair review boundary changed")
    repaired=changed["response"]["replacement_scene"]
    _must(digest(repaired.encode("utf8"))==
          m["failed_paid_replacement_scene_sha256"],
          "Failed paid repair text changed")
    review=_source_bytes(src,m["original_paid_review"]).decode("utf8")
    _must("AdapterResponseError" in review,
          "Historic paid experiment missing exact failed final-audit review")
    _must(paid["quality_usage_rollup"]["cost_usd"]==0.057988
          and paid["quality_usage_rollup"]["total_tokens"]==21870,
          "Historical billing ledger cannot be rewritten")
    return original,repaired,paid,actual_words


def _exposure(m,paid):
    price=m["current_provider_price_reference"]
    pin=_dec(price["input_usd_per_1m"])/Decimal(1000000)
    pout=_dec(price["output_usd_per_1m"])/Decimal(1000000)
    observed=paid["quality_calls"]
    _must([x["stage"] for x in observed]==list(_STAGE_NAMES),
          "Wrong cost scenario staging")
    stage_rows=[]
    total_actual=Decimal(0)
    total_exposure=Decimal(0)
    for call in observed:
        name=call["stage"]
        u=call["usage"]
        input_tokens=u["input_tokens"]
        output_tokens=u["output_tokens"]
        _must(type(input_tokens) is int and type(output_tokens) is int
              and input_tokens>=0 and output_tokens>=0
              and type(u["api_calls"]) is int and u["api_calls"]==1,
              "Source token accounting missing or noninteger")
        historical=_dec(input_tokens)*pin+_dec(output_tokens)*pout
        reported=_dec(u["cost_usd"])
        _must(historical==reported,"Pinned old provider usage disagrees with price reference")
        cap_tokens=m["allowed_original_runtime_output_caps"][name]
        output_max=_dec(cap_tokens)
        stage_exposure=_dec(input_tokens)*pin+output_max*pout
        stage_cap=_dec(m["post_usage_stage_caps_usd"][name])
        _must(output_max>=_dec(output_tokens),"Stage historical output exceeds frozen cap")
        # Compute max output to remain inside THIS stage cap if historical
        # input were unchanged. This cannot be a promised hard cap.
        affordable=(stage_cap-_dec(input_tokens)*pin)/pout
        affordable=max(Decimal(0),affordable.to_integral_value(rounding=ROUND_FLOOR))
        stage_rows.append({
            "stage":name,
            "historical_input_tokens":input_tokens,
            "historical_output_tokens":output_tokens,
            "original_runtime_output_cap_tokens":cap_tokens,
            "public_reference_repriced_historical_cost_usd":float(historical),
            "reported_paid_historical_cost_usd":u["cost_usd"],
            "conditional_exposure_if_historical_input_and_max_output_usd":
               float(stage_exposure),
            "post_usage_stage_cap_usd":float(stage_cap),
            "conditional_exposure_exceeds_stage_target":stage_exposure>stage_cap,
            "only_if_input_unchanged_max_output_to_meet_target":int(affordable),
            "price_or_input_hard_spend_guaranteed":False,
        })
        total_actual+=historical
        total_exposure+=stage_exposure
    _must(total_actual==Decimal("0.057988")
          and total_exposure==Decimal("0.123178"),
          "Public reference cost arithmetic against pinned paid ledger changed")
    return {
        "status":"INDICATIVE_ONLY_NEEDS_PROVIDER_PREFLIGHT",
        "quote_model":price["model"],
        "public_quote_observed_date":price["observed_on"],
        "quote_is_authenticated_runtime_price":False,
        "historical_paid_api_calls":3,
        "historical_token_input_total":sum(x["historical_input_tokens"] for x in stage_rows),
        "historical_token_output_total":sum(x["historical_output_tokens"] for x in stage_rows),
        "historical_paid_cost_usd":float(total_actual),
        "conditional_exposure_original_output_caps_usd":float(total_exposure),
        "conditional_exposure_exceeds_total_target":total_exposure>_dec(m["target_quality_total_usd"]),
        "total_target_usd":m["target_quality_total_usd"],
        "stage_risks":stage_rows,
        "runtime_input_tokens_upper_bound_verified":False,
        "pricing_technically_reverified_at_request_time":False,
        "provider_cache_reasoning_and_fallback_prices_bounded":False,
        "provider_hard_budget_guaranteed":False,
        "quality_target_overrun_user_permitted":m["quality_target_overrun_user_permitted"],
        "requested_exception_is_not_a_hard_spend_cap":True,
        "authorized_paid_spend_ceiling_usd":None,
        "paid_dispatch_budget_safe":False,
    }


def qualify(*,repo_root,pinned_source_root,python_executable=sys.executable):
    base=Path(repo_root).resolve(strict=True)
    src=Path(pinned_source_root).resolve(strict=True)
    m=_policy(base)
    last=qualify_offline_runner(repo_root=base,pinned_source_root=src,
                                python_executable=python_executable)
    _must(last["stop_reason"]=="REAL_PAID_DISPATCH_DISABLED_OFFLINE_RUNNER_QUALIFIED"
          and last["actual_english_master_accepted"] is False
          and last["provider_calls"]==0,
          "P4.4 cannot bypass original frozen previous offline denial")
    story,repair,paid,words=_genuine_history(m,src)
    issues=_validate_source_anchored_findings(m,story,repair)
    cost=_exposure(m,paid)
    return {
      "schema":SCHEMA,
      "mode":"SOURCE_BOUND_STORY_REVIEW_AND_PROVISIONAL_PAID_PREFLIGHT",
      "source_commit":PINNED_SOURCE_COMMIT,
      "p44_manifest_sha256":MANIFEST_SHA,
      "p43_offline_kill_switch_receipt_sha256":digest(canonical_bytes(last)),
      "original_story_sha256":m["expected_story_sha256"],
      "historical_failed_repair_scene_sha256":m["failed_paid_replacement_scene_sha256"],
      "actual_story_word_count":words,
      "reader_age":m["reader_age"],
      "signed_semantic_reviewer_attestation_present":False,
      "manual_source_anchored_findings":issues,
      "confirmed_preliminary_blockers":5,
      "preliminary_advisories":2,
      "manual_review_is_not_authenticated_model_accept":True,
      "paid_initial_audit_original_blocking_finding_count":1,
      "paid_initial_audit_spans":["S167","S172","S173","S175"],
      "paid_attempt_status":paid["status"],
      "paid_attempt_failure_reason":paid["failure_reason"],
      "historical_paid_attempt_count":1,
      "current_public_price_and_budget_exposure":cost,
      "review_for_next_real_attempt":{
         "scene_repair_range":"S159-S177",
         "entry_boundary":"S158",
         "exit_boundary":"S178",
         "max_scene_repairs":1,
         "max_quality_calls":3,
         "preserve_original_story_bytes":True,
         "compelling_age_appropriate_dialogue_and_agency_required":True,
         "causal_spatial_anchors_and_rope_load_path_required":True,
         "nisa_position_and_sequential_crossing_required":True,
         "mystery_journal_and_gate_promise_must_remain":True,
         "source_admission_without_genuine_quality_accept_forbidden":True,
         "automated_paid_retry_forbidden":True,
      },
      "quality_target_overrun_user_permitted":True,
      "quality_target_overrun_not_an_api_execution_grant":True,
      "authorized_paid_spend_ceiling_usd":None,
      "paid_execution_authorized":False,
      "new_story_generation_executed":False,
      "real_final_quality_accept_present":False,
      "english_master_seal_emitted":False,
      "q25_request_authorized":False,
      "story_state_commit_authorized":False,
      "production_write_performed":False,
      "provider_calls":0,
      "provider_cost_usd":"0",
      "stop_reason":REASON,
      "state":"STOPPED_EDITORIAL_AND_BUDGET_PREFLIGHT_BLOCKERS",
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--pinned-source-root",required=True)
    parser.add_argument("--verify-report")
    args=parser.parse_args()
    root=Path(args.repo_root).resolve(strict=True)
    report=qualify(repo_root=root,pinned_source_root=args.pinned_source_root)
    if args.verify_report:
        _must(load_json(secure_artifact(root,args.verify_report))==report,
              "P4.4 immutable editorial/price evidence changed")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2))


if __name__=="__main__":
    main()

