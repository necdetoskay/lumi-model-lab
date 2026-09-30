from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


DERIVED_PATH = "logistics_plan.location_sequence"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MechanicalNormalizationChangeV12(StrictModel):
    path: str
    source: str
    before: Any = None
    after: Any
    semantic_change: bool = False


class MechanicalNormalizationReportV12(StrictModel):
    schema_id: str = Field(
        default="spineforge-v12-mechanical-normalization.v1",
        alias="schema",
    )
    changed: bool
    changes: list[MechanicalNormalizationChangeV12]
    protected_paths_unchanged: bool = True


class MechanicalNormalizationError(ValueError):
    pass


def derive_ordered_beat_location_sequence(raw: dict[str, Any]) -> list[str]:
    beats = raw.get("beats")
    if not isinstance(beats, list) or not beats:
        raise MechanicalNormalizationError(
            "Cannot derive route: beats must be a non-empty list."
        )

    ordered: list[str] = []
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise MechanicalNormalizationError(
                f"Cannot derive route: beat[{index}] is not an object."
            )
        location = beat.get("location_ref")
        if not isinstance(location, str) or not location.strip():
            raise MechanicalNormalizationError(
                f"Cannot derive route: beat[{index}].location_ref is missing or invalid."
            )
        if not ordered or ordered[-1] != location:
            ordered.append(location)
    return ordered


def normalize_mechanical_fields(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], MechanicalNormalizationReportV12]:
    if not isinstance(raw, dict):
        raise MechanicalNormalizationError("Architect output must be an object.")

    logistics = raw.get("logistics_plan")
    if not isinstance(logistics, dict):
        raise MechanicalNormalizationError(
            "Cannot normalize route: logistics_plan must be an object."
        )

    normalized = copy.deepcopy(raw)
    derived_route = derive_ordered_beat_location_sequence(raw)
    before = copy.deepcopy(logistics.get("location_sequence"))

    changes: list[MechanicalNormalizationChangeV12] = []
    if before != derived_route:
        normalized["logistics_plan"]["location_sequence"] = derived_route
        changes.append(
            MechanicalNormalizationChangeV12(
                path=DERIVED_PATH,
                source="ordered beat.location_ref transitions",
                before=before,
                after=derived_route,
                semantic_change=False,
            )
        )

    return normalized, MechanicalNormalizationReportV12(
        changed=bool(changes),
        changes=changes,
        protected_paths_unchanged=True,
    )
