from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_story_local_repair_cycle2_once import (
    execute_story_local_repair_cycle2_once,
)


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
HANDOFF_PATH = Path(
    "evidence/spineforge-v20-story-local-repair-cycle2/37007924152-handoff.json"
)
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-STORY-LOCAL-REPAIR3"
LEGACY_CI_TRIGGER_MARKER = "PAID-V20-AGE12-ISLAND-WRITER2"


def execute_paid_story_local_repair_cycle2_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    run_fn: Callable[..., dict[str, Any]] = execute_story_local_repair_cycle2_once,
    profile_path: Path = PROFILE_PATH,
    handoff_path: Path = HANDOFF_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(profile_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    stage8 = profile.get("stage8_story_local_repair") or {}
    if stage8.get("paid_execution_authorized") is not True:
        raise RuntimeError("Stage 8 paid Story Local Repair is not authorized in frozen runtime.")
    if stage8.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("Stage 8 Story Local Repair authorization marker mismatch.")
    if int(stage8.get("paid_attempt_index") or 0) != 3:
        raise RuntimeError("Stage 8 Story Local Repair paid attempt index must be 3.")
    if stage8.get("automatic_retry_enabled") is not False:
        raise RuntimeError("Stage 8 automatic retry must remain disabled.")
    if stage8.get("automatic_repair_loop_enabled") is not False:
        raise RuntimeError("Stage 8 automatic repair loop must remain disabled.")
    if stage8.get("handoff_path") != str(handoff_path):
        raise RuntimeError("Stage 8 handoff path mismatch.")

    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != stage8.get("handoff_artifact_id"):
        raise RuntimeError("Stage 8 handoff artifact mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Immutable Stage 8 handoff must remain non-authorizing.")

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-story-local-repair3-result.json"
    story_path = out_dir / "age12-island-v20-story-local-repair3-story.txt"
    envelope_path = out_dir / "age12-island-v20-story-local-repair3-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-story-local-repair-cycle2-envelope.v1",
        "stage": 8,
        "repair_cycle_index": 2,
        "paid_attempt_index": 3,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "legacy_ci_trigger_marker": LEGACY_CI_TRIGGER_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "source_stage7_product_artifact_id": handoff[
            "source_stage7_product_artifact_id"
        ],
        "source_story_sha256": handoff["source_story_sha256"],
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
        )
    except Exception as exc:
        provider_trace = getattr(exc, "trace", None)
        result = {
            "schema": "spineforge-v20-story-local-repair-cycle2-execution.v1",
            "status": "unhandled_story_local_repair_cycle2_runtime_failure",
            "stage": 8,
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
    result, envelope = execute_paid_story_local_repair_cycle2_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_STORY_LOCAL_REPAIR_CYCLE2_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_STORY_LOCAL_REPAIR_CYCLE2_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
