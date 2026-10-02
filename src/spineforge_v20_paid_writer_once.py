from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_writer_once import execute_writer_once


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
HANDOFF_PATH = Path(
    "evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json"
)
PROMPT_PATH = Path("prompts/spineforge_v20_writer.md")
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-WRITER3"


def execute_paid_writer_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    run_fn: Callable[..., dict[str, Any]] = execute_writer_once,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(PROFILE_PATH)
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-writer3-result.json"
    story_path = out_dir / "age12-island-v20-writer3-story.txt"
    envelope_path = out_dir / "age12-island-v20-writer3-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-writer-envelope.v1",
        "attempt_index": 3,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "approval_id": handoff["approval_id"],
        "context_fingerprint": handoff["context_fingerprint"],
        "spine_hash": handoff["spine_hash"],
        "writer_model": handoff["writer_model"],
        "result_status": "started",
        "automatic_retry_executed": False,
        "editor_executed": False,
        "judge_executed": False,
        "repair_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "story_path": str(story_path),
        "writer_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(
            handoff=handoff,
            api_key=api_key,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        result = {
            "schema": "spineforge-v20-writer-evidence.v1",
            "status": "unhandled_writer_runtime_failure",
            "approval_id": handoff["approval_id"],
            "context_fingerprint": handoff["context_fingerprint"],
            "spine_hash": handoff["spine_hash"],
            "writer_model": handoff["writer_model"],
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
            "automatic_retry_executed": False,
            "editor_authorized": False,
            "judge_authorized": False,
            "repair_authorized": False,
            "translation_authorized": False,
            "state_commit_authorized": False,
        }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    story = result.get("story")
    if isinstance(story, str) and story.strip():
        story_path.write_text(story.rstrip() + "\n", encoding="utf-8")

    envelope["result_status"] = result.get("status")
    envelope["writer_usage_rollup"] = result.get("writer_usage_rollup")
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_writer_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_WRITER_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_WRITER_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
