from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

from src.model_usage_rollup import rollup_model_calls
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v20_story_quality_loop import (
    build_local_repair_handoff,
    build_reaudit_handoff,
    build_reaudit_product,
    build_repair_product,
    execute_local_repair,
    execute_reaudit,
    write_json,
)


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
AUTHORIZATION_MARKER = "PAID-V20-STORY-QUALITY-LOOP"
LEGACY_CI_TRIGGER_MARKER = "PAID-V20-AGE12-ISLAND-WRITER2"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_loop_state(profile: dict[str, Any]) -> dict[str, Any]:
    loop = profile.get("story_quality_loop") or {}
    if loop.get("loop_revision") != "story-quality-loop-v1":
        raise RuntimeError("Story Quality Loop revision mismatch.")
    if loop.get("paid_execution_authorized") is not True:
        raise RuntimeError("Story Quality Loop paid execution is not authorized.")
    if loop.get("authorization_consumed") is not False:
        raise RuntimeError("Story Quality Loop authorization is already consumed.")
    if not str(loop.get("action_authorization_id") or "").strip():
        raise RuntimeError("Story Quality Loop action authorization id is required.")
    if loop.get("authorization_marker") != AUTHORIZATION_MARKER:
        raise RuntimeError("Story Quality Loop authorization marker mismatch.")
    if loop.get("automatic_retry_enabled") is not False:
        raise RuntimeError("Story Quality Loop automatic retry must remain disabled.")
    if loop.get("automatic_paid_transition_enabled") is not False:
        raise RuntimeError("Story Quality Loop automatic paid transition must remain disabled.")
    if loop.get("automatic_repair_loop_enabled") is not False:
        raise RuntimeError("Story Quality Loop automatic repair loop must remain disabled.")
    action = str(loop.get("current_action") or "")
    if action not in {"LOCAL_REPAIR", "REAUDIT"}:
        raise RuntimeError("Story Quality Loop current action is invalid.")
    handoff_path = Path(str(loop.get("handoff_path") or ""))
    if not handoff_path.is_file():
        raise RuntimeError("Story Quality Loop frozen handoff is missing.")
    if _sha256_file(handoff_path) != loop.get("handoff_sha256"):
        raise RuntimeError("Story Quality Loop frozen handoff SHA mismatch.")
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != loop.get("handoff_artifact_id"):
        raise RuntimeError("Story Quality Loop frozen handoff artifact mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Immutable loop handoff must remain non-authorizing.")
    return loop


def execute_paid_story_quality_loop_once(
    *,
    api_key: str,
    run_id: str,
    output_root: Path = Path("evidence/spineforge-v20-paid-writer"),
    profile_path: Path = PROFILE_PATH,
    repair_run_fn: Callable[..., dict[str, Any]] = execute_local_repair,
    reaudit_run_fn: Callable[..., dict[str, Any]] = execute_reaudit,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required.")
    freeze = verify_spineforge_runtime(profile_path)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    loop = _validate_loop_state(profile)
    action = loop["current_action"]
    stage = int(loop["current_stage"])
    cycle = int(loop["cycle_index"])
    handoff_path = Path(loop["handoff_path"])
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = (
        f"age12-island-v20-story-quality-repair-c{cycle}"
        if action == "LOCAL_REPAIR"
        else f"age12-island-v20-story-quality-reaudit-c{cycle}"
    )
    result_path = out_dir / f"{stem}-result.json"
    envelope_path = out_dir / f"{stem}-envelope.json"
    story_path = out_dir / f"{stem}-story.txt"
    product_path = out_dir / f"{stem}-product.json"
    next_handoff_path = out_dir / f"{stem}-next-handoff.json"
    next_state_path = out_dir / "story-quality-loop-next-state.json"

    envelope: dict[str, Any] = {
        "schema": "spineforge-v20-paid-story-quality-loop-envelope.v1",
        "stage": stage,
        "cycle_index": cycle,
        "action": action,
        "explicit_paid_authorization": True,
        "authorization_marker": AUTHORIZATION_MARKER,
        "action_authorization_id": loop.get("action_authorization_id"),
        "legacy_ci_trigger_marker": LEGACY_CI_TRIGGER_MARKER,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "handoff_artifact_id": handoff["artifact_id"],
        "result_status": "started",
        "automatic_retry_executed": False,
        "automatic_paid_transition_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "result_path": str(result_path),
        "product_path": str(product_path),
        "next_handoff_path": None,
        "next_state_path": str(next_state_path),
        "usage_rollup": None,
    }
    write_json(envelope_path, envelope)

    try:
        if action == "LOCAL_REPAIR":
            result = repair_run_fn(api_key=api_key, handoff=handoff)
        else:
            result = reaudit_run_fn(api_key=api_key, handoff=handoff)
    except Exception as exc:
        provider_trace = getattr(exc, "trace", None)
        partial_usage_rollup = None
        if isinstance(provider_trace, dict) and isinstance(
            provider_trace.get("model_call"), dict
        ):
            partial_usage_rollup = rollup_model_calls(
                [provider_trace["model_call"]]
            )
        result = {
            "schema": "spineforge-v20-story-quality-loop-failure.v1",
            "status": "unhandled_story_quality_loop_runtime_failure",
            "stage": stage,
            "cycle_index": cycle,
            "action": action,
            "failure": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "provider_trace": provider_trace if isinstance(provider_trace, dict) else None,
            },
            "partial_usage_rollup": partial_usage_rollup,
            "automatic_retry_executed": False,
            "automatic_paid_transition_executed": False,
            "translation_executed": False,
            "state_commit_executed": False,
        }
        write_json(result_path, result)
        envelope["result_status"] = result["status"]
        envelope["usage_rollup"] = partial_usage_rollup
        write_json(envelope_path, envelope)
        return result, envelope

    write_json(result_path, result)

    next_state: dict[str, Any]
    if action == "LOCAL_REPAIR":
        story = str(result.get("repaired_story") or "")
        if not story:
            raise RuntimeError("Story Quality Loop repair produced no repaired story.")
        story_path.write_text(story.rstrip() + "\n", encoding="utf-8")
        envelope["usage_rollup"] = result.get("repair_usage_rollup")
        envelope["result_status"] = result.get("status")
        write_json(envelope_path, envelope)
        product = build_repair_product(
            result_path=result_path,
            story_path=story_path,
            envelope_path=envelope_path,
            source_story_artifact_path=Path(loop["source_story_artifact_path"]),
            source_reaudit_product_path=Path(loop["source_reaudit_product_path"]),
        )
        write_json(product_path, product)
        next_handoff = build_reaudit_handoff(
            story_artifact_path=product_path,
            stage=stage + 1,
            cycle_index=cycle,
        )
        write_json(next_handoff_path, next_handoff)
        next_state = {
            "schema": "spineforge-v20-story-quality-loop-next-state.v1",
            "loop_revision": "story-quality-loop-v1",
            "status": "NEXT_ACTION_READY_NOT_AUTHORIZED",
            "current_action": "REAUDIT",
            "current_stage": stage + 1,
            "cycle_index": cycle,
            "source_story_artifact_id": product["artifact_id"],
            "source_story_artifact_path": str(product_path),
            "source_story_artifact_sha256": _sha256_file(product_path),
            "handoff_artifact_id": next_handoff["artifact_id"],
            "handoff_path": str(next_handoff_path),
            "handoff_sha256": _sha256_file(next_handoff_path),
            "paid_execution_authorized": False,
            "automatic_paid_transition_enabled": False,
        }
    else:
        envelope["usage_rollup"] = result.get("reaudit_usage_rollup")
        envelope["result_status"] = result.get("status")
        write_json(envelope_path, envelope)
        product = build_reaudit_product(
            result_path=result_path,
            envelope_path=envelope_path,
            source_story_artifact_path=Path(loop["source_story_artifact_path"]),
            stage=stage,
            cycle_index=cycle,
        )
        write_json(product_path, product)
        decision = product["decision"]
        if decision == "LOCAL_REPAIR_REQUIRED":
            next_handoff = build_local_repair_handoff(
                reaudit_product_path=product_path,
                source_story_artifact_path=Path(loop["source_story_artifact_path"]),
                stage=stage + 1,
                repair_cycle_index=cycle + 1,
                paid_attempt_index=max(
                    int(loop.get("next_repair_paid_attempt_index") or 0),
                    int((loop.get("last_completed_action") or {}).get("paid_attempt_index") or 0) + 1,
                    cycle + 2,
                ),
            )
            write_json(next_handoff_path, next_handoff)
            next_state = {
                "schema": "spineforge-v20-story-quality-loop-next-state.v1",
                "loop_revision": "story-quality-loop-v1",
                "status": "NEXT_ACTION_READY_NOT_AUTHORIZED",
                "current_action": "LOCAL_REPAIR",
                "current_stage": stage + 1,
                "cycle_index": cycle + 1,
                "source_story_artifact_id": loop["source_story_artifact_id"],
                "source_story_artifact_path": loop["source_story_artifact_path"],
                "source_story_artifact_sha256": loop["source_story_artifact_sha256"],
                "source_reaudit_product_artifact_id": product["artifact_id"],
                "source_reaudit_product_path": str(product_path),
                "source_reaudit_product_sha256": _sha256_file(product_path),
                "handoff_artifact_id": next_handoff["artifact_id"],
                "handoff_path": str(next_handoff_path),
                "handoff_sha256": _sha256_file(next_handoff_path),
                "paid_execution_authorized": False,
                "automatic_paid_transition_enabled": False,
            }
        elif decision == "ACCEPT":
            next_state = {
                "schema": "spineforge-v20-story-quality-loop-next-state.v1",
                "loop_revision": "story-quality-loop-v1",
                "status": "QUALITY_LOOP_ACCEPTED",
                "current_action": "ENGLISH_MASTER_SEAL",
                "current_stage": stage + 1,
                "cycle_index": cycle,
                "source_story_artifact_id": loop["source_story_artifact_id"],
                "source_story_artifact_path": loop["source_story_artifact_path"],
                "source_reaudit_product_artifact_id": product["artifact_id"],
                "source_reaudit_product_path": str(product_path),
                "paid_execution_authorized": False,
                "automatic_paid_transition_enabled": False,
            }
        else:
            next_state = {
                "schema": "spineforge-v20-story-quality-loop-next-state.v1",
                "loop_revision": "story-quality-loop-v1",
                "status": "QUALITY_LOOP_STOP",
                "current_action": "STOP",
                "current_stage": stage,
                "cycle_index": cycle,
                "decision": decision,
                "source_reaudit_product_artifact_id": product["artifact_id"],
                "source_reaudit_product_path": str(product_path),
                "paid_execution_authorized": False,
                "automatic_paid_transition_enabled": False,
            }

    write_json(next_state_path, next_state)
    envelope["result_status"] = result.get("status")
    envelope["product_artifact_id"] = product["artifact_id"]
    envelope["next_handoff_path"] = (
        str(next_handoff_path) if next_handoff_path.exists() else None
    )
    envelope["next_state"] = next_state
    write_json(envelope_path, envelope)
    return result, envelope


def main() -> None:
    result, envelope = execute_paid_story_quality_loop_once(
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        run_id=os.environ.get("GITHUB_RUN_ID", "local"),
    )
    print("===SPINEFORGE_V20_PAID_STORY_QUALITY_LOOP_ENVELOPE===")
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    print("===SPINEFORGE_V20_PAID_STORY_QUALITY_LOOP_RESULT===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
