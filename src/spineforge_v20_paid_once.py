from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20 import run
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
CASE_ID = "spineforge.v20.age12.adventure-exploration.island.01"
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-ATTEMPT1"


def execute_paid_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid"),
    run_fn: Callable[..., dict[str, Any]] = run,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(PROFILE_PATH)
    case_set = load_qualification_cases()
    case = next(row for row in case_set.cases if row.case_id == CASE_ID)
    if case.context_fixture_status != "FROZEN":
        raise RuntimeError("v20 paid case fixture is not frozen.")

    pack_path = Path(case.context_fixture_ref)
    pack = SpineContextPackV1.model_validate_json(
        pack_path.read_text(encoding="utf-8")
    )

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-attempt1-result.json"
    envelope_path = out_dir / "age12-island-v20-attempt1-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-attempt-envelope.v1",
        "case_id": CASE_ID,
        "attempt_index": 1,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "result_status": "started",
        "writer_authorized": False,
        "automatic_retry_executed": False,
        "automatic_repair_executed": False,
        "result_path": str(result_path),
        "pipeline_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(
            context_pack=pack,
            obligations=case.obligations,
            api_key=api_key,
        )
    except Exception as exc:
        result = {
            "schema": "spineforge-v20-evidence.v1",
            "status": "unhandled_runtime_failure",
            "context_pack_id": pack.context_pack_id,
            "context_fingerprint": pack.context_fingerprint,
            "writer_authorized": False,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }

    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    envelope["result_status"] = result.get("status")
    envelope["pipeline_usage_rollup"] = result.get("pipeline_usage_rollup")
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
