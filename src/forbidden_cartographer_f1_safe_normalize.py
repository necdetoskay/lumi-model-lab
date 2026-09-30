from __future__ import annotations

import copy
from typing import Any


def normalize_missing_final_return_location(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Qualification-only syntactic normalizer.

    Allowed repair:
    - collapse consecutive beat location refs;
    - existing logistics sequence must equal that sequence except for ONE missing
      final location;
    - missing final location must be a return to a location already present
      earlier in the logistics sequence;
    - only logistics_plan.location_sequence may change.

    This cannot add/change beats, timing, evidence, branches, outcomes, claims,
    writer rules, or locations not already used by beats.
    """
    value = copy.deepcopy(raw)
    beats = list(value.get("beats") or [])

    beat_locations: list[str] = []
    for beat in beats:
        ref = str(beat.get("location_ref") or "").strip()
        if not ref:
            continue
        if not beat_locations or beat_locations[-1] != ref:
            beat_locations.append(ref)

    logistics = value.get("logistics_plan") or {}
    existing = [str(x).strip() for x in (logistics.get("location_sequence") or [])]

    if len(beat_locations) != len(existing) + 1:
        return raw, []
    if existing != beat_locations[:-1]:
        return raw, []

    missing = beat_locations[-1]
    if missing not in existing:
        return raw, []

    logistics["location_sequence"] = beat_locations
    return value, [{
        "field": "logistics_plan.location_sequence",
        "old": existing,
        "new": beat_locations,
        "reason": (
            "Added only the omitted final return location already present in the "
            "beat sequence; no semantic story field changed."
        ),
    }]
