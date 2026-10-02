from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_story_reaudit_cycle2_once import execute_story_reaudit_cycle2_once


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
HANDOFF_PATH = Path(
    "evidence/spineforge-v20-story-reaudit-cycle2/37010331757-handoff.json"
)
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-STORY-REAUDIT2"
LEGACY_CI_TRIGGER_MARKER = "PAID-V20-AGE12-ISLAND-WRITER2"


def execute_paid_story_reaudit_cycle2_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    run_fn: Callable[..., dict[str, Any]] = execute_story_reaudit_cycle2_once,
    profile_path: Path = PROFILE_PATH,
    handoff_path: Path = HANDOFF_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(profile_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    stage9 = profile.get("stage9_story_reaudit") or {}
    if stage9.get("paid_execution_authorized") is not True:
        raise RuntimeError("Stage 9 paid Story Re-audit is not authorized in frozen runtime.")
    if stage9.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("Stage 9 Story Re-audit authorization marker mismatch.")
    if int(stage9.get("reaudit_attempt_index") or 0) != 2:
        raise RuntimeError("Stage 9 Story Re-audit attempt index must be 2.")
    if stage9.get("automatic_retry_enabled") is not False:
        raise RuntimeError("Stage 9 automatic retry must remain disabled.")
    if stage9.get("automatic_repair_loop_enabled") is not False:
        raise RuntimeError("Stage 9 automatic repair loop must remain disabled.")
    if stage9.get("handoff_path") != str(handoff_path):
        raise RuntimeError("Stage 9 handoff path mismatch.")

    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != stage9.get("handoff_artifact_id"):
        raise RuntimeError("Stage 9 handoff artifact mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Immutable Stage 9 handoff must remain non-authorizing.")

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-story-reaudit2-result.json"
    envelope_path = out_dir / "age12-island-v20-story-reaudit2-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-story-reaudit-cycle2-envelope.v1",
        "stage": 9,
        "reaudit_attempt_index": 2,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "legacy_ci_trigger_marker": LEGACY_CI_TRIGGER_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "source_stage8_artifact_id": handoff["source_stage8_artifact_id"],
        "source_repaired_story_sha256": handoff["repaired_story_text_sha256"],
        "result_status": "started",
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "reaudit_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(api_key=api_key, handoff_path=handoff_path)
    except Exception as exc:
        provider_trace = getattr(exc, "trace", None)
        result = {
            "schema": "spineforge-v20-story-reaudit-cycle2-execution.v1",
            "status": "unhandled_story_reaudit_cycle2_runtime_failure",
            "stage": 9,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "provider_trace": provider_trace if isinstance(provider_trace, dict) else None,
            },
            "automatic_retry_executed": False,
            "repair_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    envelope["result_status"] = result.get("status")
    envelope["reaudit_usage_rollup"] = result.get("reaudit_usage_rollup")
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_story_reaudit_cycle2_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_STORY_REAUDIT_CYCLE2_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_STORY_REAUDIT_CYCLE2_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
