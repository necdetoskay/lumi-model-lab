from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

from src.generate import parse_cost
from src.model_registry import runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.spineforge_v19_transport import call_strict_json_once
from src.spineforge_v20_story_local_repair_once import (
    REPAIR_MODEL,
    REPAIR_REQUEST_CLASS,
    REPAIR_RESPONSE_SCHEMA,
    _apply_patches,
    _normalize_repair_payload,
)


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
DEFAULT_HANDOFF_PATH = Path(
    "evidence/spineforge-v20-story-local-repair-cycle2/37007924152-handoff.json"
)
REPAIR_SCHEMA_NAME = "spineforge_v20_story_local_repair_cycle2_v1"
REPAIR_PROMPT = Path("prompts/spineforge_v20_story_local_repair_cycle2.md")


JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_story(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text[:-1] if text.endswith("\n") else text


def load_frozen_story_local_repair_cycle2_handoff(
    *,
    handoff_path: Path = DEFAULT_HANDOFF_PATH,
    profile_path: Path = PROFILE_PATH,
) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    stage8 = profile.get("stage8_story_local_repair") or {}
    expected_path = Path(str(stage8.get("handoff_path") or ""))
    if expected_path != handoff_path:
        raise RuntimeError("Stage 8 handoff path does not match frozen profile.")
    if not handoff_path.is_file():
        raise RuntimeError("Frozen Stage 8 handoff artifact is missing.")
    actual_sha = _sha256_file(handoff_path)
    expected_sha = str(stage8.get("handoff_sha256") or "")
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Frozen Stage 8 handoff SHA mismatch: {actual_sha} != {expected_sha}"
        )
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != stage8.get("handoff_artifact_id"):
        raise RuntimeError("Frozen Stage 8 handoff artifact id mismatch.")
    if handoff.get("source_stage7_product_artifact_id") != stage8.get(
        "source_stage7_product_artifact_id"
    ):
        raise RuntimeError("Frozen Stage 8 source Stage 7 lineage mismatch.")
    if handoff.get("source_story_sha256") != stage8.get("source_story_sha256"):
        raise RuntimeError("Frozen Stage 8 source story lineage mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Frozen Stage 8 handoff status mismatch.")
    if handoff.get("immutable") is not True:
        raise RuntimeError("Frozen Stage 8 handoff must be immutable.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Frozen Stage 8 handoff must not authorize paid inference.")
    return handoff


def execute_story_local_repair_cycle2_once(
    *,
    api_key: str,
    handoff: dict[str, Any] | None = None,
    call_fn: JsonCall | None = None,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    if handoff is None:
        handoff = load_frozen_story_local_repair_cycle2_handoff()

    if handoff.get("schema") != "spineforge-v20-story-local-repair-cycle2-handoff.v1":
        raise RuntimeError("Stage 8 Story Local Repair handoff schema mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Stage 8 Story Local Repair handoff status mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Stage 8 immutable handoff must remain non-authorizing.")
    if int(handoff.get("repair_cycle_index") or 0) != 2:
        raise RuntimeError("Stage 8 repair cycle index must be 2.")
    if int(handoff.get("paid_attempt_index") or 0) != 3:
        raise RuntimeError("Stage 8 paid attempt index must be 3.")

    source_story_path = Path(str(handoff["source_story_path"]))
    source_story = _canonical_story(source_story_path)
    if _sha256_text(source_story) != handoff.get("source_story_sha256"):
        raise RuntimeError("Stage 8 source story SHA mismatch.")
    if _sha256_file(source_story_path) != handoff.get("source_story_file_sha256"):
        raise RuntimeError("Stage 8 source story file SHA mismatch.")

    payload = {
        "task": "repair_stage7_reaudit_findings_locally",
        "source_stage7_product_artifact_id": handoff[
            "source_stage7_product_artifact_id"
        ],
        "source_story_sha256": handoff["source_story_sha256"],
        "findings": handoff["findings"],
        "allowed_edit_span_ids": handoff["allowed_edit_span_ids"],
        "target_segments": handoff["target_segments"],
        "repair_policy": handoff["repair_policy"],
    }

    fn = call_fn or call_strict_json_once
    prompt = system_prompt or REPAIR_PROMPT.read_text(encoding="utf-8").strip()
    started = time.perf_counter()
    raw, body, request, failures = fn(
        api_key=api_key,
        model=REPAIR_MODEL,
        system_prompt=prompt,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=8000,
        seed=None,
        request_class=REPAIR_REQUEST_CLASS,
        schema_name=REPAIR_SCHEMA_NAME,
        schema=REPAIR_RESPONSE_SCHEMA,
    )
    latency = round(time.perf_counter() - started, 3)

    model_call = normalize_model_call(
        stage="spineforge_v20_story_local_repair_cycle2",
        model=REPAIR_MODEL,
        provider=runtime_profile_identity(REPAIR_MODEL).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    usage = rollup_model_calls([model_call])

    try:
        normalized = _normalize_repair_payload(raw=raw, handoff=handoff)
    except Exception as exc:
        setattr(exc, "trace", {
            "phase": "post_provider_repair_payload_validation",
            "raw_response": raw,
            "request": {
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "response_format": request.get("response_format"),
            },
            "transport_failures": failures,
            "repair_usage_rollup": usage,
            "incremental_cost_usd": usage["totals"]["cost_usd"],
            "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        })
        raise

    repaired_story, changed_ids = _apply_patches(
        source_story=source_story,
        handoff=handoff,
        patches=normalized["patches"],
    )

    return {
        "schema": "spineforge-v20-story-local-repair-cycle2-execution.v1",
        "status": "repair_generated",
        "stage": 8,
        "source_stage7_product_artifact_id": handoff[
            "source_stage7_product_artifact_id"
        ],
        "source_stage7_reaudit_artifact_id": handoff[
            "source_stage7_reaudit_artifact_id"
        ],
        "source_stage6_artifact_id": handoff["source_stage6_artifact_id"],
        "source_story_sha256": handoff["source_story_sha256"],
        "repair_model": REPAIR_MODEL,
        "patches": normalized["patches"],
        "no_change_resolutions": normalized["no_change_resolutions"],
        "changed_span_ids": changed_ids,
        "patch_count": len(normalized["patches"]),
        "no_change_resolution_count": len(normalized["no_change_resolutions"]),
        "repaired_story": repaired_story,
        "repaired_story_sha256": _sha256_text(repaired_story),
        "source_story_mutated": False,
        "all_findings_addressed": True,
        "all_findings_changed": not bool(normalized["no_change_resolutions"]),
        "reaudit_required_for_no_change_resolutions": bool(
            normalized["no_change_resolutions"]
        ),
        "changed_spans_subset_of_allowed": set(changed_ids).issubset(
            set(handoff["allowed_edit_span_ids"])
        ),
        "repair_usage_rollup": usage,
        "incremental_cost_usd": usage["totals"]["cost_usd"],
        "incremental_latency_seconds": usage["totals"]["latency_seconds"],
        "automatic_retry_executed": False,
        "reaudit_executed": False,
        "translation_executed": False,
        "state_commit_executed": False,
        "next_stage": "STORY_REAUDIT",
        "transport_failures": failures,
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "response_format": request.get("response_format"),
        },
    }
