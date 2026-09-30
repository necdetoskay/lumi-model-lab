from __future__ import annotations

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_context_contract import SpineForgeRevisionFeedbackV2
from src.spineforge_revision import build_revision_feedback


def build_context_bound_revision_feedback(
    source:dict,
    *,
    context_pack:SpineContextPackV1,
    human_feedback:list[str]|None=None,
)->SpineForgeRevisionFeedbackV2:
    source_fingerprint=str(source.get("context_fingerprint") or "")
    if source_fingerprint!=context_pack.context_fingerprint:
        raise RuntimeError("Source result context fingerprint does not match current SpineContextPack.")
    source_pack_id=str(source.get("context_pack_id") or "")
    if source_pack_id!=context_pack.context_pack_id:
        raise RuntimeError("Source result context_pack_id does not match current SpineContextPack.")

    feedback=build_revision_feedback(
        source,
        authority_freezes=list(context_pack.hard_freezes),
        human_feedback=human_feedback,
    )
    return SpineForgeRevisionFeedbackV2(
        schema="spineforge-revision-feedback.v2",
        context_pack_id=context_pack.context_pack_id,
        context_fingerprint=context_pack.context_fingerprint,
        feedback=feedback,
    )
