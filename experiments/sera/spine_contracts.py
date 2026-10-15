"""Read-only conversion of a frozen episode-spine.v2 into SERA scene contracts.

No prose generation, paid model calls or writes to the Spine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SOURCE_BLOB_SHA = "fe1dda0047000438bbfaac69022e835bf7e0a1f8"
SOURCE_RELATIVE_PATH = (
    "evidence/v4-2-mara-run-38794774463/"
    "sonnet-original-spine-pre-haiku.json"
)


class SpineContractError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def load_frozen_spine(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    actual = git_blob_sha(raw)
    if actual != SOURCE_BLOB_SHA:
        raise SpineContractError(
            f"SPINE_BLOB_MISMATCH: {actual}, expected {SOURCE_BLOB_SHA}"
        )
    spine = json.loads(raw)
    if spine.get("schema") != "episode-spine.v2":
        raise SpineContractError("SPINE_SCHEMA_UNSUPPORTED")
    return spine


def compile_scene_contracts(spine: dict[str, Any]) -> list[dict[str, Any]]:
    """9 beats -> 9 derived contracts for the first controlled experiment.

    The source remains unchanged. Textual desired outcomes are expectations,
    not evidence-backed accepted exit state.
    """
    beats = spine.get("beats")
    if not isinstance(beats, list) or not beats:
        raise SpineContractError("SPINE_BEATS_INVALID")

    all_keys = [beat.get("key") for beat in beats if isinstance(beat, dict)]
    if len(all_keys) != len(beats) or any(not isinstance(k, str) or not k for k in all_keys):
        raise SpineContractError("SPINE_BEAT_KEY_INVALID")
    if len(all_keys) != len(set(all_keys)):
        raise SpineContractError("SPINE_BEAT_KEY_DUPLICATE")

    source_locations = spine["logistics_plan"]["location_sequence"]
    derived_locations = []
    done = set()
    result = []
    for index, beat in enumerate(beats, start=1):
        key = beat["key"]
        deps = beat.get("causal_dependency_keys", [])
        if not isinstance(deps, list) or any(d not in done for d in deps):
            raise SpineContractError(f"FORWARD_OR_UNKNOWN_DEPENDENCY:{key}")
        location = beat.get("location_ref")
        if not isinstance(location, str) or not location:
            raise SpineContractError(f"BEAT_LOCATION_MISSING:{key}")
        if not derived_locations or derived_locations[-1] != location:
            derived_locations.append(location)
        result.append({
            "schema": "sera.scene-contract.v0.1",
            "spine_blob_sha": SOURCE_BLOB_SHA,
            "scene_index": index,
            "key": key,
            "phase": beat["phase"],
            "purpose": beat["purpose"],
            "location_ref": location,
            "causal_dependency_keys": list(deps),
            "expected_event": beat["external_event"],
            "planned_character_action": beat["character_action"],
            "expected_new_information": beat["new_information"],
            "expected_state_change": beat["state_change"],
            "payoff_contribution": beat["payoff_contribution"],
            "global_constraints": list(spine["constraints"]),
            "writer_rules": list(spine["writer_rules"]),
            "decision_outcome_uncommitted": (
                bool(spine.get("decision_point", {}).get("outcome_uncommitted"))
                if beat["phase"] == "DECISION" else None
            ),
            "authority": "DERIVED_PLAN_ONLY",
        })
        done.add(key)

    if derived_locations != source_locations:
        raise SpineContractError(
            f"LOCATION_SEQUENCE_MISMATCH:{derived_locations!r} != {source_locations!r}"
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="SERA read-only Spine contract compiler")
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    spine = load_frozen_spine(args.source)
    contracts = compile_scene_contracts(spine)
    print(json.dumps({
        "experiment": "SERA v0.1",
        "story": spine["title"],
        "source_blob_sha": SOURCE_BLOB_SHA,
        "scene_count": len(contracts),
        "scenes": [
            {
                "scene_index": c["scene_index"],
                "key": c["key"],
                "phase": c["phase"],
                "location_ref": c["location_ref"],
                "dependencies": c["causal_dependency_keys"],
            }
            for c in contracts
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
