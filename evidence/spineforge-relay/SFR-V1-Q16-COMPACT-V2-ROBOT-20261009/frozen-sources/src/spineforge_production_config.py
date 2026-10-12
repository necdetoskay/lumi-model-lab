"""Model-neutral run policy; no scenario-specific behavior."""
from typing import Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel


class RunConfigV1(StrictModel):
    schema_name: Literal["spineforge.run-config.v1"]="spineforge.run-config.v1"
    planner: str="openai/gpt-5.6-sol"
    plan_guard: str="anthropic/claude-sonnet-5.5"
    writer: str="openai/gpt-5.6-sol"
    scene_guard: str="anthropic/claude-sonnet-5.5"
    planner_max_tokens: int=Field(default=12000,ge=1000,le=16000,strict=True)
    plan_guard_max_tokens: int=Field(default=2000,ge=500,le=4000,strict=True)
    writer_max_tokens: int=Field(default=3500,ge=500,le=5000,strict=True)
    scene_guard_max_tokens: int=Field(default=5000,ge=500,le=7000,strict=True)
    max_total_cost_usd: float=Field(default=1.20,gt=0,allow_inf_nan=False,strict=True)
    max_call_cost_usd: float=Field(default=.30,gt=0,allow_inf_nan=False,strict=True)
    max_scene_call_cost_usd: float=Field(default=.15,gt=0,allow_inf_nan=False,strict=True)
    max_plan_rewrites: Literal[1]=1
    max_scene_rewrites: Literal[1]=1
    automatic_retry: Literal[False]=False

    def models(self):return sorted({self.planner,self.plan_guard,self.writer,self.scene_guard})
