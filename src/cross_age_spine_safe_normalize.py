from __future__ import annotations

import copy
from typing import Any


def normalize_logistics_location_sequence(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Qualification-only syntactic normalizer.

    The EpisodeSpine contract requires logistics_plan.location_sequence to contain
    canonical location refs. Sonnet may decorate those refs with parenthetical
    prose. We may strip only the decoration when:
    - the entry begins with one of the canonical beat location refs;
    - stripping produces exactly the ordered collapsed beat-location sequence;
    - no beat, premise, branch, evidence, or writer-rule semantics are changed.

    If those conditions are not met, return the payload unchanged so the
    canonical validator can reject it.
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
    sequence = [str(x).strip() for x in (logistics.get("location_sequence") or [])]
    canonical_refs = set(beat_locations)

    normalized: list[str] = []
    repairs: list[dict[str, Any]] = []

    for entry in sequence:
        if entry in canonical_refs:
            normalized.append(entry)
            continue

        matches = [
            ref
            for ref in canonical_refs
            if entry.startswith(ref + " (") and entry.endswith(")")
        ]
        if len(matches) != 1:
            return raw, []

        ref = matches[0]
        normalized.append(ref)
        repairs.append(
            {
                "field": "logistics_plan.location_sequence",
                "old": entry,
                "new": ref,
                "reason": "Removed parenthetical prose from an otherwise canonical location ref.",
            }
        )

    if normalized != beat_locations:
        return raw, []

    if repairs:
        logistics["location_sequence"] = normalized
    return value, repairs
