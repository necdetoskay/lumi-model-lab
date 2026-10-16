"""SERA v0.10: one opt-in paid, source-bound Mara sentence-sweep pilot.

Exactly ONE provider request after explicit --live plus key preflight. No
fallback, retry, alternate model, story generation, JEV or DB writes.
Before any paid call archive the frozen source, request digest and plan.
No application output-token ceiling is used. Incomplete/error responses
are diagnostic HOLD with provider-reported usage/cost if available.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
import os
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_typed_live_v05 import (
    entry_state, REGISTRY, MODEL, one_provider_call,
)
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.sentence_sweep_v010 import (
    create_plan, bind_batch, summarize_partial,
)

LEXICON = Path(__file__).resolve().parent / (
    "fixtures/object_candidate_lexicon_v0.1.json"
)
TARGET_QUOTE = "closed the case"


def prepare():
    fixture = json.loads(PATH.read_text(encoding="utf-8"))
    prose = fixture["prose"]
    if (fixture.get("source_prose_sha256") != EXPECTED_SHA
        or prose_hash(prose) != EXPECTED_SHA
        or fixture.get("production_commit_authorized") is not False):
        raise CoverageError("V010_FROZEN_SOURCE_MISMATCH")
    state = entry_state()
    registry = {k: v for k, v in REGISTRY.items()
                if k in state["entities"]}
    candidates = json.loads(LEXICON.read_text(encoding="utf-8"))["candidates"]
    plan = create_plan(
        prose=prose, scene_key=fixture["scene_id"],
        entry_revision=state["revision"], registry=registry,
        candidate_lexicon=candidates,
    )
    targets = {x["id"] for x in plan["source_sentences"]
               if TARGET_QUOTE in x["quote"]}
    batches = [b for b in plan["batches"]
               if any(sid in targets for sid in b["sentence_ids"])]
    if len(batches) != 1 or len(targets) != 1:
        raise CoverageError("V010_TARGET_SOURCE_UNRESOLVED")
    return {"prose": prose, "plan": plan, "batch": batches[0]}


def run(*, output: Path, launch_id: str, key: str) -> dict:
    if output.exists():
        raise CoverageError("V010_EVIDENCE_PATH_EXISTS")
    source = prepare()
    selected = source["batch"]
    result = {
        "schema": "sera.mara-s1-sweep-paid-pilot.v0.10",
        "launch_id": launch_id,
        "source_prose_sha256": EXPECTED_SHA,
        "model_requested": MODEL,
        "batch_id": selected["batch_id"],
        "target_sentence_ids": selected["sentence_ids"],
        "request_sha256": selected["request_sha256"],
        "response_format": selected["response_format"],
        "provider_attempts": 0,
        "provider_usage": None,
        "provider_reported_cost": None,
        "provider_response_id": None,
        "observed_model": None,
        "provider_raw_content": None,
        "raw_extraction": None,
        "bound_batch": None,
        "recovery_queue": None,
        "status": "PREFLIGHT_HOLD",
        "max_model_output_tokens_configured": False,
        "semantic_completeness_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }

    def save():
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".stage")
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                       encoding="utf-8")
        tmp.replace(output)

    save()
    try:
        if not key:
            raise CoverageError("V010_PROVIDER_KEY_MISSING")
        from src.openrouter_preflight import (
            fetch_key_status, enforce_key_access,
        )
        enforce_key_access(fetch_key_status(key), min_remaining=0.25)
        result["status"] = "ATTEMPTING_SINGLE_PROVIDER_CALL"
        result["provider_attempts"] = 1
        save()
        # v0.5 vetted adapter enforces no output token limit on outbound
        # payload and has no model-reasoning toggle.
        response = one_provider_call(
            key=key,
            prepared={"request": {
                "messages": selected["messages"],
                "response_format": selected["response_format"],
            }},
        )
        if response["error"]:
            result["status"] = "PROVIDER_ERROR_HOLD"
            result["error_code"] = response["error"]
            result["provider_detail"] = response.get("provider_detail")
            save()
            return result
        body = response["raw"]
        result["provider_response_id"] = body.get("id")
        result["observed_model"] = body.get("model")
        result["provider_usage"] = body.get("usage")
        if isinstance(body.get("usage"), dict):
            result["provider_reported_cost"] = body["usage"].get("cost")
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise CoverageError("V010_PROVIDER_CHOICES_INVALID")
        choice = choices[0]
        result["finish_reason"] = choice.get("finish_reason")
        content = (choice.get("message") or {}).get("content")
        result["provider_raw_content"] = content
        save()
        if result["finish_reason"] != "stop":
            raise CoverageError("V010_PROVIDER_INCOMPLETE")
        if not isinstance(content, str):
            raise CoverageError("V010_PROVIDER_CONTENT_INVALID")
        try:
            raw = json.loads(content)
        except ValueError:
            raise CoverageError("V010_PROVIDER_JSON_INVALID") from None
        result["raw_extraction"] = raw
        bound = bind_batch(
            plan=source["plan"], batch_id=selected["batch_id"],
            raw=raw, prose=source["prose"],
        )
        result["bound_batch"] = bound
        result["recovery_queue"] = summarize_partial(
            plan=source["plan"], bound_batches=[bound],
        )
        result["status"] = "ONE_BATCH_EXTRACTED_REMAINING_SOURCE_HOLD"
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INCOMPLETE_HOLD"
        result["error_code"] = str(exc)[:300]
    save()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--launch-id", default="dry-run")
    args = parser.parse_args()
    prepared = prepare()
    if not args.live:
        print(json.dumps({
            "mode": "DRY_RUN_NO_PROVIDER_CALL",
            "scene": prepared["plan"]["scene_key"],
            "source_sha256": EXPECTED_SHA,
            "model": MODEL,
            "batch_count": len(prepared["plan"]["batches"]),
            "pilot_batch_id": prepared["batch"]["batch_id"],
            "pilot_sentence_ids": prepared["batch"]["sentence_ids"],
            "request_sha256": prepared["batch"]["request_sha256"],
            "output_token_limit": "NOT_SET_BY_APPLICATION",
            "canonical_db_writes": 0,
        }, ensure_ascii=False, indent=2))
        return
    if args.output is None:
        parser.error("--live requires --output")
    result = run(
        output=args.output, launch_id=args.launch_id,
        key=os.getenv("OPENROUTER_API_KEY",""),
    )
    print(json.dumps({
        "status": result["status"],
        "provider_attempts": result["provider_attempts"],
        "provider_reported_cost": result["provider_reported_cost"],
        "error_code": result.get("error_code"),
        "batch_id": result["batch_id"],
        "extracted_event_candidates": len(
            [e for r in (result.get("bound_batch") or {}).get("rows", [])
             for e in r.get("events", [])]
        ),
        "canonical_commit_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
