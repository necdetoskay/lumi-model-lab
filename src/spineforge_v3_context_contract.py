from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.spineforge_v3_contract import SpineForgeProductV1


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class SpineForgeRevisionFeedbackV3(StrictModel):
    schema_id:Literal["spineforge-revision-feedback.v3"]=Field(alias="schema")
    context_pack_id:str
    context_fingerprint:str
    source_attempt:int=Field(ge=1)
    next_attempt:int=Field(ge=2)
    source_status:Literal[
        "creative_contract_rejected",
        "creative_replan_required",
        "product_replan_required",
        "human_revise",
    ]
    must_preserve:list[str]=Field(min_length=2,max_length=12)
    must_change:list[str]=Field(min_length=1,max_length=12)
    creative_feedback:list[str]=Field(min_length=1,max_length=12)
    structural_feedback:list[str]=Field(default_factory=list,max_length=12)
    previous_creative_signature:dict[str,Any]|None=None
    previous_spine_raw:dict[str,Any]|None=None
    validation_errors:list[str]=Field(default_factory=list,max_length=12)
    authority_freezes:list[str]=Field(min_length=1,max_length=20)

    @model_validator(mode="after")
    def validate_attempts(self)->"SpineForgeRevisionFeedbackV3":
        if self.next_attempt!=self.source_attempt+1:
            raise ValueError("next_attempt must equal source_attempt + 1")
        return self


class SpineForgeProductV3(StrictModel):
    schema_id:Literal["spineforge-product.v3"]=Field(alias="schema")
    context_pack_id:str
    context_fingerprint:str
    product:SpineForgeProductV1
