"""Q8 repeatability qualification across unrelated story fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_q5t import save
from src.spineforge_relay_v1_runner import execute_story, prepare as prepare_story

FIXTURES = [
    Path("tests/fixtures/spineforge_relay_v1/q8_greenhouse_notebook.json"),
    Path("tests/fixtures/spineforge_relay_v1/q8_hill_kite.json"),
]
ABORT_EVIDENCE = Path("evidence/spineforge-relay/SFR-V1-Q8A-INFRA-ABORT-20261007/result.json")
RUNTIME_FILES = [
    Path("src/spineforge_relay_v1_runner.py"),
    Path("src/spineforge_relay_v1_q6d.py"),
    Path("prompts/spineforge_relay_v1_q6d_writer.md"),
    Path("prompts/spineforge_relay_v1_q6d_guard.md"),
]
DEFAULT_OUTPUT = Path("evidence/spineforge-relay/SFR-V1-Q8B-REPEATABILITY-20261007")
MAX_TOTAL_COST_USD = 1.00


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare() -> dict[str, Any]:
    stories = [prepare_story(path) for path in FIXTURES]
    return {
        "schema": "spineforge-relay.q8b-preflight.v1",
        "qualification_id": "SFR-V1-Q8B-REPEATABILITY-20261007",
        "parent_q8a_abort_sha256": _sha(ABORT_EVIDENCE),
        "runtime_files": [{"path": p.as_posix(), "sha256": _sha(p)} for p in RUNTIME_FILES],
        "story_count": len(stories),
        "stories": stories,
        "same_runner": "src/spineforge_relay_v1_runner.py",
        "same_writer": "openai/gpt-5.6-sol",
        "same_guard": "anthropic/claude-sonnet-5.5",
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_suite_on_story_failure": True,
        "production_write": False,
        "max_total_cost_usd": MAX_TOTAL_COST_USD,
    }


def authorization_for(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "spineforge-relay.q8b-authorization.v1",
        "preflight_sha256": canonical_sha256(preflight),
        "paid_execution_authorized": True,
        "story_ids": [x["story_id"] for x in preflight["stories"]],
        "max_rewrites_per_scene": 1,
        "automatic_retry": False,
        "stop_suite_on_story_failure": True,
        "production_write": False,
        "max_total_cost_usd": MAX_TOTAL_COST_USD,
        "user_instruction": (
            "2026-10-07: fresh SFR-v1 Q8B repeatability after Q8A infrastructure abort; "
            "using the same generic runner, writer and guard; max one rewrite per scene; "
            "no automatic retry; stop suite on story failure"
        ),
    }


def execute_suite(
    *,
    api_key: str,
    preflight: dict[str, Any],
    authorization: dict[str, Any],
    output: Path = DEFAULT_OUTPUT,
    call_fn=None,
) -> dict[str, Any]:
    if preflight != prepare():
        raise RuntimeError("Q8B frozen preflight drift")
    if authorization != authorization_for(preflight):
        raise RuntimeError("Q8B authorization mismatch")
    if not api_key:
        raise RuntimeError("Missing credential")

    output.mkdir(parents=True, exist_ok=False)
    with (output / "authorization-claimed.json").open("x", encoding="utf-8") as handle:
        json.dump(
            {"status": "CLAIMED_BEFORE_INFERENCE", **authorization},
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
    save(output / "preflight.json", preflight)
    save(output / "authorization.json", authorization)

    results = []
    known_cost = 0.0
    suite = {
        "status": "REJECT_REPEATABILITY",
        "reason": "UNFINISHED",
        "stories": results,
        "automatic_retry": False,
        "known_cost_usd": 0.0,
    }

    for fixture_path, story_preflight in zip(FIXTURES, preflight["stories"], strict=True):
        story_id = story_preflight["story_id"]
        result = execute_story(
            fixture_path=fixture_path,
            api_key=api_key,
            preflight=story_preflight,
            output=output / story_id,
            call_fn=call_fn,
        )
        results.append(result)
        known_cost += float(result.get("known_cost_usd") or 0.0)
        if known_cost > MAX_TOTAL_COST_USD:
            raise RuntimeError("Q8B total provider cost exceeds authorization")
        suite["known_cost_usd"] = round(known_cost, 8)
        if result["status"] != "ACCEPT":
            suite["reason"] = "STORY_FAILED:" + story_id
            save(output / "result.json", suite)
            return suite

    suite["status"] = "ACCEPT"
    suite["reason"] = "TWO_UNRELATED_STORIES_ACCEPTED_WITH_SAME_RUNNER"
    suite["known_cost_usd"] = round(known_cost, 8)
    save(output / "result.json", suite)
    return suite
