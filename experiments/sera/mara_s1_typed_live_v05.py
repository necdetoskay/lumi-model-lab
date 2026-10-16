"""SERA v0.5 one-shot blind typed extraction of the FROZEN Mara S1 prose.

Opt-in: exactly one billable OpenRouter attempt; no retry, no fallback, no
writer regeneration, no JEV run, no story/database commits. Always archive
diagnostic data including failed provider/schema responses.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.typed_extractor_contract_v05 import (
    make_typed_request, bind_typed_response,
)
from experiments.sera.world_state_v02 import (
    entity_template, initial_state, environment_template,
)

MODEL = "google/gemini-3.7-flash"
MAX_TOKENS = 4096
MIN_PROVIDER_KEY_REMAINING = 0.25
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SCENE = "hook_empty_platform"
LOCATION = "north_quay_station"
REGISTRY = {
    "mara": ["Mara"],
    "vane": ["Vane", "Teodor Vane"],
    "vane_watch": ["watch", "pocket watch"],
    "platform_clock": ["platform clock"],
    "archive_telegram": ["telegram", "archive telegram"],
    "mara_notebook": ["notebook"],
    "train_41": ["train 41", "train"],
}


def entry_state():
    return initial_state(
        minute=135,
        entities={
            "mara": entity_template(
                "mara", "CHARACTER", LOCATION, last_action_minute=135,
                knowledge=["claim:archive_recorded_arrival_0210"],
            ),
            "vane": entity_template(
                "vane", "CHARACTER", LOCATION, last_action_minute=135,
                knowledge=["claim:vane_watch_stopped_0207"],
            ),
            "vane_watch": entity_template(
                "vane_watch", "OBJECT", LOCATION,
                owner="vane", holder="vane", functional="STOPPED",
            ),
            "platform_clock": entity_template(
                "platform_clock", "OBJECT", LOCATION,
            ),
            "archive_telegram": entity_template(
                "archive_telegram", "OBJECT", LOCATION,
                holder="mara", owner="mara",
            ),
            "mara_notebook": entity_template(
                "mara_notebook", "OBJECT", LOCATION,
                holder="mara", owner="mara",
            ),
        },
        regions={LOCATION: environment_template("UNKNOWN",
                                                last_change_minute=135)},
    )


def prepare_request() -> dict:
    fixture = json.loads(PATH.read_text(encoding="utf-8"))
    prose = fixture["prose"]
    if (fixture.get("source_prose_sha256") != EXPECTED_SHA
        or sha256(prose.encode("utf-8")).hexdigest() != EXPECTED_SHA
        or fixture.get("production_commit_authorized") is not False):
        raise CoverageError("V05_LIVE_SOURCE_NOT_FROZEN")
    entry = entry_state()
    request = make_typed_request(
        prose=prose, scene_key=SCENE, entry=entry, registry=REGISTRY,
    )
    return {"prose": prose, "entry": entry, "request": request}


def one_provider_call(*, key: str, prepared: dict) -> dict:
    if not key:
        raise CoverageError("V05_LIVE_KEY_MISSING")
    req = prepared["request"]
    payload = {
        "model": MODEL, "messages": req["messages"],
        "response_format": req["response_format"],
        "temperature": 0, "max_tokens": MAX_TOKENS,
        # Prior Gemini response consumed 4082 completion tokens and was
        # truncated. Disable optional reasoning for this *bounded* retry.
        "reasoning": {"enabled": False},
        "stream": False,
    }
    http = Request(
        ENDPOINT, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "SERA M3.5 Frozen Mara S1 Typed Extraction",
        },
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    try:
        with urlopen(http, timeout=180) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(600).decode("utf-8", errors="replace")
        return {"error": f"HTTP_{exc.code}", "provider_detail": detail,
                "raw": None}
    except URLError:
        return {"error": "TRANSPORT_UNAVAILABLE", "raw": None}
    return {"raw": raw, "error": None}


def run(*, output: Path, launch_id: str, key: str) -> dict:
    if output.exists():
        raise CoverageError("V05_EVIDENCE_PATH_EXISTS")
    prepared = prepare_request()
    request = prepared["request"]
    result = {
        "protocol": "sera.mara-s1-typed-live.v0.5",
        "launch_id": launch_id, "source_prose_sha256": EXPECTED_SHA,
        "model_requested": MODEL,
        "request_sha256": request["request_sha256"],
        "provider_attempts": 0,
        "max_attempts": 1,
        "provider_usage": None,
        "provider_reported_cost": None,
        "response_id": None,
        "observed_model": None,
        "raw_content": None,
        "bound_extraction": None,
        "status": "STARTED",
        "model_quality_not_qualified": True,
        "commit_authorized": False,
        "production_db_writes": 0,
    }
    def checkpoint():
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".stage")
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        temp.replace(output)
    checkpoint()
    try:
        from src.openrouter_preflight import (
            fetch_key_status, enforce_key_access,
        )
        enforce_key_access(
            fetch_key_status(key),
            min_remaining=MIN_PROVIDER_KEY_REMAINING,
        )
        result["provider_attempts"] = 1
        checkpoint()
        response = one_provider_call(key=key, prepared=prepared)
        if response["error"]:
            result["status"] = "PROVIDER_ERROR_HOLD"
            result["error_code"] = response["error"]
            result["provider_detail"] = response.get("provider_detail")
            checkpoint()
            return result
        body = response["raw"]
        if not isinstance(body, dict):
            raise CoverageError("V05_PROVIDER_BODY_INVALID")
        result["response_id"] = body.get("id")
        result["observed_model"] = body.get("model")
        usage = body.get("usage")
        result["provider_usage"] = usage
        if isinstance(usage, dict):
            result["provider_reported_cost"] = usage.get("cost")
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise CoverageError("V05_PROVIDER_CHOICES_INVALID")
        choice = choices[0]
        content = (choice.get("message") or {}).get("content")
        result["raw_content"] = content
        result["finish_reason"] = choice.get("finish_reason")
        checkpoint()
        if result["finish_reason"] != "stop":
            raise CoverageError("V05_PROVIDER_INCOMPLETE")
        if not isinstance(content, str):
            raise CoverageError("V05_PROVIDER_CONTENT_INVALID")
        try:
            parsed = json.loads(content)
        except ValueError:
            raise CoverageError("V05_PROVIDER_JSON_INVALID") from None
        report = bind_typed_response(
            raw=parsed, request=request, prose=prepared["prose"],
            scene_key=SCENE, entry=prepared["entry"],
        )
        result["bound_extraction"] = report
        result["status"] = "EXTRACTED_DIAGNOSTIC_HOLD"
        result["new_entity_refs"] = sorted({
            mention["entity_ref"] for mention in report["report"]["mentions"]
            if mention["entity_ref"].startswith("new:")
        })
        result["event_count"] = len(report["normalized_events"])
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INCOMPLETE_HOLD"
        result["error_code"] = str(exc)[:300]
    checkpoint()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--launch-id", default="dry-run")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    prepared = prepare_request()
    if not args.live:
        print(json.dumps({
            "mode": "DRY_RUN_NO_MODEL_CALL",
            "scene": SCENE,
            "source_prose_sha256": EXPECTED_SHA,
            "request_sha256": prepared["request"]["request_sha256"],
            "model": MODEL,
            "max_attempts": 1,
            "schema_type": "json_schema",
            "production_db_writes": 0,
        }, ensure_ascii=False, indent=2))
        return
    if args.output is None:
        parser.error("--live requires --output")
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise CoverageError("V05_LIVE_KEY_MISSING")
    result = run(output=args.output, launch_id=args.launch_id, key=key)
    print(json.dumps({
        "status": result["status"],
        "provider_attempts": result["provider_attempts"],
        "provider_reported_cost": result["provider_reported_cost"],
        "error_code": result.get("error_code"),
        "new_entity_refs": result.get("new_entity_refs"),
        "event_count": result.get("event_count"),
        "production_db_writes": 0,
        "commit_authorized": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
