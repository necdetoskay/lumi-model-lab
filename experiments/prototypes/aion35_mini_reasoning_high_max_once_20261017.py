"""Aion 3.5 Mini high-vs-max single-use paid STORY WRITER comparison.

No human story edits, no editor/judge API calls, no max_tokens or reasoning
token cap, no automatic retry, and no world/production DB writes.
The exact historical Deniz balcony story spine + author instructions are
loaded from the pinned source file. Only reasoning.effort differs.
A completed reply is stored before any analysis; missing/unknown responses
are NEVER reposted, even after rerunning GitHub Actions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

MODEL = "aion-labs/aion-3.5-mini"
EFFORTS = ("high", "max")
BRANCH = "experiment/aion35-mini-reasoning-high-max-20261017"
GRANT_PATH = Path("experiments/triggers/aion35-reasoning-high-max-20261017.json")
OLD_SOURCE = Path("experiments/prototypes/aion35_mini_one_story_english_smoke_20260926.py")
OLD_BLOB = "04fb04bcb3ef5e4fad59f5576e7eb363fa11fcbc"
URL = "https://openrouter.ai/api/v1/chat/completions"
SCHEMA = "aion35-mini-high-max-original-deniz-one-use-v1"


def checked(flag: bool, why: str):
    if not flag:
        raise RuntimeError(why)


def digest(data):
    return sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".pending")
    checked(not tmp.exists(), "PENDING_RESULT_EXISTS_ABORT_NO_RETRY")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True,
                  allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def build_base_request():
    out = subprocess.run(["git", "hash-object", str(OLD_SOURCE)],
                         capture_output=True, text=True, check=True)
    checked(out.stdout.strip() == OLD_BLOB, "ORIGINAL_STORY_PROMPT_BLOB_DRIFT")
    from experiments.prototypes.aion35_mini_one_story_english_smoke_20260926 import (
        WRITER_MODEL, WRITER_SYSTEM, PREMISE, STORY_SPINE,
    )
    checked(WRITER_MODEL == MODEL and len(STORY_SPINE) == 8 and
            "Deniz" in PREMISE and "EXACTLY 4-year-old" in WRITER_SYSTEM,
            "FROZEN_OLD_DENIZ_PROMPT_NOT_REUSABLE")
    text = "\n".join(
        f"{i+1}. [{item['density']}] {item['beat']}"
        for i, item in enumerate(STORY_SPINE)
    )
    user_prompt = (
        f"PREMISE:\n{PREMISE}\n\nSTORY SPINE:\n{text}\n\n"
        "Turn this spine into a natural finished children's story."
    )
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": WRITER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.72,
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def make_request(effort):
    checked(effort in EFFORTS, "UNKNOWN_AION_REASONING_EFFORT")
    request = build_base_request()
    request["reasoning"] = {"effort": effort, "exclude": True}
    forbidden = {"max_tokens", "max_completion_tokens", "max_output_tokens",
                 "max_new_tokens", "reasoning_effort"}
    checked(not forbidden.intersection(request) and
            not forbidden.intersection(request["reasoning"]) and
            request["reasoning"]["effort"] == effort,
            "TOKEN_CEILING_OR_REASONING_POLICY_DRIFT")
    return request


def verify_equal_experiment():
    a = make_request("high")
    b = make_request("max")
    assert set(a) == set(b)
    assert {k: v for k, v in a.items() if k != "reasoning"} == {
        k: v for k, v in b.items() if k != "reasoning"
    }
    assert a["reasoning"]["exclude"] == b["reasoning"]["exclude"]
    assert a["reasoning"]["effort"] == "high"
    assert b["reasoning"]["effort"] == "max"
    return {
        "schema": SCHEMA,
        "model": MODEL,
        "source_blob": OLD_BLOB,
        "efforts": list(EFFORTS),
        "common_request_sha256": digest({
            k: v for k, v in a.items() if k != "reasoning"
        }),
        "high_request_sha256": digest(a),
        "max_request_sha256": digest(b),
        "user_output_token_ceiling_set": False,
        "single_use_max_attempts": 2,
        "no_editor_no_silent_repair": True,
    }


def _git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def validate_one_use_launch(grant):
    checked(isinstance(grant, dict) and
            set(grant) == {
                "schema", "launch_id", "base_commit", "model", "efforts",
                "max_provider_posts", "source_blob", "grant_policy",
            } and
            grant["schema"] == SCHEMA and
            grant["launch_id"] == "aion35mini-deniz-high-max-20261017-once" and
            grant["model"] == MODEL and
            grant["efforts"] == list(EFFORTS) and
            grant["max_provider_posts"] == 2 and
            grant["source_blob"] == OLD_BLOB and
            grant["grant_policy"] == "PAID_TWO_CALLS_HIGH_AND_MAX_EXPLICIT_USER_APPROVAL",
            "GRANT_SCOPE_UNAUTHORIZED")
    # A paid workflow can only be started by exactly one grant-only commit.
    checked(_git("rev-parse", "HEAD^") == grant["base_commit"],
            "CODE_PARENT_UNREVIEWED")
    changed = _git("diff", "--name-only", "HEAD^", "HEAD").splitlines()
    checked(changed == [str(GRANT_PATH)], "PAID_LAUNCH_CHANGED_CODE")
    checked(os.getenv("GITHUB_REF_NAME") == BRANCH,
            "PAID_LAUNCH_WRONG_BRANCH")
    checked(os.getenv("GITHUB_SHA") == _git("rev-parse", "HEAD"),
            "GITHUB_ACTIONS_SHA_NOT_CHECKOUT")
    return verify_equal_experiment()


def claim_one_use(grant, claim_root: Path):
    checked(claim_root.is_absolute(), "CLAIM_ROOT_MUST_BE_PERSISTENT_ABSOLUTE")
    claim_root.mkdir(parents=True, exist_ok=True)
    claim = claim_root / (grant["launch_id"] + ".claimed.json")
    data = {
        "schema": SCHEMA,
        "launch_id": grant["launch_id"],
        "grant_sha256": digest(grant),
        "actions_run_id": os.environ.get("GITHUB_RUN_ID"),
        "claimed_utc": datetime.now(timezone.utc).isoformat(),
        "maximum_posts": 2,
    }
    fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    # Persistent runner storage; no new human steps in story pipeline.
    return claim


def real_stream_call(request, api_key):
    """One POST; NO retry on 429/timeout/disconnect/unknown billing outcome."""
    import requests

    checked(request.get("model") == MODEL and
            request.get("reasoning", {}).get("effort") in EFFORTS and
            request.get("stream") is True and
            not any(k in request for k in (
                "max_tokens", "max_completion_tokens", "max_output_tokens")),
            "PAID_REQUEST_SCOPE_INVALID")
    stamp = time.monotonic()
    # Aion may stream many minutes; this is a per-idle-read timeout only.
    with requests.post(
        URL,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "LUMI Aion Mini Reasoning A/B",
        },
        json=request, stream=True, timeout=(25, 480),
    ) as resp:
        resp.raise_for_status()
        text = []
        finish_reason = None
        usage = None
        generation_id = None
        returned_model = None
        event_count = 0
        stream_closed_cleanly = False
        for line in resp.iter_lines(decode_unicode=False):
            if not line:
                continue
            if isinstance(line, bytes):
                # SSE JSON is UTF-8. requests' default decode_unicode=True
                # can incorrectly choose ISO-8859-1 for text/event-stream,
                # producing visible mojibake like "â\\x80\\x94".
                # Keep the original paid receipts immutable, fix decoder only.
                line = line.decode("utf-8", errors="strict")
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                stream_closed_cleanly = True
                break
            event_count += 1
            packet = json.loads(body)
            checked(not packet.get("error"), "PROVIDER_STREAM_ERROR")
            generation_id = generation_id or packet.get("id")
            returned_model = returned_model or packet.get("model")
            if packet.get("usage"):
                usage = packet["usage"]
            for choice in packet.get("choices") or []:
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if isinstance(content, str):
                    text.append(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and isinstance(
                                part.get("text"), str):
                            text.append(part["text"])
                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
    story = "".join(text)
    checked(generation_id and event_count > 0,
            "NO_PROVIDER_GENERATION_ID")
    checked(stream_closed_cleanly and finish_reason is not None,
            "PROVIDER_STREAM_TRUNCATED_OR_NO_DONE")
    return {
        "generation_id": generation_id,
        "returned_model": returned_model,
        "finish_reason": finish_reason,
        "story": story,
        "usage": usage,
        "event_count": event_count,
        "elapsed_seconds": round(time.monotonic()-stamp, 3),
    }


def summarize(effort, result, request):
    story = result["story"]
    usage = result.get("usage") or {}
    breakdown = usage.get("completion_tokens_details") or {}
    return {
        "effort": effort, "model": MODEL,
        "request_sha256": digest(request),
        "generation_id": result.get("generation_id"),
        "returned_model": result.get("returned_model"),
        "finish_reason": result.get("finish_reason"),
        "words": len(story.split()),
        "nonempty_story": bool(story.strip()),
        "within_requested_375_to_625_words": 375 <= len(story.split()) <= 625,
        "story_sha256": sha256(story.encode("utf-8")).hexdigest(),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": breakdown.get("reasoning_tokens"),
            "cost_usd_observed": usage.get("cost"),
        },
        "elapsed_seconds": result["elapsed_seconds"],
        "story_quality_semantically_judged": False,
        "original_story_manually_edited": False,
        "model_output_token_ceiling_set": False,
    }


def run_live(*,output_root,claim_root,api_key,grant):
    inputs = validate_one_use_launch(grant)
    checked(bool(api_key) and api_key.startswith("sk-"),
            "API_KEY_ABSENT_NO_PROVIDER_POST")
    # Commit claim BEFORE any network call; rerun would otherwise bill twice.
    claim_one_use(grant, claim_root)
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    atomic_json(out/"inputs.json", inputs)
    results = {}
    for effort in EFFORTS:
        request = make_request(effort)
        # A per-stage started marker is durable for this run. Any unknown
        # network outcome is terminal without resending.
        atomic_json(out/(effort+".started.json"), {
            "effort": effort, "request_sha256": digest(request),
            "model": MODEL, "possibly_billed": True,
        })
        try:
            provider = real_stream_call(request, api_key)
        except Exception as exc:
            atomic_json(out/(effort+".failure.json"), {
                "effort": effort, "failure_class": type(exc).__name__,
                "failure_reason": str(exc)[:600],
                "request_sha256": digest(request),
                "possibly_billed": True, "safe_no_retry": True,
            })
            break
        # Save raw complete result BEFORE validating/deciding PASS.
        atomic_json(out/(effort+".receipt.json"), provider)
        (out/(effort+".txt")).write_text(
            provider["story"] + "\n", encoding="utf-8"
        )
        results[effort] = summarize(effort,provider,request)
        atomic_json(out/(effort+".summary.json"),results[effort])
        # A missing or length-truncated response is not a valid story
        # comparison, but is still preserved as real historical evidence.
        if (
            provider.get("finish_reason") != "stop" or
            not provider.get("story", "").strip() or
            not provider.get("generation_id") or
            provider.get("returned_model") != MODEL
        ):
            break
    pair_complete = (
        len(results) == 2 and
        all(
            row["finish_reason"] == "stop" and
            row["nonempty_story"] and
            row["returned_model"] == MODEL and
            row["generation_id"]
            for row in results.values()
        ) and
        len({row["generation_id"] for row in results.values()}) == 2
    )
    comparison = {
        "schema": SCHEMA,
        "status": ("TWO_GENUINE_PROVIDER_ANSWERS_COMPARABLE"
                   if pair_complete else
                   "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND"),
        "both_provider_generations_distinct_and_complete": pair_complete,
        "source_input": inputs,
        "completed_real_provider_replies": len(results),
        "real_paid_post_ceiling": 2,
        "real_paid_posts_started": len(list(out.glob("*.started.json"))),
        "results": results,
        "semantic_quality_winner_unverified": True,
        "model_output_token_limit_set": False,
        "manual_story_repairs": 0,
        "editor_or_judge_provider_calls": 0,
        "canonical_world_writes": 0,
        "production_db_writes": 0,
        "requires_manual_story_repair": False,
    }
    atomic_json(out/"result.json", comparison)
    print(json.dumps(comparison, ensure_ascii=False, sort_keys=True),
          flush=True)
    return comparison


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--live",action="store_true")
    p.add_argument("--grant-file",type=Path,default=GRANT_PATH)
    p.add_argument("--output-root",type=Path,default=Path("runs/aion-high-max-once"))
    p.add_argument("--claim-root",type=Path)
    a=p.parse_args()
    checked(a.live != a.dry_run, "CHOOSE_EXACTLY_ONE_MODE")
    if a.dry_run:
        print(json.dumps(verify_equal_experiment(),sort_keys=True))
        return
    checked(a.claim_root is not None, "PERSISTENT_CLAIM_ROOT_REQUIRED")
    grant=json.loads(a.grant_file.read_text(encoding="utf-8"))
    run_live(output_root=a.output_root,claim_root=a.claim_root,
             api_key=os.environ.get("OPENROUTER_API_KEY",""),grant=grant)


if __name__=="__main__":
    main()
