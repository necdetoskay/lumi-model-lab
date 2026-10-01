from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_local_repair import run_local_repair
from src.spineforge_v20_obligations import load_qualification_cases


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
SOURCE_PATH = Path("evidence/spineforge-v20-repair/36908095596-source.json")
SPEC_PATH = Path("evidence/spineforge-v20-repair/36908095596-repair-spec.json")
AUTHORIZATION_MARKER = "PAID-V20-AGE12-ISLAND-REPAIR1"


def execute_paid_repair_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-repair"),
    run_fn: Callable[..., dict[str, Any]] = run_local_repair,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")

    freeze = verify_spineforge_runtime(PROFILE_PATH)
    source_artifact = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    source_spine = NarrativeSpineV1.model_validate(source_artifact["narrative_spine"])

    case = load_qualification_cases().cases[0]
    pack = SpineContextPackV1.model_validate_json(
        Path(case.context_fixture_ref).read_text(encoding="utf-8")
    )
    if pack.context_fingerprint != spec["source_context_fingerprint"]:
        raise RuntimeError("Repair ContextPack fingerprint mismatch.")
    if source_artifact["spine_hash"] != spec["source_spine_hash"]:
        raise RuntimeError("Repair source Spine hash mismatch.")
    if spec["source_gate_decision"] != "REPAIR":
        raise RuntimeError("Source gate decision is not REPAIR.")
    if spec["finding"]["repairability"] != "LOCAL":
        raise RuntimeError("Source finding is not LOCAL repairable.")

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "age12-island-v20-repair1-result.json"
    envelope_path = out_dir / "age12-island-v20-repair1-envelope.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-repair-envelope.v1",
        "source_run_id": spec["source_run_id"],
        "source_spine_hash": spec["source_spine_hash"],
        "attempt_index": 1,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "context_fingerprint": pack.context_fingerprint,
        "result_status": "started",
        "writer_authorized": False,
        "automatic_retry_executed": False,
        "automatic_repair_loop_executed": False,
        "result_path": str(result_path),
        "pipeline_usage_rollup": None,
    }
    envelope_path.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    try:
        result = run_fn(
            source_spine=source_spine,
            context_pack=pack,
            obligations=case.obligations,
            repair_spec=spec,
            api_key=api_key,
        )
    except Exception as exc:
        result = {
            "schema": "spineforge-v20-local-repair-evidence.v1",
            "status": "unhandled_repair_runtime_failure",
            "source_spine_hash": spec["source_spine_hash"],
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
    result, envelope = execute_paid_repair_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_REPAIR_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_REPAIR_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
