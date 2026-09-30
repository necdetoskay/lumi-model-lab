from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.spineforge_contract import SpineForgeProductV1
from src.spineforge_revision import SpineForgeRevisionFeedbackV1


class StrictModel(BaseModel):
    model_config=ConfigDict(extra="forbid")


class SpineForgeRevisionFeedbackV2(StrictModel):
    schema_id:Literal["spineforge-revision-feedback.v2"]=Field(alias="schema")
    context_pack_id:str
    context_fingerprint:str
    feedback:SpineForgeRevisionFeedbackV1


class SpineForgeProductV2(StrictModel):
    schema_id:Literal["spineforge-product.v2"]=Field(alias="schema")
    context_pack_id:str
    context_fingerprint:str
    product:SpineForgeProductV1
