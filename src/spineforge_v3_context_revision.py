from __future__ import annotations

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v3_context_contract import SpineForgeRevisionFeedbackV3


def _binding_guard(source:dict,context_pack:SpineContextPackV1)->None:
    if str(source.get("context_pack_id") or "")!=context_pack.context_pack_id:
        raise RuntimeError("Source result context_pack_id does not match current SpineContextPack.")
    if str(source.get("context_fingerprint") or "")!=context_pack.context_fingerprint:
        raise RuntimeError("Source result context fingerprint does not match current SpineContextPack.")


def _preserve(raw:dict)->list[str]:
    sig=raw.get("creative_signature") if isinstance(raw,dict) else None
    if isinstance(sig,dict):
        values=[
            str(sig.get("dramatic_engine") or "").strip(),
            str(sig.get("central_wonder_or_intrigue") or "").strip(),
        ]
        values=[x for x in values if x]
        if len(values)>=2:
            return values[:12]
    spine=raw.get("episode_spine") if isinstance(raw,dict) else None
    title=str((spine or {}).get("title") or "approved-premise story identity").strip()
    return [
        f"Preserve the prior draft's core story identity: {title}.",
        "Preserve authority-safe creative strengths unrelated to the reported failure.",
    ]


def build_context_bound_revision_feedback_v3(
    source:dict,
    *,
    context_pack:SpineContextPackV1,
    human_feedback:list[str]|None=None,
)->SpineForgeRevisionFeedbackV3:
    _binding_guard(source,context_pack)
    status=str(source.get("status") or "")
    attempt=int(source.get("attempt_index") or 1)
    raw=source.get("creative_draft") or source.get("creative_normalized_payload") or source.get("creative_raw_payload") or {}
    if not isinstance(raw,dict):
        raw={}

    validation_errors:list[str]=[]
    must_change:list[str]=[]
    creative_feedback:list[str]=[]
    structural_feedback:list[str]=[]

    if status=="creative_contract_rejected":
        failure=source.get("failure") or {}
        message=str(failure.get("message") or "Creative draft failed deterministic contract validation.")
        parse=[str(x) for x in (source.get("creative_parse_failures") or []) if str(x).strip()]
        validation_errors=([message]+parse)[:12]
        must_change=validation_errors or ["Return a draft satisfying the supplied output contract."]
        creative_feedback=[
            "Rebuild only the parts needed to satisfy deterministic contract validation; do not hide or relabel invalid state.",
            "Preserve the unchanged SpineContextPack authority, approved premise, hard freezes, and unrelated creative strengths.",
            *validation_errors,
        ][:12]
        structural_feedback=list(validation_errors)
    elif status=="creative_replan_required":
        hard=source.get("hardening_plan") or {}
        structural_feedback=[str(x) for x in (hard.get("blocking_problems") or [])][:12]
        creative_feedback=[str(x) for x in (hard.get("replan_feedback") or [])][:12]
        must_change=(creative_feedback or structural_feedback)[:12]
    elif status=="product_replan_required":
        gate=source.get("product_gate") or {}
        blocking=[str(x) for x in (gate.get("blocking_reasons") or [])][:12]
        structural_feedback=blocking
        creative_feedback=blocking
        must_change=blocking
    elif status=="awaiting_human_review" and human_feedback:
        status="human_revise"
        creative_feedback=[str(x) for x in human_feedback][:12]
        must_change=list(creative_feedback)
    else:
        raise RuntimeError("Unsupported source state for v3 revision feedback.")

    if not must_change:
        raise RuntimeError("Revision feedback requires at least one concrete change.")

    return SpineForgeRevisionFeedbackV3(
        schema="spineforge-revision-feedback.v3",
        context_pack_id=context_pack.context_pack_id,
        context_fingerprint=context_pack.context_fingerprint,
        source_attempt=attempt,
        next_attempt=attempt+1,
        source_status=status,
        must_preserve=_preserve(raw),
        must_change=must_change,
        creative_feedback=creative_feedback or must_change,
        structural_feedback=structural_feedback,
        previous_creative_signature=(raw.get("creative_signature") if isinstance(raw.get("creative_signature"),dict) else None),
        previous_spine_raw=(raw.get("episode_spine") if isinstance(raw.get("episode_spine"),dict) else None),
        validation_errors=validation_errors,
        authority_freezes=list(context_pack.hard_freezes),
    )
