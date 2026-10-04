from __future__ import annotations

import hashlib
import json
import os
import subprocess
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v21_model_adapter import (
    execute_final_audit_call,
    execute_initial_audit_call,
    execute_scene_repair_call,
)
from src.spineforge_v21_quality_runtime import run_bounded_quality


PROFILE_PATH = Path(
    "data/specifications/story_lab/"
    "spineforge_runtime_profile_v21_bounded_quality_frozen.json"
)
AUTHORIZATION_MARKER = "PAID-V21-BOUNDED-QUALITY-E2E"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_commit_message() -> str:
    completed = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _load_source_story(profile: dict[str, Any]) -> tuple[dict[str, Any], str]:
    source = profile["source_story"]
    artifact_path = Path(source["artifact_path"])
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact.get("status") != "FROZEN" or artifact.get("immutable") is not True:
        raise RuntimeError("v21 source story artifact must be frozen and immutable.")
    if artifact.get("artifact_id") != source["artifact_id"]:
        raise RuntimeError("v21 source story artifact id mismatch.")
    if artifact.get("repaired_story_text_sha256") != source["story_sha256"]:
        raise RuntimeError("v21 source story SHA binding mismatch.")

    story_path = Path(artifact["repaired_story_path"])
    story = story_path.read_text(encoding="utf-8")
    if story.endswith("\n"):
        story = story[:-1]
    if _sha256_text(story) != source["story_sha256"]:
        raise RuntimeError("v21 source story bytes do not match frozen SHA.")
    return artifact, story


def execute_paid_quality_once(
    *,
    api_key: str,
    run_id: str,
    profile_path: Path = PROFILE_PATH,
    output_root: Path = Path("evidence/spineforge-v21-paid-quality"),
    initial_audit_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    scene_repair_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    final_audit_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    verify_fn: Callable[[Path], dict[str, Any]] = verify_spineforge_runtime,
    require_commit_marker: bool = True,
    commit_message: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    paid = profile.get("paid_boundary") or {}
    if paid.get("paid_execution_authorized") is not True:
        raise RuntimeError("v21 paid quality execution is not authorized.")
    if paid.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("v21 paid authorization marker mismatch.")
    if paid.get("authorization_consumed") is not False:
        raise RuntimeError("v21 paid authorization is already consumed.")

    message = commit_message if commit_message is not None else current_commit_message()
    if require_commit_marker and f"[{AUTHORIZATION_MARKER}]" not in message:
        raise RuntimeError("v21 paid authorization marker missing from commit.")

    freeze = verify_fn(profile_path)
    artifact, story = _load_source_story(profile)
    approved_spine_hash = str(profile["source_story"]["approved_spine_hash"])
    canon_invariants = list(profile["source_story"]["canon_invariants"])
    stage_limits = dict(profile["cost_policy"]["quality_stage_limits_usd"])

    initial = initial_audit_fn or (
        lambda payload: execute_initial_audit_call(
            api_key=api_key,
            payload=payload,
        )
    )
    repair = scene_repair_fn or (
        lambda payload: execute_scene_repair_call(
            api_key=api_key,
            payload=payload,
        )
    )
    final = final_audit_fn or (
        lambda payload: execute_final_audit_call(
            api_key=api_key,
            payload=payload,
        )
    )

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "v21-bounded-quality-result.json"
    envelope_path = out_dir / "v21-bounded-quality-envelope.json"
    accepted_story_path = out_dir / "v21-accepted-story.txt"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v21-paid-quality-envelope.v1",
        "run_id": run_id,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "source_story_artifact_id": artifact["artifact_id"],
        "source_story_sha256": profile["source_story"]["story_sha256"],
        "max_quality_model_calls": 3,
        "result_status": "started",
        "automatic_retry_executed": False,
        "automatic_second_repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "accepted_story_path": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_bounded_quality(
            source_story_artifact_id=artifact["artifact_id"],
            source_story_sha256=profile["source_story"]["story_sha256"],
            source_story=story,
            story_segments=artifact["repaired_segments"],
            approved_spine_hash=approved_spine_hash,
            canon_invariants=canon_invariants,
            initial_audit_fn=initial,
            scene_repair_fn=repair,
            final_audit_fn=final,
            stage_cost_limits_usd={
                "INITIAL_AUDIT": float(stage_limits["initial_audit"]),
                "SCENE_REPAIR": float(stage_limits["scene_repair"]),
                "FINAL_AUDIT": float(stage_limits["final_audit"]),
            },
        )
    except Exception as exc:
        result = {
            "schema": "spineforge-v21-paid-quality-failure.v1",
            "status": "UNHANDLED_RUNTIME_FAILURE",
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "automatic_retry_executed": False,
            "automatic_second_repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    accepted_story = result.get("accepted_story")
    if isinstance(accepted_story, str) and accepted_story.strip():
        accepted_story_path.write_text(
            accepted_story.rstrip() + "\n",
            encoding="utf-8",
        )
        envelope["accepted_story_path"] = str(accepted_story_path)

    envelope["result_status"] = result.get("status")
    envelope["quality_usage_rollup"] = result.get("quality_usage_rollup")
    envelope["quality_model_calls"] = result.get("quality_model_calls")
    envelope["result_sha256"] = hashlib.sha256(result_path.read_bytes()).hexdigest()
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_quality_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V21_PAID_QUALITY_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V21_PAID_QUALITY_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
