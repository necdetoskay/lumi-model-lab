from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


DIMENSION_ALIASES = {
    "CHARACTER_DRIVENESS": "CHARACTER_DRIVENNESS",
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuditAliasChangeV13(StrictModel):
    path: str
    before: str
    after: str
    semantic_change: bool = False


class AuditAliasNormalizationReportV13(StrictModel):
    schema_id: str = Field(
        default="spineforge-v13-audit-alias-normalization.v1",
        alias="schema",
    )
    changed: bool
    changes: list[AuditAliasChangeV13]
    decision_unchanged: bool = True
    scores_unchanged: bool = True
    blockers_unchanged: bool = True
    repair_targets_unchanged: bool = True


class AuditAliasNormalizationError(ValueError):
    pass


def normalize_audit_contract_aliases(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], AuditAliasNormalizationReportV13]:
    if not isinstance(raw, dict):
        raise AuditAliasNormalizationError("Audit output must be an object.")
    dimensions = raw.get("dimensions")
    if not isinstance(dimensions, list):
        raise AuditAliasNormalizationError("Audit dimensions must be a list.")

    normalized = copy.deepcopy(raw)
    changes: list[AuditAliasChangeV13] = []

    for index, row in enumerate(normalized["dimensions"]):
        if not isinstance(row, dict):
            raise AuditAliasNormalizationError(
                f"Audit dimensions[{index}] must be an object."
            )
        name = row.get("name")
        if not isinstance(name, str):
            raise AuditAliasNormalizationError(
                f"Audit dimensions[{index}].name must be a string."
            )
        alias = DIMENSION_ALIASES.get(name)
        if alias is not None:
            row["name"] = alias
            changes.append(
                AuditAliasChangeV13(
                    path=f"dimensions[{index}].name",
                    before=name,
                    after=alias,
                    semantic_change=False,
                )
            )

    return normalized, AuditAliasNormalizationReportV13(
        changed=bool(changes),
        changes=changes,
    )
