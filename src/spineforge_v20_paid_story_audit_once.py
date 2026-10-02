from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_story_audit_once import execute_story_audit_once


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
WRITER_MANIFEST_PATH = Path(
    "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
)
WRITER_HANDOFF_PATH = Path(
    "evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json"
)
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-STORY-AUDIT4"
LEGACY_CI_TRIGGER_MARKER = "PAID-V20-AGE12-ISLAND-WRITER2"


def build_story_audit_failure_result(exc: Exception) -> dict[str, Any]:
    provider_trace = getattr(exc, "trace", None)
    return {
        "schema": "spineforge-v20-story-audit-execution.v1",
        "status": "unhandled_story_audit_runtime_failure",
        "stage": 5,
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


def execute_paid_story_audit_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    run_fn: Callable[..., dict[str, Any]] = execute_story_audit_once,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(PROFILE_PATH)
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    stage5 = profile.get("stage5_story_audit") or {}
    if stage5.get("paid_execution_authorized") is not True:
        raise RuntimeError("Stage 5 paid Story Audit is not authorized in frozen runtime.")
    if stage5.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("Stage 5 paid Story Audit authorization marker mismatch.")
    if int(stage5.get("audit_calls_per_execution") or 0) != 2:
        raise RuntimeError("Stage 5 paid Story Audit must be pinned to exactly two audit calls.")
    if stage5.get("automatic_retry_enabled") is not False:
        raise RuntimeError("Stage 5 paid Story Audit automatic retry must remain disabled.")

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-story-audit4-result.json"
    envelope_path = out_dir / "age12-island-v20-story-audit4-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-story-audit-envelope.v1",
        "stage": 5,
        "attempt_index": 4,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "legacy_ci_trigger_marker": LEGACY_CI_TRIGGER_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "source_writer_manifest_path": str(WRITER_MANIFEST_PATH),
        "source_writer_handoff_path": str(WRITER_HANDOFF_PATH),
        "result_status": "started",
        "automatic_retry_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "audit_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(
            api_key=api_key,
            writer_manifest_path=WRITER_MANIFEST_PATH,
            writer_handoff_path=WRITER_HANDOFF_PATH,
        )
    except Exception as exc:
        result = build_story_audit_failure_result(exc)

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    envelope["result_status"] = result.get("status")
    envelope["audit_usage_rollup"] = result.get("audit_usage_rollup")
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_story_audit_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_STORY_AUDIT_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_STORY_AUDIT_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
