from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpineForgeContextCaseV10_1(StrictModel):
    schema_id: Literal["spineforge-context-case.v10.1"] = Field(alias="schema")
    case_id: str
    runtime_profile: str
    canonical_state_source: str
    expected_context_pack_id: str
    expected_context_fingerprint: str
    qualification_kind: str
    exact_age: int = Field(ge=3, le=120)
    narrative_family: str
    status: str
    cost_ledger: str
    max_attempts: int = Field(ge=1, le=5)
    rules: dict[str, Any]


def load_spineforge_v10_1_case(path: Path) -> SpineForgeContextCaseV10_1:
    payload = SpineForgeContextCaseV10_1.model_validate_json(path.read_text(encoding="utf-8"))
    for label, value in (
        ("runtime_profile", payload.runtime_profile),
        ("canonical_state_source", payload.canonical_state_source),
    ):
        p = Path(value)
        if not p.exists():
            raise RuntimeError(f"SpineForge v10.1 case {label} does not exist: {p}")
    return payload
