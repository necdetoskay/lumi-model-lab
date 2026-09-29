from __future__ import annotations

import copy
from typing import Any


def normalize_reversal_support_refs(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Qualification-only safe normalizer.

    It may remove self/future reversal evidence references ONLY when the same
    evidence item already has at least one valid pre-reversal support ref.
    It never edits claims, certainty, beats, outcomes, or adds evidence.
    If an evidence item has no valid pre-reversal support, it is left untouched
    so the canonical validator can reject it.
    """
    value = copy.deepcopy(raw)
    beats = list(value.get("beats") or [])
    reversal_index = next(
        (idx for idx, beat in enumerate(beats) if beat.get("phase") == "REVERSAL"),
        None,
    )
    if reversal_index is None:
        return value, []

    pre_reversal = {
        str(beat.get("key"))
        for beat in beats[:reversal_index]
        if beat.get("key") is not None
    }

    repairs: list[dict[str, Any]] = []
    reversal = value.get("reversal") or {}
    for idx, evidence in enumerate(reversal.get("evidence") or []):
        refs = [str(x) for x in (evidence.get("supporting_beat_keys") or [])]
        valid = [ref for ref in refs if ref in pre_reversal]
        invalid = [ref for ref in refs if ref not in pre_reversal]

        if invalid and valid:
            evidence["supporting_beat_keys"] = valid
            repairs.append(
                {
                    "evidence_index": idx,
                    "claim": str(evidence.get("claim") or ""),
                    "removed_refs": invalid,
                    "kept_refs": valid,
                    "reason": "Removed only self/future refs; at least one valid pre-reversal support remained.",
                }
            )

    return value, repairs
