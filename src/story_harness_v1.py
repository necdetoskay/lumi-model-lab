"""LUMI Story Harness V1: zero-cost, read-only stage-artifact lineage replay.

Does not run models, original story stages, validators, network or subprocesses.
Fixture-provided PASS is NEVER promoted to an authenticated stage-gate pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

PLAN_SCHEMA = "lumi.story-harness-plan.v1"
REPORT_SCHEMA = "lumi.story-harness-replay.v1"
STAGE_ORDER = ("context", "spine", "writer", "q25", "quality", "finalization")
GATES = frozenset({"REPORTED_PASS", "REPORTED_REJECT", "REPORTED_REVIEW"})
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
STAGE_KEYS = frozenset({
    "stage_id", "artifact", "sha256", "depends_on",
    "consumed_sha256", "reported_gate",
})
PLAN_KEYS = frozenset({"schema", "run_id", "mode", "budget", "stages"})
MAX_FILE_BYTES = 1_048_576


class HarnessStop(ValueError):
    """Fail closed: never execute a later stage or treat plan metadata as truth."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_keys(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise HarnessStop("Duplicate JSON key is forbidden")
        result[name] = value
    return result


def load_json(data: bytes):
    def disallow_constant(value):
        raise HarnessStop("Nonfinite JSON constant is forbidden")
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_keys,
            parse_constant=disallow_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HarnessStop("Invalid UTF-8 JSON file") from exc


def secure_artifact(root: Path, path: str) -> bytes:
    """Reject symlinks, traversal and unqualified non-JSON artifacts."""
    if not isinstance(path, str) or not path:
        raise HarnessStop("Invalid artifact path")
    relative = Path(path)
    if (relative.is_absolute() or ".." in relative.parts or
            "." in relative.parts or "\\" in path or
            relative.suffix != ".json" or len(relative.parts) < 2):
        raise HarnessStop("Artifact must be a safe repository-relative JSON path")
    cursor = root
    for component in relative.parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise HarnessStop("Symlinked artifact paths are not allowed")
    qualified = cursor.resolve()
    if not qualified.is_relative_to(root):
        raise HarnessStop("Artifact path escaped its repository root")
    if not qualified.is_file() or qualified.stat().st_size > MAX_FILE_BYTES:
        raise HarnessStop("Artifact missing or too large")
    data = qualified.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise HarnessStop("Artifact became too large during read")
    load_json(data)
    return data


def _plan_checks(plan: dict):
    if not isinstance(plan, dict) or set(plan) != PLAN_KEYS:
        raise HarnessStop("Unexpected or missing plan field")
    if (plan["schema"] != PLAN_SCHEMA or
            plan["mode"] != "OFFLINE_REPLAY_ONLY" or
            not isinstance(plan["run_id"], str) or
            RUN_RE.fullmatch(plan["run_id"]) is None):
        raise HarnessStop("Unqualified story harness replay mode or run ID")
    if plan["budget"] != {"max_provider_calls": 0, "max_cost_usd": "0"}:
        raise HarnessStop("V1 paid provider calls and spending are forbidden")
    stages = plan["stages"]
    if not isinstance(stages, list) or not (1 <= len(stages) <= len(STAGE_ORDER)):
        raise HarnessStop("Invalid stage count")
    previous = None
    indexes = []
    for item in stages:
        if not isinstance(item, dict) or set(item) != STAGE_KEYS:
            raise HarnessStop("Unexpected or missing stage field")
        stage = item["stage_id"]
        if not isinstance(stage, str) or stage not in STAGE_ORDER:
            raise HarnessStop("Unsupported story stage")
        indexes.append(STAGE_ORDER.index(stage))
        if not isinstance(item["sha256"], str) or not SHA_RE.fullmatch(item["sha256"]):
            raise HarnessStop("Malformed stage artifact SHA")
        if item["reported_gate"] not in GATES:
            raise HarnessStop("Unsupported reported gate status")
        if previous is None:
            if item["depends_on"] is not None or item["consumed_sha256"] is not None:
                raise HarnessStop("Initial stage cannot invent a predecessor")
        else:
            if item["depends_on"] != previous["stage_id"]:
                raise HarnessStop("Stage dependency is not the previous stage")
            if item["consumed_sha256"] != previous["sha256"]:
                raise HarnessStop("Stage input SHA does not match prior artifact")
        previous = item
    if indexes != sorted(set(indexes)):
        raise HarnessStop("Stage order or identity is invalid")


def replay(plan: dict, *, repo_root: Path | str) -> dict:
    """Inspect exact archived bytes. No actual gate is invoked or certified."""
    _plan_checks(plan)
    root = Path(repo_root).resolve(strict=True)
    rows = []
    for stage in plan["stages"]:
        artifact = secure_artifact(root, stage["artifact"])
        actual = digest(artifact)
        if actual != stage["sha256"]:
            raise HarnessStop("Stage artifact integrity mismatch: " + stage["stage_id"])
        rows.append({
            "stage_id": stage["stage_id"],
            "artifact": stage["artifact"],
            "verified_artifact_sha256": actual,
            "depends_on": stage["depends_on"],
            "consumed_sha256": stage["consumed_sha256"],
            "reported_gate": stage["reported_gate"],
            "gate_decision_authoritatively_verified": False,
            "actual_stage_invoked": False,
            "provider_calls": 0,
            "provider_cost_usd": "0",
        })
        if stage["reported_gate"] != "REPORTED_PASS":
            break
    last = rows[-1]["reported_gate"]
    status = (
        "STOPPED_ON_REPORTED_REJECT" if last == "REPORTED_REJECT"
        else "STOPPED_ON_REPORTED_REVIEW" if last == "REPORTED_REVIEW"
        else "REPLAYED_REPORTED_CHAIN_ONLY"
    )
    return {
        "schema": REPORT_SCHEMA,
        "run_id": plan["run_id"],
        "plan_sha256": digest(canonical_bytes(plan)),
        "status": status,
        "stage_count_planned": len(plan["stages"]),
        "stage_count_inspected": len(rows),
        "downstream_blocked": status != "REPLAYED_REPORTED_CHAIN_ONLY",
        "stages": rows,
        "gate_decision_authoritatively_verified": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "model_execution_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": "0",
    }


def archive_once(result: dict, *, repo_root: Path | str) -> Path:
    """Optional artifact recording ONLY in repo/runs/story_harness_v1/<run_id>."""
    root = Path(repo_root).resolve(strict=True)
    if result.get("schema") != REPORT_SCHEMA or result.get("state_commit_authorized") is not False:
        raise HarnessStop("Invalid or promoted replay manifest")
    run_id = result.get("run_id")
    if not isinstance(run_id, str) or RUN_RE.fullmatch(run_id) is None:
        raise HarnessStop("Unsafe replay archive ID")
    run_base = root / "runs" / "story_harness_v1"
    for check in (root / "runs", run_base):
        if check.is_symlink():
            raise HarnessStop("Symlinked archive directory is forbidden")
    run_base.mkdir(parents=True, exist_ok=True)
    run_dir = run_base / run_id
    run_dir.mkdir(mode=0o700, exist_ok=False)
    target = run_dir / "manifest.json"
    with target.open("xb") as output:
        output.write(json.dumps(
            result, sort_keys=True, ensure_ascii=False, indent=2,
        ).encode("utf-8") + b"\n")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--archive-once", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve(strict=True)
    plan = load_json(secure_artifact(root, args.plan))
    result = replay(plan, repo_root=root)
    if args.archive_once:
        archive_once(result, repo_root=root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
