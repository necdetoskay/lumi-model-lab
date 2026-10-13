"""P4.17 real-provider capable bounded state/topic → SpineForge → Writer pilot.

Never treats model prose as accepted English Master/Q25/State. Exactly two
one-shot POST attempts at most, no retry. Persistent O_EXCL claim occurs BEFORE
provider POST; an ambiguous response consumes the entire run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import (
    compile_case, build_spine_request, approve_spine_for_writer,
    build_writer_request, sha,
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-5.5"
PROVIDER = "Anthropic"
SCHEMA = "lumi.story-harness-p417-real-provider-pilot.v1"
USD_CAP = Decimal("0.35")
GLOBAL_USER_CAP = Decimal("10")
OUTPUT_CAPS = {"SPINEFORGE": 1800, "WRITER": 2500}
STAGE_MAX_USD = {"SPINEFORGE": Decimal("0.075"), "WRITER": Decimal("0.14")}
MAX_REQUEST_BYTES = 30000
MAX_RESPONSE_BYTES = 200000
KEY_ENV = "OPENROUTER_API_KEY"
SPINE_BEAT = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "location": {"type": "string"},
        "goal": {"type": "string"},
        "choice": {"type": "string"},
        "consequence": {"type": "string"},
        "obligation_reference": {"type": ["string", "null"]},
    },
    "required": ["id", "location", "goal", "choice",
                 "consequence", "obligation_reference"],
}
SPINE_JSON = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "source_pack_sha256": {"type": "string"},
        "beats": {"type": "array", "minItems": 4, "maxItems": 8,
                  "items": SPINE_BEAT},
        "spine_summary": {"type": "string"},
    },
    "required": ["source_pack_sha256", "beats", "spine_summary"],
}
WRITER_JSON = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "source_pack_sha256": {"type": "string"},
        "spine_sha256": {"type": "string"},
        "story_text": {"type": "string"},
        "beat_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["source_pack_sha256", "spine_sha256", "story_text", "beat_ids"],
}


def must(ok, message):
    if not ok:
        raise HarnessStop(message)


def money(value):
    must(type(value) in (int, float, str, Decimal) and type(value) is not bool,
         "Provider money must be numeric")
    try:
        n = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise HarnessStop("Provider cost is not numeric") from exc
    must(n.is_finite() and n >= 0, "Provider cost missing/nonfinite/negative")
    return n


def wire(stage, prompt):
    must(stage in OUTPUT_CAPS, "Unknown stage")
    must(type(prompt) is dict and prompt.get("stage") == stage
         and prompt.get("provider_dispatch_allowed") is False,
         "Source-bound offline prompt required")
    sys_prompt = prompt.get("system_prompt")
    usr_prompt = prompt.get("user_prompt")
    must(type(sys_prompt) is str and type(usr_prompt) is str and
         50 < len(sys_prompt) < 10000 and 50 < len(usr_prompt) < 15000,
         "Invalid generation prompt length")
    schema = SPINE_JSON if stage == "SPINEFORGE" else WRITER_JSON
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": usr_prompt}],
        "max_tokens": OUTPUT_CAPS[stage],
        "stream": False,
        "usage": {"include": True},
        "provider": {
            "only": [PROVIDER], "allow_fallbacks": False,
            "require_parameters": True,
            "max_price": {"prompt": 2, "completion": 10},
        },
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "lumi_p417_" + stage.lower() + "_v1",
            "strict": True, "schema": schema}},
    }
    must(len(canonical_json(body)) <= MAX_REQUEST_BYTES,
         "Oversized model request")
    return body


class BoundedOncePilot:
    """A single predeclared case, shared immutable ledger dir, no retry.

    Default fake transport is allowed only in tests. Real request method is a
    CLI-only guarded explicit entry; no exposed generic arbitrary transport.
    """
    def __init__(self, run_root, *, case_id, plan):
        must(case_id in [c["id"] for c in plan["cases"]],
             "Case not in approved 10 input benchmark")
        must(type(run_root) in (str, Path), "Missing ledger directory")
        root = Path(run_root)
        must(root.is_dir() and not root.is_symlink(),
             "Create protected run root before pilot")
        self.case = next(c for c in plan["cases"] if c["id"] == case_id)
        self.pack = compile_case(self.case)
        self.dir = root / (case_id.lower() + "-" + self.pack["pack_sha256"][:16])
        self.dir.mkdir(mode=0o700, exist_ok=False)
        self.cost = Decimal("0")
        self.calls = 0
        self.halted = False
        self._write("00-claim.json", {
            "schema": SCHEMA, "run_id": self.dir.name,
            "case_id": case_id, "source_sha256": self.pack["pack_sha256"],
            "max_run_spend_usd": format(USD_CAP, "f"),
            "user_total_ceiling_usd": format(GLOBAL_USER_CAP, "f"),
            "status": "CONSUMED_BEFORE_ANY_PROVIDER_POST",
        })

    def _write(self, filename, value):
        path = self.dir / filename
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        handle = os.open(path, flags, 0o600)
        with os.fdopen(handle, "wb") as f:
            f.write(canonical_json(value) + b"\n")
            f.flush()
            os.fsync(f.fileno())

    def _record(self, stage, request, *, cost=None, usage=None, ok=False):
        receipt = {
            "schema": SCHEMA, "stage": stage,
            "exact_wire_sha256": hashlib.sha256(canonical_json(request)).hexdigest(),
            "provider_call_attempted": True,
            "outcome": "SETTLED" if ok else "STOP_UNKNOWN_OR_INVALID",
            "provider_usage": usage if ok else None,
            "provider_reported_cost_usd": format(cost, "f") if cost is not None else None,
            "cumulative_reported_usd": format(self.cost + cost, "f") if cost is not None else None,
            "retry_authorized": False,
        }
        self._write(f"{self.calls:02d}-{stage.lower()}-receipt.json", receipt)

    def call(self, stage, prompt, *, transport):
        must(not self.halted and self.calls < 2
             and (self.calls == 0 and stage == "SPINEFORGE" or
                  self.calls == 1 and stage == "WRITER"),
             "No retries, wrong stage or consumed run")
        must(callable(transport), "Missing bounded POST transport")
        body = wire(stage, prompt)
        self.calls += 1
        self.halted = True
        self._write(f"{self.calls:02d}-{stage.lower()}-intent.json", {
            "schema": SCHEMA, "stage": stage,
            "wire_sha256": hashlib.sha256(canonical_json(body)).hexdigest(),
            "expected_max_tokens": OUTPUT_CAPS[stage],
            "transport_at_most_once": True,
            "no_retry_on_unknown_charge": True,
        })
        result = None
        try:
            result = transport(body)
            must(type(result) is dict and result.get("model") == MODEL,
                 "Unexpected provider model")
            usage = result.get("usage")
            must(type(usage) is dict
                 and type(usage.get("prompt_tokens")) is int
                 and type(usage.get("completion_tokens")) is int
                 and usage["prompt_tokens"] >= 0
                 and 0 <= usage["completion_tokens"] <= OUTPUT_CAPS[stage],
                 "Missing/unbounded provider token count")
            cost = money(usage.get("cost"))
            must(cost <= STAGE_MAX_USD[stage]
                 and self.cost + cost <= USD_CAP
                 and self.cost + cost <= GLOBAL_USER_CAP,
                 "Exceeded stage/one-run/global USD ceiling")
            choices = result.get("choices")
            must(type(choices) is list and len(choices) == 1
                 and choices[0].get("finish_reason") == "stop",
                 "Incomplete generated JSON or output truncated")
            content = choices[0].get("message", {}).get("content")
            must(type(content) is str and len(content) <= MAX_RESPONSE_BYTES,
                 "Missing/oversized provider message")
            parsed = json.loads(content)
            must(type(parsed) is dict, "Expected structured JSON object")
            if stage == "SPINEFORGE":
                prepared = approve_spine_for_writer(self.pack, parsed)
                must(prepared["spine_sha256"] == sha(parsed),
                     "Broken approved Spine hash")
            else:
                must(set(parsed) == {"source_pack_sha256", "spine_sha256",
                                     "story_text", "beat_ids"}
                     and parsed["source_pack_sha256"] == self.pack["pack_sha256"]
                     and type(parsed["spine_sha256"]) is str
                     and type(parsed["story_text"]) is str
                     and type(parsed["beat_ids"]) is list,
                     "Story source/Spine identity malformed")
                expected = getattr(self, "prepared_spine", None)
                must(expected is not None
                     and parsed["spine_sha256"] == expected["spine_sha256"],
                     "Writer substituted an unrelated Spine")
                ids = [x["id"] for x in expected["spine"]["beats"]]
                must(parsed["beat_ids"] == ids,
                     "Writer skipped/reordered approved story beats")
                words = len(parsed["story_text"].split())
                must(self.pack["word_targets"]["min"] <= words <=
                     self.pack["word_targets"]["max"],
                     "Writer failed age-specific story length")
            self._record(stage, body, usage={
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"]},
                cost=cost, ok=True)
            self.cost += cost
            self.halted = False
            if stage == "SPINEFORGE":
                self.prepared_spine = prepared
                return prepared
            self._write("story-draft.json", {
                "schema": SCHEMA, "source_pack_sha256": self.pack["pack_sha256"],
                "spine_sha256": expected["spine_sha256"],
                "model": MODEL, "model_generated": True,
                "quality_accepted": False,
                "english_master_authorized": False,
                "q25_authorized": False,
                "story_state_write_authorized": False,
                "story_sha256": hashlib.sha256(
                    parsed["story_text"].encode("utf-8")).hexdigest(),
                "story_text": parsed["story_text"],
                "word_count": words,
                "total_reported_usd": format(self.cost, "f"),
            })
            return parsed
        except Exception:
            if not (self.dir / f"{self.calls:02d}-{stage.lower()}-receipt.json").exists():
                try:
                    self._record(stage, body, ok=False)
                except Exception:
                    pass
            raise HarnessStop("Paid/synthetic stage failed, run consumed; no retry") from None

    def execute(self, *, transport):
        p = build_spine_request(self.pack)
        prepared = self.call("SPINEFORGE", p, transport=transport)
        writer = build_writer_request(self.pack, prepared)
        result = self.call("WRITER", writer, transport=transport)
        return {
            "schema": SCHEMA, "case_id": self.case["id"],
            "source_pack_sha256": self.pack["pack_sha256"],
            "spine_sha256": prepared["spine_sha256"],
            "story_sha256": hashlib.sha256(
                result["story_text"].encode()).hexdigest(),
            "story_words": len(result["story_text"].split()),
            "real_generation_transport_invoked": True,
            "two_stage_cost_usd": format(self.cost, "f"),
            "quality_accepted": False,
            "english_master_authorized": False,
            "q25_authorized": False,
            "state_write_authorized": False,
        }


def https_post_once(api_key, body):
    must(type(api_key) is str and api_key.startswith("sk-or-")
         and 10 <= len(api_key) <= 256,
         "Missing OpenRouter bearer")
    request = urllib.request.Request(
        ENDPOINT, method="POST",
        headers={"Authorization": "Bearer " + api_key,
                 "Content-Type": "application/json",
                 "Accept": "application/json"},
        data=canonical_json(body),
    )
    try:
        with urllib.request.urlopen(request, timeout=130) as reply:
            must(reply.status == 200 and reply.geturl() == ENDPOINT,
                 "Unexpected completion status/redirect")
            raw = reply.read(MAX_RESPONSE_BYTES + 1)
            must(len(raw) <= MAX_RESPONSE_BYTES,
                 "Oversized completion response")
        return json.loads(raw)
    except HarnessStop:
        raise
    except Exception:
        raise HarnessStop("Provider request failed/unknown billed status; no retry") from None


def public_offline_status(repo_root="."):
    plan = load_plan(repo_root)
    return {
        "schema": SCHEMA,
        "case_count": len(plan["cases"]),
        "first_real_pilot_case": "B01",
        "max_provider_post_calls_per_attempt": 2,
        "aggregate_user_budget_usd": format(GLOBAL_USER_CAP, "f"),
        "per_pilot_maximum_usd": format(USD_CAP, "f"),
        "per_stage_max_usd": {x: format(v, "f") for x, v in STAGE_MAX_USD.items()},
        "run_dir_claim_is_atomic": True,
        "has_automatic_retry": False,
        "provider_model": MODEL,
        "openrouter_secret_value_logged": False,
        "authenticated_openrouter_secret_verified": False,
        "real_provider_calls": 0,
        "real_model_cost_usd": "0",
        "genuine_independent_story_quality_accepted": False,
        "master_q25_state_authorized": False,
        "stop_reason": "P417_OFFLINE_UNTIL_OPERATOR_CONTROLLED_PAID_ONE_SHOT_EXEC",
    }


def main():
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo-root", default=".")
    cli.add_argument("--paid-one-shot", action="store_true")
    cli.add_argument("--case-id", default="B01")
    cli.add_argument("--run-root")
    args = cli.parse_args()
    if not args.paid_one_shot:
        print(json.dumps(public_offline_status(args.repo_root), sort_keys=True))
        return
    must(os.getenv("LUMI_P417_ENABLE_PAID") == "ONE_SHOT_APPROVED_10_USD_USER_LIMIT",
         "Run-specific paid execution switch absent")
    must(args.case_id == "B01" and args.run_root,
         "Paid pilot limited to B01 and explicit durable claims")
    api_key = os.getenv(KEY_ENV, "")
    must(bool(api_key), "No pre-existing GitHub Actions OpenRouter inference secret")
    plan = load_plan(args.repo_root)
    pilot = BoundedOncePilot(args.run_root, case_id=args.case_id, plan=plan)
    # Never print provider response or prompts, only redacted and hashed result.
    print(json.dumps(pilot.execute(
        transport=lambda body: https_post_once(api_key, body)), sort_keys=True))


if __name__ == "__main__":
    main()
