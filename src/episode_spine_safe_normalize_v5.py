from __future__ import annotations

import copy
from typing import Any

from src.episode_spine_safe_normalize_v4 import normalize_episode_spine_syntax as normalize_episode_spine_syntax_v4


_STRING_LIST_FIELDS = {
    "constraints",
    "location_sequence",
    "movement_constraints",
    "causal_dependency_keys",
    "escalation_ladder",
    "supporting_beat_keys",
    "intended_milestone_keys",
    "completion_evidence",
    "writer_rules",
}


def _coerce_safe_string_lists(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Wrap scalar strings into one-item lists only for fields whose contract is list[str].

    This changes representation only; it never splits, merges, rewrites or invents semantic content.
    """
    value = copy.deepcopy(raw)
    repairs: list[dict[str, Any]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key in list(node.keys()):
                child = node[key]
                child_path = f"{path}.{key}" if path else key
                if key in _STRING_LIST_FIELDS and isinstance(child, str):
                    node[key] = [child]
                    repairs.append({
                        "kind": "coerce_scalar_string_to_list",
                        "field": child_path,
                        "old": child,
                        "new": [child],
                        "reason": "The contract requires list[str]; wrapping one scalar string preserves the same single semantic item.",
                    })
                else:
                    walk(child, child_path)
        elif isinstance(node, list):
            for idx, child in enumerate(node):
                walk(child, f"{path}[{idx}]")

    walk(value, "")
    return value, repairs


def _fill_decision_noop_new_information(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Allow a DECISION beat to add no new fact.

    A decision can legitimately operate on already-established evidence. When the model omits
    new_information entirely on a DECISION beat, the application may represent that absence as
    the empty string. No story fact is invented.
    """
    value = copy.deepcopy(raw)
    repairs: list[dict[str, Any]] = []
    beats = value.get("beats")
    if not isinstance(beats, list):
        return raw, []

    for idx, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        if beat.get("phase") != "DECISION":
            continue
        if "new_information" in beat:
            continue
        beat["new_information"] = ""
        repairs.append({
            "kind": "fill_decision_noop_new_information",
            "field": f"beats[{idx}].new_information",
            "old": None,
            "new": "",
            "reason": "DECISION may choose among established evidence without introducing a new fact; empty string is a semantic no-op.",
        })

    return value, repairs


def normalize_episode_spine_syntax(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """v5 generic, semantics-preserving contract-tolerance normalizer.

    v5 keeps all v4 authority protections and adds only:
    - scalar string -> one-item list coercion for known list[str] contract fields;
    - missing DECISION.new_information -> empty-string no-op.

    It does NOT:
    - create missing phases;
    - create beats, causal bridges, evidence, outcomes or branches;
    - invent facts;
    - repair authority violations;
    - convert substantive structural failure into PASS.
    """
    current, repairs = normalize_episode_spine_syntax_v4(copy.deepcopy(raw))
    all_repairs = list(repairs)

    for fn in (_coerce_safe_string_lists, _fill_decision_noop_new_information):
        candidate, next_repairs = fn(current)
        if next_repairs:
            current = candidate
            all_repairs.extend(next_repairs)

    return current, all_repairs
