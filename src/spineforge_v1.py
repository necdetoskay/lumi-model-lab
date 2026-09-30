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
from src.episode_spine_safe_normalize_v2 import normalize_episode_spine_syntax
from src.generate import parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.premise_architect_v2_contract import (
    PremiseLabStateV1,
    build_reveal_safe_premise_projection,
)
from src.reader_profile_v2 import ReaderDevelopmentProfileV2
from src.saga_blueprint_contract import NarrativeFixture
from src.saga_spine_v2_contract import CharacterSagaSpineV2
from src.spineforge_contract import (
    CreativeSignatureV1,
    SpineCreativeDraftV1,
    SpineForgeProductV1,
    SpineHardeningPlanV1,
    SpineProductGateV1,
)
from src.spineforge_patch import apply_hardening_plan
from src.spineforge_revision import SpineForgeRevisionFeedbackV1

AION_MODEL="aion-labs/aion-3.5-mini"
SONNET_MODEL="anthropic/claude-sonnet-5.5"
LUNA_MODEL="openai/gpt-5.6-luna"

DEFAULT_CREATIVE_PROMPT=Path("prompts/spineforge_creative_architect_v1.md")
DEFAULT_HARDENER_PROMPT=Path("prompts/spineforge_structural_hardener_v1.md")
DEFAULT_GATE_PROMPT=Path("prompts/spineforge_product_gate_v1.md")


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


def _context(
    *,
    saga_path:Path,
    reader_path:Path,
    fixture_path:Path,
    state_path:Path,
    premise_path:Path,
)->dict[str,Any]:
    saga=CharacterSagaSpineV2.model_validate(_read(saga_path))
    reader=ReaderDevelopmentProfileV2.model_validate(_read(reader_path))
    fixture=NarrativeFixture.model_validate(_read(fixture_path))
    state=PremiseLabStateV1.model_validate(_read(state_path))
    premise_artifact=_read(premise_path)
    premise=premise_artifact["premise"]
    projection=build_reveal_safe_premise_projection(
        spine=saga,reader=reader,fixture=fixture,state=state
    )

    eligible={row["key"] for row in projection["eligible_main_saga_milestones"]}
    intended=sorted(set(premise["target_refs"]) & eligible)
    session=projection["session_target"]
    allowed=set(premise["location_refs"])
    accessible={
        row["key"]
        for row in projection["world"]["location_access"]
        if row["status"]=="AVAILABLE" and row["premise_usage"]=="FULL"
    }
    if not allowed.issubset(accessible):
        raise RuntimeError("Premise contains inaccessible locations.")

    return {
        "premise_artifact":premise_artifact,
        "premise":premise,
        "projection":projection,
        "reader":reader,
        "session":session,
        "allowed_locations":sorted(allowed),
        "intended_milestones":intended,
    }


def _validate_spine_authority(
    *,
    draft:SpineCreativeDraftV1,
    ctx:dict[str,Any],
)->None:
    spine=draft.episode_spine
    premise=ctx["premise"]
    reader=ctx["reader"]
    session=ctx["session"]

    if spine.premise_key!=premise["key"]:
        raise RuntimeError("Spine premise_key mismatch.")
    if spine.exact_age!=reader.exact_age:
        raise RuntimeError("Spine exact_age mismatch.")
    if spine.session!=session["name"]:
        raise RuntimeError("Spine session mismatch.")
    if spine.target_words_min!=session["target_words_min"] or spine.target_words_max!=session["target_words_max"]:
        raise RuntimeError("Spine word target mismatch.")
    used={beat.location_ref for beat in spine.beats}
    if not used.issubset(set(ctx["allowed_locations"])):
        raise RuntimeError("Spine uses location outside approved premise.")
    if set(spine.saga_progression.intended_milestone_keys)!=set(ctx["intended_milestones"]):
        raise RuntimeError("Spine intended milestones differ from authority.")
    if ctx["intended_milestones"] and spine.episode_role not in {
        "MAIN_SAGA_ENTRY","MAIN_SAGA_PROGRESS","MIXED"
    }:
        raise RuntimeError("Main Saga milestone requires Main Saga episode role.")


def _normalize_creative_raw(raw:dict[str,Any])->tuple[dict[str,Any],list[dict[str,Any]]]:
    value=json.loads(json.dumps(raw))
    if not isinstance(value.get("episode_spine"),dict):
        return raw,[]
    normalized,repairs=normalize_episode_spine_syntax(value["episode_spine"])
    value["episode_spine"]=normalized
    return value,repairs


def run(
    *,
    saga_path:Path,
    reader_path:Path,
    fixture_path:Path,
    state_path:Path,
    premise_path:Path,
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

    for model in (AION_MODEL,SONNET_MODEL,LUNA_MODEL):
        require_qualification_runtime_profile(model)

    ctx=_context(
        saga_path=saga_path,reader_path=reader_path,fixture_path=fixture_path,
        state_path=state_path,premise_path=premise_path,
    )
    revision_feedback=None
    attempt_index=1
    if revision_feedback_path is not None:
        revision_feedback=SpineForgeRevisionFeedbackV1.model_validate(
            _read(revision_feedback_path)
        )
        attempt_index=revision_feedback.next_attempt
    if attempt_index>max_attempts:
        raise RuntimeError(
            f"SpineForge attempt limit exceeded: {attempt_index}>{max_attempts}"
        )

    calls=[]
    started=time.perf_counter()
    evidence={
        "schema_version":"spineforge-v1-evidence.v1",
        "status":"started",
        "attempt_index":attempt_index,
        "revision_feedback":(
            revision_feedback.model_dump(mode="json",by_alias=True)
            if revision_feedback is not None else None
        ),
        "started_at":_now(),
        "models":{
            "creative_architect":AION_MODEL,
            "structural_hardener":SONNET_MODEL,
            "product_gate":LUNA_MODEL,
        },
        "approved_premise":ctx["premise_artifact"],
        "projection":ctx["projection"],
        "human_review":{
            "required":True,
            "verdict":None,
            "writer_authorized":False,
        },
    }

    creative_input={
        "task":"create_spineforge_creative_draft",
        "approved_premise":ctx["premise"],
        "premise_context":ctx["projection"],
        "required_intended_milestone_keys":ctx["intended_milestones"],
        "allowed_location_refs":ctx["allowed_locations"],
        "required_session":{
            "name":ctx["session"]["name"],
            "target_words_min":ctx["session"]["target_words_min"],
            "target_words_max":ctx["session"]["target_words_max"],
        },
        "revision_context":(
            revision_feedback.model_dump(mode="json",by_alias=True)
            if revision_feedback is not None else None
        ),
        "revision_rule":(
            "When revision_context exists: preserve must_preserve and authority_freezes; "
            "fix must_change and creative_feedback; do not merely patch wording. "
            "Rebuild any affected causal/scene structure while keeping unaffected creative strengths."
        ),
        "output_contract":SpineCreativeDraftV1.model_json_schema(by_alias=True),
        "hard_rules":{
            "prose_generation_forbidden":True,
            "human_review_required":True,
            "hidden_truth_inference_forbidden":True,
            "future_choice_precommitment_forbidden":True,
            "milestone_commit_forbidden":True,
        },
    }

    call_started=time.perf_counter()
    creative_raw,creative_body,creative_request,creative_failures=call_structured_json_with_retry(
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
    evidence["creative_safe_normalization"]={
        "applied":bool(normalization_repairs),
        "repairs":normalization_repairs,
        "semantic_fields_changed":False,
    }
    try:
        draft=SpineCreativeDraftV1.model_validate(normalized_raw)
        _validate_spine_authority(draft=draft,ctx=ctx)
    except (ValidationError,RuntimeError) as exc:
        evidence.update({
            "status":"creative_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup_model_calls(calls),
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        evidence["total_cost_usd"]=evidence["pipeline_usage_rollup"]["totals"]["cost_usd"]
        _write(out_path,evidence)
        return evidence

    evidence["creative_draft"]=draft.model_dump(mode="json",by_alias=True)

    hardener_input={
        "task":"harden_creative_spine_without_taking_creative_ownership",
        "approved_premise":ctx["premise"],
        "premise_context":ctx["projection"],
        "creative_signature":draft.creative_signature.model_dump(mode="json"),
        "episode_spine":draft.episode_spine.model_dump(mode="json",by_alias=True),
        "output_contract":SpineHardeningPlanV1.model_json_schema(by_alias=True),
        "hard_rules":{
            "minimal_patch_only":True,
            "creative_identity_rewrite_forbidden":True,
            "maximum_patches":12,
            "if_creative_identity_must_change":"REPLAN",
        },
    }

    call_started=time.perf_counter()
    hard_raw,hard_body,hard_request,hard_failures=call_structured_json_with_retry(
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
        evidence.update({
            "status":"hardener_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup_model_calls(calls),
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        evidence["total_cost_usd"]=evidence["pipeline_usage_rollup"]["totals"]["cost_usd"]
        _write(out_path,evidence)
        return evidence

    evidence["hardening_plan"]=plan.model_dump(mode="json",by_alias=True)
    if plan.decision=="REPLAN":
        evidence.update({
            "status":"creative_replan_required",
            "pipeline_usage_rollup":rollup_model_calls(calls),
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        evidence["total_cost_usd"]=evidence["pipeline_usage_rollup"]["totals"]["cost_usd"]
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
        _validate_spine_authority(draft=hardened_draft,ctx=ctx)
    except Exception as exc:
        evidence.update({
            "status":"hardening_patch_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup_model_calls(calls),
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        evidence["total_cost_usd"]=evidence["pipeline_usage_rollup"]["totals"]["cost_usd"]
        _write(out_path,evidence)
        return evidence

    evidence["applied_hardening_patches"]=applied
    evidence["hardened_spine"]=hardened.model_dump(mode="json",by_alias=True)

    gate_input={
        "task":"evaluate_spineforge_product",
        "approved_premise":ctx["premise"],
        "premise_context":ctx["projection"],
        "creative_signature":draft.creative_signature.model_dump(mode="json"),
        "creative_spine":draft.episode_spine.model_dump(mode="json",by_alias=True),
        "hardening_plan":plan.model_dump(mode="json",by_alias=True),
        "applied_hardening_patches":applied,
        "hardened_spine":hardened.model_dump(mode="json",by_alias=True),
        "output_contract":SpineProductGateV1.model_json_schema(by_alias=True),
    }

    call_started=time.perf_counter()
    gate_raw,gate_body,gate_request,gate_failures=call_structured_json_with_retry(
        api_key=key,
        model=LUNA_MODEL,
        system_prompt=gate_prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps(gate_input,ensure_ascii=False),
        temperature=0.0,
        max_tokens=5500,
        seed=2026093009,
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
        evidence.update({
            "status":"product_gate_contract_rejected",
            "failure":{"type":type(exc).__name__,"message":str(exc)},
            "pipeline_usage_rollup":rollup_model_calls(calls),
            "completed_at":_now(),
            "latency_seconds":round(time.perf_counter()-started,3),
        })
        evidence["total_cost_usd"]=evidence["pipeline_usage_rollup"]["totals"]["cost_usd"]
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
        product=SpineForgeProductV1(
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
                "authority_alignment_valid":True,
                "hardening_patch_valid":True,
                "creative_identity_protected":True,
            },
            lineage={
                "models":evidence["models"],
                "usage_rollup":rollup,
            },
            human_review=evidence["human_review"],
        )
        evidence["spine_product"]=product.model_dump(mode="json",by_alias=True)

    _write(out_path,evidence)
    return evidence


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--saga",type=Path,required=True)
    p.add_argument("--reader",type=Path,required=True)
    p.add_argument("--fixture",type=Path,required=True)
    p.add_argument("--state",type=Path,required=True)
    p.add_argument("--premise",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--creative-prompt",type=Path,default=DEFAULT_CREATIVE_PROMPT)
    p.add_argument("--hardener-prompt",type=Path,default=DEFAULT_HARDENER_PROMPT)
    p.add_argument("--gate-prompt",type=Path,default=DEFAULT_GATE_PROMPT)
    p.add_argument("--revision-feedback",type=Path)
    p.add_argument("--max-attempts",type=int,default=3)
    a=p.parse_args()
    result=run(
        saga_path=a.saga,reader_path=a.reader,fixture_path=a.fixture,
        state_path=a.state,premise_path=a.premise,out_path=a.out,
        creative_prompt_path=a.creative_prompt,
        hardener_prompt_path=a.hardener_prompt,
        gate_prompt_path=a.gate_prompt,
        revision_feedback_path=a.revision_feedback,
        max_attempts=a.max_attempts,
    )
    print(json.dumps({
        "status":result["status"],
        "models":result["models"],
        "usage":(result.get("pipeline_usage_rollup") or {}).get("totals"),
        "human_review":result["human_review"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
