from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.episode_spine_v3_contract import EpisodeSpineV3

KEY_PATTERN=r"^[a-z][a-z0-9_]*$"


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class CreativeSignatureV1(StrictModel):
    dramatic_engine:str
    protagonist_desire:str
    protagonist_pressure:str
    central_wonder_or_intrigue:str
    signature_scene_promises:list[str]=Field(min_length=2,max_length=5)
    roleplay_opportunities:list[str]=Field(min_length=3,max_length=7)
    emotional_turns:list[str]=Field(min_length=2,max_length=5)
    world_specific_story_uses:list[str]=Field(min_length=2,max_length=6)
    freshness_claim:str
    why_reader_wants_next_beat:str


class SpineCreativeDraftV1(StrictModel):
    schema_id:Literal["spineforge-creative-draft.v1"]=Field(alias="schema")
    creative_model:str
    creative_signature:CreativeSignatureV1
    episode_spine:EpisodeSpineV3
    self_check_notes:list[str]=Field(default_factory=list,max_length=8)


class HardeningPatchV1(StrictModel):
    path:str
    expected_old:Any
    replacement:Any
    defect_class:Literal[
        "CAUSALITY",
        "LOGISTICS",
        "EVIDENCE_CEILING",
        "BRANCH_EXECUTABILITY",
        "PAYOFF_CONSISTENCY",
        "AUTHORITY_SAFETY",
        "WRITER_EXECUTABILITY",
        "REPETITION_SAFETY",
        "OTHER_STRUCTURAL",
    ]
    reason:str
    creative_impact:Literal["NONE","LOW"]


class SpineHardeningPlanV1(StrictModel):
    schema_id:Literal["spineforge-hardening-plan.v1"]=Field(alias="schema")
    decision:Literal["KEEP","PATCH","STRUCTURAL_PATCH","REPLAN"]
    assessment_summary:str
    preserved_creative_strengths:list[str]=Field(min_length=2,max_length=8)
    blocking_problems:list[str]=Field(default_factory=list,max_length=12)
    patches:list[HardeningPatchV1]=Field(default_factory=list,max_length=12)
    replan_feedback:list[str]=Field(default_factory=list,max_length=10)

    @model_validator(mode="after")
    def validate_decision(self)->"SpineHardeningPlanV1":
        if self.decision=="KEEP":
            if self.patches or self.blocking_problems or self.replan_feedback:
                raise ValueError("KEEP cannot include patches/blockers/replan feedback")
        elif self.decision in {"PATCH","STRUCTURAL_PATCH"}:
            if not self.patches:
                raise ValueError("PATCH decisions require at least one patch")
            if self.replan_feedback:
                raise ValueError("PATCH decisions cannot include replan feedback")
            if self.decision=="PATCH" and len(self.patches)>6:
                raise ValueError("PATCH is limited to 6 bounded changes")
        elif self.decision=="REPLAN":
            if self.patches:
                raise ValueError("REPLAN cannot include patches")
            if not self.replan_feedback:
                raise ValueError("REPLAN requires concrete creative replan feedback")
        return self


class SpineProductDimensionV1(StrictModel):
    name:Literal[
        "STORY_DESIRE",
        "ROLEPLAY_POTENTIAL",
        "SCENE_POTENTIAL",
        "CHARACTER_DRIVENNESS",
        "WORLD_SPECIFICITY",
        "WONDER_OR_INTRIGUE",
        "AGE_MATURITY",
        "CAUSAL_COHERENCE",
        "ESCALATION",
        "REVERSAL_QUALITY",
        "AGENCY",
        "BRANCH_EXECUTABILITY",
        "CLIMAX_PAYOFF",
        "LOCAL_SATISFACTION",
        "SAGA_ALIGNMENT",
        "WRITER_EXECUTABILITY",
        "FRESHNESS",
    ]
    score:int=Field(ge=1,le=5)
    blocking_failure:bool
    reason:str


class SpineProductGateV1(StrictModel):
    schema_id:Literal["spineforge-product-gate.v1"]=Field(alias="schema")
    dimensions:list[SpineProductDimensionV1]
    decision:Literal["ACCEPT","REPLAN"]
    blocking_reasons:list[str]
    decision_reason:str

    @model_validator(mode="after")
    def validate_gate(self)->"SpineProductGateV1":
        expected={
            "STORY_DESIRE","ROLEPLAY_POTENTIAL","SCENE_POTENTIAL",
            "CHARACTER_DRIVENNESS","WORLD_SPECIFICITY","WONDER_OR_INTRIGUE",
            "AGE_MATURITY","CAUSAL_COHERENCE","ESCALATION","REVERSAL_QUALITY",
            "AGENCY","BRANCH_EXECUTABILITY","CLIMAX_PAYOFF","LOCAL_SATISFACTION",
            "SAGA_ALIGNMENT","WRITER_EXECUTABILITY","FRESHNESS",
        }
        names=[row.name for row in self.dimensions]
        if len(names)!=len(set(names)) or set(names)!=expected:
            raise ValueError("Spine Product Gate must cover every dimension exactly once")
        if any(x.blocking_failure for x in self.dimensions) and self.decision!="REPLAN":
            raise ValueError("Any blocking failure requires REPLAN")
        if self.decision=="ACCEPT":
            scores={x.name:x.score for x in self.dimensions}
            minimums={
                "STORY_DESIRE":4,
                "ROLEPLAY_POTENTIAL":4,
                "SCENE_POTENTIAL":4,
                "CHARACTER_DRIVENNESS":4,
                "WORLD_SPECIFICITY":4,
                "WONDER_OR_INTRIGUE":4,
                "AGE_MATURITY":4,
                "CAUSAL_COHERENCE":4,
                "ESCALATION":4,
                "REVERSAL_QUALITY":3,
                "AGENCY":4,
                "BRANCH_EXECUTABILITY":4,
                "CLIMAX_PAYOFF":4,
                "LOCAL_SATISFACTION":4,
                "SAGA_ALIGNMENT":4,
                "WRITER_EXECUTABILITY":4,
                "FRESHNESS":4,
            }
            failures=[
                f"{name}:{scores[name]}<{minimum}"
                for name,minimum in minimums.items()
                if scores[name]<minimum
            ]
            if failures:
                raise ValueError("ACCEPT misses protected product thresholds: "+", ".join(failures))
        return self


class SpineForgeProductV1(StrictModel):
    schema_id:Literal["spineforge-product.v1"]=Field(alias="schema")
    status:Literal["AWAITING_HUMAN_REVIEW","HUMAN_APPROVED","REPLAN_REQUIRED"]
    premise_key:str
    exact_age:int
    creative_draft:SpineCreativeDraftV1
    hardening_plan:SpineHardeningPlanV1
    hardened_spine:EpisodeSpineV3
    product_gate:SpineProductGateV1
    deterministic_checks:dict[str,Any]
    lineage:dict[str,Any]
    human_review:dict[str,Any]
