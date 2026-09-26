from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_profile(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _range_for_profile(profile: dict[str, Any]) -> tuple[int, int] | None:
    hard = profile.get("hard_word_range")
    if isinstance(hard, dict):
        return int(hard["min"]), int(hard["max"])

    publication = profile.get("publication_length_policy")
    if isinstance(publication, dict):
        reference = publication.get("reference_word_range")
        if isinstance(reference, dict):
            return int(reference["min"]), int(reference["max"])
    return None


def length_observation(profile: dict[str, Any], word_count: int) -> dict[str, Any]:
    word_range = _range_for_profile(profile)
    if word_range is None:
        return {
            "outside_reference_range": False,
            "blocking": False,
            "class": None,
        }

    minimum, maximum = word_range
    outside = word_count < minimum or word_count > maximum

    publication = profile.get("publication_length_policy")
    if isinstance(publication, dict):
        deterministic_hard_fail = bool(
            publication.get("deterministic_hard_fail", False)
        )
        return {
            "outside_reference_range": outside,
            "blocking": outside and deterministic_hard_fail,
            "class": (
                "hard_length_failure"
                if outside and deterministic_hard_fail
                else "length_deviation" if outside else None
            ),
        }

    return {
        "outside_reference_range": outside,
        "blocking": outside,
        "class": "hard_length_failure" if outside else None,
    }


def publication_ready(
    profile: dict[str, Any],
    word_count: int,
    findings: list[dict[str, Any]],
) -> bool:
    length = length_observation(profile, word_count)
    if length["blocking"]:
        return False

    hard_fail_classes = set(profile.get("hard_fail_classes") or [])
    blocking_severities = set(profile.get("blocking_severities") or [])

    for finding in findings:
        if (
            finding.get("class") in hard_fail_classes
            and finding.get("severity") in blocking_severities
        ):
            return False

    return True
