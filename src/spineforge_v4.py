from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import ValidationError

from src.english_story_pipeline import call_structured_json_with_retry
from src.episode_spine_safe_normalize_v4 import normalize_episode_spine_syntax
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_context_contract import (
    SpineForgeProductV3,
    SpineForgeRevisionFeedbackV3,
)
from src.spineforge_v3_context_revision import build_context_bound_revision_feedback_v3
from src.spineforge_v3_contract import (
    SpineCreativeDraftV1,
    SpineForgeProductV1,
    SpineHardeningPlanV1,
    SpineProductGateV1,
)
from src.spineforge_v3_patch import apply_hardening_plan

AION_MODEL="aion-labs/aion-3.5-mini"
SONNET_MODEL="anthropic/claude-sonnet-5.5"
LUNA_MODEL="openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT=Path("prompts/spineforge_creative_architect_v3_context.md")
DEFAULT_HARDENER_PROMPT=Path("prompts/spineforge_structural_hardener_v2_context.md")
DEFAULT_GATE_PROMPT=Path("prompts/spineforge_product_gate_v2_context.md")


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


def _read(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path:Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def _model_call(stage:str,model:str,body:dict[str,Any],latency:float)->dict[str,Any]:
    return normalize_model_call(
        stage=stage,
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )


def _normalize_creative_raw(raw:dict[str,Any])->tuple[dict[str,Any],list[dict[str,Any]]]:
    value=json.loads(json.dumps(raw))
    repairs:list[dict[str,Any]]=[]

    # Provider/model lineage belongs to the application runtime, not to model-authored JSON.
    if value.get("creative_model")!=AION_MODEL:
        repairs.append({
            "kind":"stamp_application_owned_model_identity",
            "field":"creative_model",
            "old":value.get("creative_model"),
            "new":AION_MODEL,
            "reason":"The runtime owns provider/model identity.",
        })
        value["creative_model"]=AION_MODEL

    spine=value.get("episode_spine")
    if not isinstance(spine,dict):
        return value,repairs

    normalized,syntax_repairs=normalize_episode_spine_syntax(spine)
    repairs.extend(syntax_repairs)
    value["episode_spine"]=normalized

    # location_sequence duplicates information already carried by the ordered beats.
    # Derive it deterministically instead of spending a retry on representational drift.
    beats=normalized.get("beats")
    logistics=normalized.get("logistics_plan")
    if isinstance(beats,list) and isinstance(logistics,dict):
        derived:list[str]=[]
        for beat in beats:
            if not isinstance(beat,dict):
                continue
            location=beat.get("location_ref")
            if isinstance(location,str) and location and (
                not derived or derived[-1]!=location
            ):
                derived.append(location)
        if derived and logistics.get("location_sequence")!=derived:
            repairs.append({
                "kind":"derive_logistics_location_sequence",
                "field":"episode_spine.logistics_plan.location_sequence",
                "old":logistics.get("location_sequence"),
                "new":derived,
                "reason":"location_sequence is a redundant deterministic projection of beat order.",
            })
            logistics["location_sequence"]=derived

    return value,repairs


def _allowed_full_locations(pack:SpineContextPackV1)->set[str]:
    return {
        str(x["key"])
        for x in pack.knowledge_boundaries["accessible_locations"]
        if x.get("premise_usage")=="FULL"
    }


def _validate_spine_authority(
    *,
    draft:SpineCreativeDraftV1,
    pack:SpineContextPackV1,
)->None:
    spine=draft.episode_spine
    premise=pack.approved_premise
    session=pack.session_target

    if draft.creative_model!=AION_MODEL:
        raise RuntimeError("Creative draft model identity mismatch.")
    if spine.premise_key!=premise["key"]:
        raise RuntimeError("Spine premise_key mismatch.")
    if spine.exact_age!=int(pack.reader_profile["exact_age"]):
        raise RuntimeError("Spine exact_age mismatch.")
    if spine.session!=session["name"]:
        raise RuntimeError("Spine session mismatch.")
    if (
        spine.target_words_min!=int(session["target_words_min"])
        or spine.target_words_max!=int(session["target_words_max"])
    ):
        raise RuntimeError("Spine word target mismatch.")

    allowed=set(premise["location_refs"])
    full=_allowed_full_locations(pack)
    if not allowed.issubset(full):
        raise RuntimeError("Approved premise contains location without FULL access.")
    used={beat.location_ref for beat in spine.beats}
    if not used.issubset(allowed):
        raise RuntimeError("Spine uses location outside approved premise.")

    intended=set(pack.saga["intended_milestone_keys"])
    if set(spine.saga_progression.intended_milestone_keys)!=intended:
        raise RuntimeError("Spine intended milestones differ from ContextPack authority.")
    if intended and spine.episode_role not in {
        "MAIN_SAGA_ENTRY","MAIN_SAGA_PROGRESS","MIXED"
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")


def _validate_revision(
    *,
    revision_path:Path|None,
    pack:SpineContextPackV1,
    max_attempts:int,
)->tuple[SpineForgeRevisionFeedbackV3|None,int]:
    if revision_path is None:
        return None,1
    revision=SpineForgeRevisionFeedbackV3.model_validate(_read(revision_path))
    attempt=revision.next_attempt
    if revision.context_pack_id!=pack.context_pack_id:
        raise RuntimeError("Revision feedback context_pack_id is stale.")
    if revision.context_fingerprint!=pack.context_fingerprint:
        raise RuntimeError("Revision feedback context_fingerprint is stale.")
    if attempt>max_attempts:
        raise RuntimeError(f"SpineForge attempt limit exceeded: {attempt}>{max_attempts}")
    return revision,attempt


def run(
    *,
    context_pack_path:Path,
    out_path:Path,
    creative_prompt_path:Path=DEFAULT_CREATIVE_PROMPT,
    hardener_prompt_path:Path=DEFAULT_HARDENER_PROMPT,
    gate_prompt_path:Path=DEFAULT_GATE_PROMPT,
    revision_feedback_path:Path|None=None,
    max_attempts:int=3,
    api_key:str|None=None,
)->dict[str,Any]:
    load_dotenv()
    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    pack=SpineContextPackV1.model_validate(_read(context_pack_path))
    revision,attempt_index=_validate_revision(
        revision_path=revision_feedback_path,
        pack=pack,
        max_attempts=max_attempts,
    )

    for model in (AION_MODEL,SONNET_MODEL,LUNA_MODEL):
        require_qualification_runtime_profile(model)

    pack_payload=pack.model_dump(mode="json",by_alias=True)
    calls=[]
    started=time.perf_counter()
    evidence={
        "schema_version":"spineforge-v4-evidence.v1",
        "status":"started",
        "attempt_index":attempt_index,
        "context_pack_id":pack.context_pack_id,
        "context_fingerprint":pack.context_fingerprint,
        "context_pack":pack_payload,
        "revision_feedback":(
            revision.model_dump(mode="json",by_alias=True) if revision else None
        ),
        "started_at":_now(),
        "models":{
            "creative_architect":AION_MODEL,
            "structural_hardener":SONNET_MODEL,
            "product_gate":LUNA_MODEL,
        },
        "human_review":{
            "required":True,
            "verdict":None,
            "writer_authorized":False,
        },
    }

    creative_input={
        "task":"create_spineforge_creative_draft",
        "spine_context_pack":pack_payload,
        "revision_context":(
            revision.model_dump(mode="json",by_alias=True) if revision else None
        ),
        "output_contract":SpineCreativeDraftV1.model_json_schema(by_alias=True),
    }

    call_started=time.perf_counter()
    creative_raw,creative_body,_,creative_failures=call_structured_json_with_retry(
        api_key=key,
        model=AION_MODEL,
        system_prompt=creative_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(creative_input,ensure_ascii=False),
        temperature=0.85,
        max_tokens=14000,
        seed=None,
        request_class="teacher_story_medium_reasoning",
        max_parse_attempts=1,
    )
    creative_latency=round(time.perf_counter()-call_started,3)
    calls.append(_model_call("spineforge_creative_architect",AION_MODEL,creative_body,creative_latency))
    evidence["creative_raw_payload"]=creative_raw
    evidence["creative_parse_failures"]=creative_failures

    normalized_raw,normalization_repairs=_normalize_creative_raw(creative_raw)
    evidence["creative_normalized_payload"]=normalized_raw
    evidence["creative_safe_normalization"]={
        "applied":bool(normalization_repairs),
        "repairs":normalization_repairs,
        "semantic_fields_changed":False,
    }

    try:
        draft=SpineCreativeDraftV1.model_validate(normalized_raw)
        _validate_spine_authority(draft=draft,pack=pack)
    except (ValidationError,RuntimeError) as exc:
        rollup=rollup_model_calls(calls)
        evidence.update({
            "status":"creative_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        try:
            feedback=build_context_bound_revision_feedback_v3(
                evidence,
                context_pack=pack,
            )
            evidence["revision_feedback_candidate"]=feedback.model_dump(
                mode="json",by_alias=True
            )
        except Exception as feedback_exc:
            evidence["revision_feedback_candidate_error"]={
                "type":type(feedback_exc).__name__,
                "message":str(feedback_exc),
            }
        _write(out_path,evidence)
        return evidence

    evidence["creative_draft"]=draft.model_dump(mode="json",by_alias=True)

    hardener_input={
        "task":"harden_creative_spine_without_taking_creative_ownership",
        "spine_context_pack":pack_payload,
        "creative_signature":draft.creative_signature.model_dump(mode="json"),
        "episode_spine":draft.episode_spine.model_dump(mode="json",by_alias=True),
        "output_contract":SpineHardeningPlanV1.model_json_schema(by_alias=True),
    }

    call_started=time.perf_counter()
    hard_raw,hard_body,_,hard_failures=call_structured_json_with_retry(
        api_key=key,
        model=SONNET_MODEL,
        system_prompt=hardener_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(hardener_input,ensure_ascii=False),
        temperature=0.0,
        max_tokens=7000,
        seed=None,
        request_class="saga_architect",
        max_parse_attempts=1,
    )
    hard_latency=round(time.perf_counter()-call_started,3)
    calls.append(_model_call("spineforge_structural_hardener",SONNET_MODEL,hard_body,hard_latency))
    evidence["hardener_raw_payload"]=hard_raw
    evidence["hardener_parse_failures"]=hard_failures

    try:
        plan=SpineHardeningPlanV1.model_validate(hard_raw)
    except ValidationError as exc:
        rollup=rollup_model_calls(calls)
        evidence.update({
            "status":"hardener_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        _write(out_path,evidence)
        return evidence

    evidence["hardening_plan"]=plan.model_dump(mode="json",by_alias=True)
    if plan.decision=="REPLAN":
        rollup=rollup_model_calls(calls)
        evidence.update({
            "status":"creative_replan_required",
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        _write(out_path,evidence)
        return evidence

    try:
        hardened,applied=apply_hardening_plan(draft.episode_spine,plan)
        hardened_draft=SpineCreativeDraftV1(
            schema="spineforge-creative-draft.v1",
            creative_model=draft.creative_model,
            creative_signature=draft.creative_signature,
            episode_spine=hardened,
            self_check_notes=draft.self_check_notes,
        )
        _validate_spine_authority(draft=hardened_draft,pack=pack)
    except Exception as exc:
        rollup=rollup_model_calls(calls)
        evidence.update({
            "status":"hardening_patch_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        _write(out_path,evidence)
        return evidence

    evidence["applied_hardening_patches"]=applied
    evidence["hardened_spine"]=hardened.model_dump(mode="json",by_alias=True)

    gate_input={
        "task":"evaluate_spineforge_product",
        "spine_context_pack":pack_payload,
        "creative_signature":draft.creative_signature.model_dump(mode="json"),
        "creative_spine":draft.episode_spine.model_dump(mode="json",by_alias=True),
        "hardening_plan":plan.model_dump(mode="json",by_alias=True),
        "applied_hardening_patches":applied,
        "hardened_spine":hardened.model_dump(mode="json",by_alias=True),
        "output_contract":SpineProductGateV1.model_json_schema(by_alias=True),
    }

    call_started=time.perf_counter()
    gate_raw,gate_body,_,gate_failures=call_structured_json_with_retry(
        api_key=key,
        model=LUNA_MODEL,
        system_prompt=gate_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(gate_input,ensure_ascii=False),
        temperature=0.0,
        max_tokens=5500,
        seed=2026093010,
        request_class="editorial_audit",
        max_parse_attempts=1,
    )
    gate_latency=round(time.perf_counter()-call_started,3)
    calls.append(_model_call("spineforge_product_gate",LUNA_MODEL,gate_body,gate_latency))
    evidence["product_gate_raw_payload"]=gate_raw
    evidence["product_gate_parse_failures"]=gate_failures

    try:
        gate=SpineProductGateV1.model_validate(gate_raw)
    except ValidationError as exc:
        rollup=rollup_model_calls(calls)
        evidence.update({
            "status":"product_gate_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        _write(out_path,evidence)
        return evidence

    status="awaiting_human_review" if gate.decision=="ACCEPT" else "product_replan_required"
    rollup=rollup_model_calls(calls)
    evidence.update({
        "status":status,
        "product_gate":gate.model_dump(mode="json",by_alias=True),
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "completed_at":_now(),
        "latency_seconds":round(time.perf_counter()-started,3),
    })

    if gate.decision=="ACCEPT":
        legacy_product=SpineForgeProductV1(
            schema="spineforge-product.v1",
            status="AWAITING_HUMAN_REVIEW",
            premise_key=hardened.premise_key,
            exact_age=hardened.exact_age,
            creative_draft=draft,
            hardening_plan=plan,
            hardened_spine=hardened,
            product_gate=gate,
            deterministic_checks={
                "creative_contract_valid":True,
                "context_pack_authority_valid":True,
                "hardening_patch_valid":True,
                "creative_identity_protected":True,
                "context_fingerprint_bound":True,
            },
            lineage={
                "models":evidence["models"],
                "usage_rollup":rollup,
                "context_pack_id":pack.context_pack_id,
                "context_fingerprint":pack.context_fingerprint,
            },
            human_review=evidence["human_review"],
        )
        product=SpineForgeProductV3(
            schema="spineforge-product.v3",
            context_pack_id=pack.context_pack_id,
            context_fingerprint=pack.context_fingerprint,
            product=legacy_product,
        )
        evidence["spine_product"]=product.model_dump(mode="json",by_alias=True)

    _write(out_path,evidence)
    return evidence


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--context-pack",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--creative-prompt",type=Path,default=DEFAULT_CREATIVE_PROMPT)
    p.add_argument("--hardener-prompt",type=Path,default=DEFAULT_HARDENER_PROMPT)
    p.add_argument("--gate-prompt",type=Path,default=DEFAULT_GATE_PROMPT)
    p.add_argument("--revision-feedback",type=Path)
    p.add_argument("--max-attempts",type=int,default=3)
    a=p.parse_args()
    result=run(
        context_pack_path=a.context_pack,
        out_path=a.out,
        creative_prompt_path=a.creative_prompt,
        hardener_prompt_path=a.hardener_prompt,
        gate_prompt_path=a.gate_prompt,
        revision_feedback_path=a.revision_feedback,
        max_attempts=a.max_attempts,
    )
    print(json.dumps({
        "status":result["status"],
        "attempt_index":result["attempt_index"],
        "context_pack_id":result["context_pack_id"],
        "context_fingerprint":result["context_fingerprint"],
        "usage":(result.get("pipeline_usage_rollup") or {}).get("totals"),
        "human_review":result["human_review"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
