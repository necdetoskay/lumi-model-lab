from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.spineforge_contract import CreativeSignatureV1


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class SpineForgeRevisionFeedbackV1(StrictModel):
    schema_id:Literal["spineforge-revision-feedback.v1"]=Field(alias="schema")
    source_attempt:int=Field(ge=1)
    next_attempt:int=Field(ge=2)
    source_status:Literal[
        "creative_replan_required",
        "product_replan_required",
        "human_revise",
    ]
    must_preserve:list[str]=Field(min_length=2,max_length=12)
    must_change:list[str]=Field(min_length=1,max_length=12)
    creative_feedback:list[str]=Field(min_length=1,max_length=12)
    structural_feedback:list[str]=Field(default_factory=list,max_length=12)
    previous_creative_signature:CreativeSignatureV1
    previous_spine:EpisodeSpineV2
    authority_freezes:list[str]=Field(min_length=1,max_length=20)

    @model_validator(mode="after")
    def validate_attempts(self)->"SpineForgeRevisionFeedbackV1":
        if self.next_attempt!=self.source_attempt+1:
            raise ValueError("next_attempt must equal source_attempt + 1")
        return self


def build_revision_feedback(
    source:dict[str,Any],
    *,
    authority_freezes:list[str],
    human_feedback:list[str]|None=None,
)->SpineForgeRevisionFeedbackV1:
    status=str(source.get("status") or "")
    draft_raw=source.get("creative_draft")
    if not isinstance(draft_raw,dict):
        raise RuntimeError("Source evidence has no creative_draft.")
    signature=CreativeSignatureV1.model_validate(draft_raw["creative_signature"])
    spine=EpisodeSpineV2.model_validate(draft_raw["episode_spine"])
    source_attempt=int(source.get("attempt_index") or 1)

    preserve=[]
    must_change=[]
    creative=[]
    structural=[]

    if status=="creative_replan_required":
        hard=source.get("hardening_plan") or {}
        preserve=[str(x) for x in (hard.get("preserved_creative_strengths") or [])]
        structural=[str(x) for x in (hard.get("blocking_problems") or [])]
        creative=[str(x) for x in (hard.get("replan_feedback") or [])]
        must_change=creative or structural
    elif status=="product_replan_required":
        gate=source.get("product_gate") or {}
        hard=source.get("hardening_plan") or {}
        preserve=[str(x) for x in (hard.get("preserved_creative_strengths") or [])]
        blocking=[str(x) for x in (gate.get("blocking_reasons") or [])]
        structural=blocking
        creative=blocking
        must_change=blocking
    elif status=="awaiting_human_review" and human_feedback:
        status="human_revise"
        preserve=[
            str(x)
            for x in ((source.get("hardening_plan") or {}).get("preserved_creative_strengths") or [])
        ]
        creative=[str(x) for x in human_feedback]
        must_change=creative
    else:
        raise RuntimeError(
            "Revision feedback source must be REPLAN or awaiting human review with human feedback."
        )

    if len(preserve)<2:
        preserve=[
            signature.dramatic_engine,
            signature.central_wonder_or_intrigue,
        ]

    return SpineForgeRevisionFeedbackV1(
        schema="spineforge-revision-feedback.v1",
        source_attempt=source_attempt,
        next_attempt=source_attempt+1,
        source_status=status,
        must_preserve=preserve[:12],
        must_change=must_change[:12],
        creative_feedback=creative[:12],
        structural_feedback=structural[:12],
        previous_creative_signature=signature,
        previous_spine=spine,
        authority_freezes=authority_freezes,
    )


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--authority-freeze",action="append",default=[])
    p.add_argument("--human-feedback",action="append",default=[])
    a=p.parse_args()
    source=json.loads(a.source.read_text(encoding="utf-8"))
    feedback=build_revision_feedback(
        source,
        authority_freezes=list(a.authority_freeze),
        human_feedback=list(a.human_feedback) or None,
    )
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(
        json.dumps(feedback.model_dump(mode="json",by_alias=True),ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )


if __name__=="__main__":
    main()
