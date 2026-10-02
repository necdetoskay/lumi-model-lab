from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_story_local_repair_once import (
    execute_story_local_repair_once,
)


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
HANDOFF_PATH = Path(
    "evidence/spineforge-v20-story-local-repair/36990160527-handoff.json"
)
PROMPT_PATH = Path("prompts/spineforge_v20_story_local_repair.md")
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR1"
LEGACY_CI_TRIGGER_MARKER = "PAID-V20-AGE12-ISLAND-WRITER2"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_story_local_repair_failure_result(exc: Exception) -> dict[str, Any]:
    provider_trace = getattr(exc, "trace", None)
    return {
        "schema": "spineforge-v20-story-local-repair-execution.v1",
        "status": "unhandled_story_local_repair_runtime_failure",
        "stage": 6,
        "failure": {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "provider_trace": provider_trace if isinstance(provider_trace, dict) else None,
        },
        "automatic_retry_executed": False,
        "reaudit_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
    }


def execute_paid_story_local_repair_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    run_fn: Callable[..., dict[str, Any]] = execute_story_local_repair_once,
    profile_path: Path = PROFILE_PATH,
    handoff_path: Path = HANDOFF_PATH,
    prompt_path: Path = PROMPT_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(profile_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    stage6 = profile.get("stage6_story_local_repair") or {}
    if stage6.get("paid_execution_authorized") is not True:
        raise RuntimeError(
            "Stage 6 paid Story Local Repair is not authorized in frozen runtime."
        )
    if stage6.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("Stage 6 paid Story Local Repair authorization marker mismatch.")
    if int(stage6.get("repair_attempt_index") or 0) != 1:
        raise RuntimeError("Stage 6 Story Local Repair attempt index must be 1.")
    if stage6.get("automatic_retry_enabled") is not False:
        raise RuntimeError("Stage 6 Story Local Repair automatic retry must remain disabled.")
    if stage6.get("automatic_repair_loop_enabled") is not False:
        raise RuntimeError(
            "Stage 6 Story Local Repair automatic repair loop must remain disabled."
        )
    if stage6.get("handoff_path") != str(handoff_path):
        raise RuntimeError("Stage 6 Story Local Repair handoff path mismatch.")
    if stage6.get("handoff_sha256") != _sha256_file(handoff_path):
        raise RuntimeError("Stage 6 Story Local Repair handoff SHA mismatch.")

    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != stage6.get("handoff_artifact_id"):
        raise RuntimeError("Stage 6 Story Local Repair handoff artifact mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Immutable Stage 6 handoff must remain non-authorizing.")

    system_prompt = prompt_path.read_text(encoding="utf-8").strip()

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-story-local-repair1-result.json"
    story_path = out_dir / "age12-island-v20-story-local-repair1-story.txt"
    envelope_path = out_dir / "age12-island-v20-story-local-repair1-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-story-local-repair-envelope.v1",
        "stage": 6,
        "attempt_index": 1,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "legacy_ci_trigger_marker": LEGACY_CI_TRIGGER_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "source_handoff_artifact_id": handoff["artifact_id"],
        "source_story_sha256": handoff["source_story_sha256"],
        "source_audit_artifact_id": handoff["source_audit_artifact_id"],
        "repair_model": handoff["repair_model"],
        "result_status": "started",
        "automatic_retry_executed": False,
        "reaudit_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "story_path": str(story_path),
        "repair_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(
            api_key=api_key,
            handoff=handoff,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        result = build_story_local_repair_failure_result(exc)

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    repaired_story = result.get("repaired_story")
    if isinstance(repaired_story, str) and repaired_story.strip():
        story_path.write_text(repaired_story.rstrip() + "\n", encoding="utf-8")

    envelope["result_status"] = result.get("status")
    envelope["repair_usage_rollup"] = result.get("repair_usage_rollup")
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_story_local_repair_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_STORY_LOCAL_REPAIR_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_STORY_LOCAL_REPAIR_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
