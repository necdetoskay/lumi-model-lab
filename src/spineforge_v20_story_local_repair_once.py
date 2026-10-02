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
from src.spineforge_v20_story_audit_artifact import (
    build_story_audit_source,
    load_verified_writer_story_artifact,
)
from src.spineforge_v20_story_local_repair_handoff import DEFAULT_WRITER_MANIFEST


REPAIR_MODEL = "anthropic/claude-sonnet-5.5"
REPAIR_REQUEST_CLASS = "spineforge_v20_story_local_repair"
REPAIR_SCHEMA_NAME = "spineforge_v20_story_local_repair_v1"
REPAIR_PROMPT = Path("prompts/spineforge_v20_story_local_repair.md")


PROFILE_PATH = Path(
    "data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json"
)
DEFAULT_HANDOFF_PATH = Path(
    "evidence/spineforge-v20-story-local-repair/36990160527-handoff.json"
)

REPAIR_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["patches", "summary"],
    "properties": {
        "patches": {
            "type": "array",
            "minItems": 1,
            "maxItems": 64,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "span_id",
                    "replacement_text",
                    "addresses_finding_indexes",
                ],
                "properties": {
                    "span_id": {"type": "string", "maxLength": 16},
                    "replacement_text": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 1800,
                    },
                    "addresses_finding_indexes": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 25,
                        "items": {"type": "integer", "minimum": 0, "maximum": 255},
                    },
                },
            },
        },
        "summary": {"type": "string", "maxLength": 600},
    },
}

JsonCall = Callable[
    ..., tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_story_local_repair_handoff(
    *,
    handoff_path: Path = DEFAULT_HANDOFF_PATH,
    profile_path: Path = PROFILE_PATH,
) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    stage6 = profile.get("stage6_story_local_repair") or {}
    expected_path = Path(str(stage6.get("handoff_path") or ""))
    if expected_path != handoff_path:
        raise RuntimeError("Stage 6 handoff path does not match frozen profile.")
    if not handoff_path.is_file():
        raise RuntimeError("Frozen Stage 6 handoff artifact is missing.")
    actual_sha = _sha256_file(handoff_path)
    expected_sha = str(stage6.get("handoff_sha256") or "")
    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Frozen Stage 6 handoff SHA mismatch: {actual_sha} != {expected_sha}"
        )
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    if handoff.get("artifact_id") != stage6.get("handoff_artifact_id"):
        raise RuntimeError("Frozen Stage 6 handoff artifact id mismatch.")
    if handoff.get("source_audit_artifact_id") != stage6.get(
        "source_stage5_artifact_id"
    ):
        raise RuntimeError("Frozen Stage 6 source audit lineage mismatch.")
    if handoff.get("source_story_sha256") != stage6.get("source_story_sha256"):
        raise RuntimeError("Frozen Stage 6 source story lineage mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Frozen Stage 6 handoff status mismatch.")
    if handoff.get("immutable") is not True:
        raise RuntimeError("Frozen Stage 6 handoff must be immutable.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Frozen Stage 6 handoff must not contain paid authorization.")
    return handoff


def _normalize_repair_payload(
    *,
    raw: dict[str, Any],
    handoff: dict[str, Any],
) -> dict[str, Any]:
    patches_raw = raw.get("patches")
    if not isinstance(patches_raw, list) or not patches_raw:
        raise RuntimeError("Story Local Repair patches must be a non-empty list.")

    allowed = set(str(x) for x in handoff["allowed_edit_span_ids"])
    target_by_id = {
        str(row["span_id"]): row
        for row in handoff["target_segments"]
    }
    finding_indexes = set(range(int(handoff["finding_count"])))

    patches: list[dict[str, Any]] = []
    no_change_resolutions: list[dict[str, Any]] = []
    seen_spans: set[str] = set()
    addressed: set[int] = set()

    for row in patches_raw:
        if not isinstance(row, dict):
            raise RuntimeError("Story Local Repair patch must be an object.")
        span_id = str(row.get("span_id") or "")
        replacement = str(row.get("replacement_text") or "").strip()
        indexes = [int(x) for x in (row.get("addresses_finding_indexes") or [])]

        if span_id not in allowed:
            raise RuntimeError(f"Repair attempted forbidden span: {span_id}")
        if span_id in seen_spans:
            raise RuntimeError(f"Duplicate repair patch span: {span_id}")
        if not replacement:
            raise RuntimeError(f"Repair replacement is empty: {span_id}")
        if not indexes:
            raise RuntimeError(f"Repair patch addresses no findings: {span_id}")
        if any(index not in finding_indexes for index in indexes):
            raise RuntimeError(f"Repair patch references unknown finding: {span_id}")

        legal_for_span = set(int(x) for x in target_by_id[span_id]["finding_indexes"])
        if any(index not in legal_for_span for index in indexes):
            raise RuntimeError(
                f"Repair patch claims finding not bound to span: {span_id}"
            )

        seen_spans.add(span_id)
        addressed.update(indexes)
        source_text = str(target_by_id[span_id]["source_text"]).strip()
        if replacement == source_text:
            no_change_resolutions.append({
                "span_id": span_id,
                "disposition": "NO_CHANGE",
                "source_text": source_text,
                "addresses_finding_indexes": sorted(set(indexes)),
                "reason": (
                    "Repair model returned the frozen source unchanged; "
                    "mandatory Story Re-audit must adjudicate this finding."
                ),
            })
            continue

        patches.append({
            "span_id": span_id,
            "replacement_text": replacement,
            "addresses_finding_indexes": sorted(set(indexes)),
        })

    if addressed != finding_indexes:
        missing = sorted(finding_indexes - addressed)
        raise RuntimeError(
            f"Story Local Repair did not address every finding: {missing}"
        )

    return {
        "patches": patches,
        "no_change_resolutions": no_change_resolutions,
        "summary": str(raw.get("summary") or "").strip(),
    }


def _apply_patches(
    *,
    source_story: str,
    handoff: dict[str, Any],
    patches: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    target_by_id = {
        str(row["span_id"]): row
        for row in handoff["target_segments"]
    }
    edits = []
    for patch in patches:
        span_id = str(patch["span_id"])
        target = target_by_id[span_id]
        start = int(target["char_start"])
        end = int(target["char_end"])
        source_text = str(target["source_text"])
        if source_story[start:end] != source_text:
            raise RuntimeError(
                f"Source story no longer matches repair span offsets: {span_id}"
            )
        edits.append(
            (start, end, span_id, str(patch["replacement_text"]))
        )

    repaired = source_story
    for start, end, span_id, replacement in sorted(
        edits, key=lambda row: row[0], reverse=True
    ):
        repaired = repaired[:start] + replacement + repaired[end:]

    changed_ids = [
        span_id
        for _, _, span_id, _ in sorted(edits, key=lambda row: row[0])
    ]
    return repaired, changed_ids


def execute_story_local_repair_once(
    *,
    api_key: str,
    handoff: dict[str, Any] | None = None,
    call_fn: JsonCall | None = None,
    system_prompt: str | None = None,
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    if handoff is None:
        handoff = load_frozen_story_local_repair_handoff()

    if handoff.get("schema") != "spineforge-v20-story-local-repair-handoff.v1":
        raise RuntimeError("Story Local Repair handoff schema mismatch.")
    if handoff.get("status") != "READY_NOT_AUTHORIZED":
        raise RuntimeError("Story Local Repair handoff status mismatch.")
    if handoff.get("paid_execution_authorized") is not False:
        raise RuntimeError("Zero-cost handoff must not pre-authorize paid repair.")

    verified_writer = load_verified_writer_story_artifact(
        manifest_path=DEFAULT_WRITER_MANIFEST,
        repo_root=repo_root,
    )
    if verified_writer["manifest"]["story_sha256"] != handoff["source_story_sha256"]:
        raise RuntimeError("Story Local Repair source story SHA mismatch.")
    source_story = verified_writer["story"]
    story_source = build_story_audit_source(
        manifest_path=DEFAULT_WRITER_MANIFEST,
        repo_root=repo_root,
    )

    payload = {
        "task": "repair_qualified_story_findings_locally",
        "source_writer_artifact_id": handoff["source_writer_artifact_id"],
        "source_story_sha256": handoff["source_story_sha256"],
        "source_audit_artifact_id": handoff["source_audit_artifact_id"],
        "findings": handoff["findings"],
        "allowed_edit_span_ids": handoff["allowed_edit_span_ids"],
        "story_segments": story_source["story_segments"],
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
        stage="spineforge_v20_story_local_repair",
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
        "schema": "spineforge-v20-story-local-repair-execution.v1",
        "status": "repair_generated",
        "source_writer_artifact_id": handoff["source_writer_artifact_id"],
        "source_story_sha256": handoff["source_story_sha256"],
        "source_audit_artifact_id": handoff["source_audit_artifact_id"],
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
