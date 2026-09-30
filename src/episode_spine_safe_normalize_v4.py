from __future__ import annotations

import copy
from typing import Any


def _collapsed_beat_locations(raw: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for beat in raw.get("beats") or []:
        ref = str(beat.get("location_ref") or "").strip()
        if ref and (not out or out[-1] != ref):
            out.append(ref)
    return out


def _normalize_location_decorations(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = copy.deepcopy(raw)
    beat_locations = _collapsed_beat_locations(value)
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
        repairs.append({
            "kind": "strip_location_decoration",
            "field": "logistics_plan.location_sequence",
            "old": entry,
            "new": ref,
            "reason": "Removed parenthetical prose from a canonical beat location ref.",
        })

    logistics["location_sequence"] = normalized
    return value, repairs


def _normalize_one_missing_final_return(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = copy.deepcopy(raw)
    beat_locations = _collapsed_beat_locations(value)
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
        "kind": "append_omitted_final_return",
        "field": "logistics_plan.location_sequence",
        "old": existing,
        "new": beat_locations,
        "reason": (
            "Added only one omitted final return location that is already present "
            "in the ordered beat sequence and was visited earlier."
        ),
    }]


def _normalize_reversal_support_refs(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    value = copy.deepcopy(raw)
    beats = list(value.get("beats") or [])
    reversal_index = next(
        (idx for idx, beat in enumerate(beats) if beat.get("phase") == "REVERSAL"),
        None,
    )
    if reversal_index is None:
        return raw, []

    established_through_reversal = {
        str(beat.get("key"))
        for beat in beats[:reversal_index + 1]
        if beat.get("key") is not None
    }
    repairs: list[dict[str, Any]] = []
    reversal = value.get("reversal") or {}

    for idx, evidence in enumerate(reversal.get("evidence") or []):
        refs = [str(x) for x in (evidence.get("supporting_beat_keys") or [])]
        valid = [ref for ref in refs if ref in established_through_reversal]
        invalid = [ref for ref in refs if ref not in established_through_reversal]
        if invalid and valid:
            evidence["supporting_beat_keys"] = valid
            repairs.append({
                "kind": "remove_future_reversal_support",
                "field": f"reversal.evidence[{idx}].supporting_beat_keys",
                "removed": invalid,
                "kept": valid,
                "reason": (
                    "Removed only future support refs while retaining at least "
                    "one support ref established at or before the reversal."
                ),
            })

    return value, repairs


def normalize_episode_spine_syntax(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Generic, semantics-preserving qualification/runtime normalizer.

    It is intentionally narrow. It may:
    - strip parenthetical prose from canonical location refs;
    - append one omitted final return location already explicit in the beats;
    - remove future reversal support refs only when valid support established
      at or before the reversal remains.

    It must never edit beats, claims, evidence certainty, branches, outcomes,
    writer rules, premise keys, word targets, or introduce a new location.
    """
    current = copy.deepcopy(raw)
    all_repairs: list[dict[str, Any]] = []

    for fn in (
        _normalize_location_decorations,
        _normalize_one_missing_final_return,
        _normalize_reversal_support_refs,
    ):
        candidate, repairs = fn(current)
        if repairs:
            current = candidate
            all_repairs.extend(repairs)

    return current, all_repairs
