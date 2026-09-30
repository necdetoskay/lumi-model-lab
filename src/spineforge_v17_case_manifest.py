from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SpineForgeV17AuditCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_id: str = Field(alias="schema")
    case_id: str
    runtime_profile: str
    source_evidence_path: str
    expected_context_pack_id: str
    expected_context_fingerprint: str
    qualification_kind: str
    status: str
    cost_ledger: str
    max_attempts: int
    rules: dict[str, bool]


def load_spineforge_v17_case(path: Path) -> SpineForgeV17AuditCase:
    return SpineForgeV17AuditCase.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )
