"""P4.17 real-provider capable bounded state/topic → SpineForge → Writer pilot.

Never treats model prose as accepted English Master/Q25/State. Exactly two
one-shot POST attempts at most, no retry. Persistent O_EXCL claim occurs BEFORE
provider POST; an ambiguous response consumes the entire run.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
import urllib.error

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
DIAGNOSTIC_SCHEMA = "lumi.story-harness-p417-sanitized-failure-diagnostic.v1"
SAFE_ERROR_CODES = {
    "Unexpected provider model": "MODEL_ID_MISMATCH",
    "Missing/unbounded provider token count": "USAGE_TOKENS_INVALID",
    "Provider money must be numeric": "BILLED_COST_NOT_PRESENT",
    "Provider cost is not numeric": "BILLED_COST_NONNUMERIC",
    "Provider cost missing/nonfinite/negative": "BILLED_COST_INVALID",
    "Exceeded stage/one-run/global USD ceiling": "BILLED_COST_OVER_CAP",
    "Incomplete generated JSON or output truncated": "FINISH_REASON_OR_CHOICE_INVALID",
    "Missing/oversized provider message": "CONTENT_MISSING_OR_OVERSIZE",
    "Expected structured JSON object": "MODEL_JSON_NOT_OBJECT",
    "Story source/Spine identity malformed": "WRITER_LINEAGE_BAD",
    "Writer substituted an unrelated Spine": "WRITER_SPINE_MISMATCH",
    "Writer skipped/reordered approved story beats": "WRITER_BEAT_MISMATCH",
    "Writer failed age-specific story length": "WRITER_WORD_COUNT_INVALID",
}
class ProviderTransportFault(HarnessStop):
    def __init__(self, category, hint="UNCLASSIFIED"):
        if category not in {"HTTP_400","HTTP_401","HTTP_402","HTTP_403",
                            "HTTP_404","HTTP_408","HTTP_422","HTTP_429",
                            "HTTP_500","HTTP_502","HTTP_503","HTTP_504",
                            "NETWORK_OR_UNKNOWN","PROVIDER_RESPONSE_OVERSIZE"}:
            category = "PROVIDER_HTTP_OTHER"
        self.category = category
        self.hint = hint if hint in {
            "SCHEMA_UNSUPPORTED_ARRAY_BOUNDS",
            "SCHEMA_OTHER",
            "PARAMETER_UNSUPPORTED",
            "MODEL_UNAVAILABLE",
            "UNCLASSIFIED",
        } else "UNCLASSIFIED"
        super().__init__("Provider refused/failed; sanitized category=" + category)

USD_CAP = Decimal("0.35")
GLOBAL_USER_CAP = Decimal("10")
# Sonnet 5.5 includes mandatory thinking in completion tokens. Real r04
# finished at exactly 1,800 tokens without reaching stop; r05 raises ONLY
# finite per-request output caps, preserving every scene/canon admission rule.
OUTPUT_CAPS = {"SPINEFORGE": 5500, "WRITER": 6500}
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
        "beats": {"type": "array",
                  "description": "Exactly four to eight ordered beats, verified by the local immutable Spine validator.",
                  "items": SPINE_BEAT},
        "spine_summary": {"type": "string"},
    },
    "required": ["source_pack_sha256", "beats", "spine_summary"],
}
SPINE_ENVELOPE_JSON = {
    "type":"object", "additionalProperties":False,
    "properties":{
        "source_pack_sha256":{"type":"string"},
        "spine_summary":{"type":"string"},
        "beats_json":{"type":"string",
            "description":"JSON-encoded array of four to eight complete scene beat objects, source-validated locally."},
    },
    "required":["source_pack_sha256","spine_summary","beats_json"],
}
WRITER_ENVELOPE_JSON = {
    "type":"object", "additionalProperties":False,
    "properties":{
        "source_pack_sha256":{"type":"string"},
        "spine_sha256":{"type":"string"},
        "story_text":{"type":"string"},
        "beat_ids_json":{"type":"string",
            "description":"JSON encoded string array of all approved beat IDs in exact scene order."},
    },
    "required":["source_pack_sha256","spine_sha256","story_text","beat_ids_json"],
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


def wire(stage, prompt, *, simple_envelope=False):
    must(stage in OUTPUT_CAPS, "Unknown stage")
    must(type(prompt) is dict and prompt.get("stage") == stage
         and prompt.get("provider_dispatch_allowed") is False,
         "Source-bound offline prompt required")
    sys_prompt = prompt.get("system_prompt")
    usr_prompt = prompt.get("user_prompt")
    must(type(sys_prompt) is str and type(usr_prompt) is str and
         50 < len(sys_prompt) < 10000 and 50 < len(usr_prompt) < 15000,
         "Invalid generation prompt length")
    # Third same-method correction: mirror source-specific allowed values in
    # the strict JSON Schema itself. Prompt-only instructions are not a
    # contract when the decoder can choose unknown places or obligation text.
    schema = deepcopy(
        (SPINE_ENVELOPE_JSON if stage=="SPINEFORGE" else WRITER_ENVELOPE_JSON)
        if simple_envelope else
        (SPINE_JSON if stage=="SPINEFORGE" else WRITER_JSON))
    try:
        input_payload = json.loads(usr_prompt)
    except (TypeError, ValueError):
        raise HarnessStop("Malformed model source payload") from None
    must(type(input_payload) is dict and
         input_payload.get("pack_sha256",
                           input_payload.get("source_pack_sha256")) ==
         prompt["source_pack_sha256"],
         "Model prompt SHA differs from the source pack")
    if simple_envelope:
        # A flat outer JSON Schema is compatible with the proven OpenRouter
        # P4.18 primitive strict-output path. The complete nested Canon/scene
        # validator still runs after decoding the JSON-string payload.
        if stage == "SPINEFORGE":
            sys_prompt += (
                " For this provider-compatible output use exactly three "
                "fields: source_pack_sha256, spine_summary, beats_json. "
                "beats_json MUST be a valid JSON STRING containing a JSON "
                "array of 4-8 beat objects with fields id,location,goal,"
                "choice,consequence,obligation_reference; use a JSON null "
                "for nonreferenced obligations. Do not return a beats array "
                "as an outer JSON property.")
        else:
            sys_prompt += (
                " For this provider-compatible output use exactly four "
                "fields: source_pack_sha256,spine_sha256,story_text,beat_ids_json. "
                "beat_ids_json MUST be a JSON STRING encoding an array of "
                "all exact approved beat IDs in order, not an outer JSON "
                "array or commentary.")
    elif stage == "SPINEFORGE":
        state = input_payload.get("canonical_state")
        must(type(state) is dict and type(state.get("locations")) is list
             and state["locations"] and
             type(input_payload.get("open_obligations")) is list,
             "Invalid source-specific Spine schema inputs")
        props = schema["properties"]["beats"]["items"]["properties"]
        schema["properties"]["source_pack_sha256"]["enum"] = [
            prompt["source_pack_sha256"]]
        props["id"]["enum"] = [f"BEAT_{n:02d}" for n in range(1, 9)]
        props["location"]["enum"] = list(state["locations"])
        props["obligation_reference"]["enum"] = [
            None, *input_payload["open_obligations"]]
    else:
        sha_spine = prompt.get("spine_sha256")
        beats = input_payload.get("approved_beats")
        must(type(sha_spine) is str and len(sha_spine) == 64
             and type(beats) is list and 4 <= len(beats) <= 8,
             "Invalid Writer Spine source/beat list")
        ids = [b["id"] for b in beats]
        schema["properties"]["source_pack_sha256"]["enum"] = [
            prompt["source_pack_sha256"]]
        schema["properties"]["spine_sha256"]["enum"] = [sha_spine]
        schema["properties"]["beat_ids"]["items"]["enum"] = ids
        schema["properties"]["beat_ids"]["description"] = (
            "Include all " + str(len(ids)) +
            " approved beat IDs exactly once in their approved order; "
            "source-bound application validation enforces this.")
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
            "name": "lumi_p417_" + stage.lower() +
                    ("_flat_v2" if simple_envelope else "_v1"),
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
    def __init__(self, run_root, *, case_id, plan, run_variant='r01'):
        must(case_id in [c["id"] for c in plan["cases"]],
             "Case not in approved 10 input benchmark")
        must(run_variant in ('r01','r02','r03','r04','r05'),
             "Disallowed or reused paid one-shot run variant")
        must(type(run_root) in (str, Path), "Missing ledger directory")
        root = Path(run_root)
        must(root.is_dir() and not root.is_symlink(),
             "Create protected run root before pilot")
        self.case = next(c for c in plan["cases"] if c["id"] == case_id)
        self.use_simple_envelope = run_variant in ('r04','r05')
        self.pack = compile_case(self.case)
        label = case_id.lower() + "-" + self.pack["pack_sha256"][:16]
        if run_variant != 'r01':
            label += '-' + run_variant
        self.dir = root / label
        self.dir.mkdir(mode=0o700, exist_ok=False)
        self.cost = Decimal("0")
        self.calls = 0
        self.halted = False
        self._write("00-claim.json", {
            "schema": SCHEMA, "run_id": self.dir.name,
            "run_variant": run_variant,
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

    def _record(self, stage, request, *, cost=None, usage=None, ok=False,
                diagnostic=None, generation_id=None):
        receipt = {
            "schema": SCHEMA, "stage": stage,
            "exact_wire_sha256": hashlib.sha256(canonical_json(request)).hexdigest(),
            "provider_call_attempted": True,
            "outcome": "SETTLED" if ok else "STOP_UNKNOWN_OR_INVALID",
            "provider_usage": usage if (ok or usage is not None) else None,
            "provider_reported_cost_usd": format(cost, "f") if cost is not None else None,
            "cumulative_reported_usd": format(self.cost + cost, "f") if cost is not None else None,
            "retry_authorized": False,
            "safe_failure_diagnostic": diagnostic if not ok else None,
            "provider_generation_id": generation_id,
        }
        self._write(f"{self.calls:02d}-{stage.lower()}-receipt.json", receipt)

    def call(self, stage, prompt, *, transport):
        must(not self.halted and self.calls < 2
             and (self.calls == 0 and stage == "SPINEFORGE" or
                  self.calls == 1 and stage == "WRITER"),
             "No retries, wrong stage or consumed run")
        must(callable(transport), "Missing bounded POST transport")
        body = wire(stage, prompt,
                    simple_envelope=self.use_simple_envelope)
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
        diagnostic_phase = "TRANSPORT"
        try:
            result = transport(body)
            diagnostic_phase = "PROVIDER_ENVELOPE"
            must(type(result) is dict and result.get("model") == MODEL,
                 "Unexpected provider model")
            usage = result.get("usage")
            diagnostic_phase = "PROVIDER_USAGE"
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
            diagnostic_phase = "PROVIDER_FINISH"
            must(type(choices) is list and len(choices) == 1
                 and choices[0].get("finish_reason") == "stop",
                 "Incomplete generated JSON or output truncated")
            content = choices[0].get("message", {}).get("content")
            must(type(content) is str and len(content) <= MAX_RESPONSE_BYTES,
                 "Missing/oversized provider message")
            diagnostic_phase = "JSON_PARSE"
            parsed = json.loads(content)
            must(type(parsed) is dict, "Expected structured JSON object")
            if self.use_simple_envelope:
                # Only decoding the wrapper changes; all pre-existing
                # source/scene/Word/Spine/Story admission checks below remain.
                if stage == "SPINEFORGE":
                    must(set(parsed) == {
                        "source_pack_sha256","spine_summary","beats_json"
                    } and type(parsed["beats_json"]) is str and
                         len(parsed["beats_json"]) <= MAX_RESPONSE_BYTES,
                         "Malformed flat Spine envelope")
                    beat_list = json.loads(parsed["beats_json"])
                    must(type(beat_list) is list,
                         "Flat Spine beats were not JSON array")
                    parsed = {
                        "source_pack_sha256":parsed["source_pack_sha256"],
                        "spine_summary":parsed["spine_summary"],
                        "beats":beat_list,
                    }
                else:
                    must(set(parsed) == {
                        "source_pack_sha256","spine_sha256",
                        "story_text","beat_ids_json"
                    } and type(parsed["beat_ids_json"]) is str and
                         len(parsed["beat_ids_json"]) <= 4096,
                         "Malformed flat Writer envelope")
                    beat_ids = json.loads(parsed["beat_ids_json"])
                    must(type(beat_ids) is list,
                         "Flat Writer beat IDs were not a JSON array")
                    parsed = {
                        "source_pack_sha256":parsed["source_pack_sha256"],
                        "spine_sha256":parsed["spine_sha256"],
                        "story_text":parsed["story_text"],
                        "beat_ids":beat_ids,
                    }
            diagnostic_phase = "SPINE_VALIDATION" if stage == "SPINEFORGE" else "WRITER_VALIDATION"
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
            generation_id = result.get("id")
            if not (type(generation_id) is str and
                    re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}", generation_id)):
                generation_id = None
            self._record(stage, body, usage={
                "prompt_tokens": usage["prompt_tokens"],
                "completion_tokens": usage["completion_tokens"]},
                cost=cost, ok=True, generation_id=generation_id)
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
        except Exception as exc:
            # Never serialize arbitrary provider error messages, response prose,
            # URL, bearer credentials or untrusted exception str().
            if isinstance(exc, ProviderTransportFault):
                failure = exc.category
            elif isinstance(exc, json.JSONDecodeError):
                failure = "MODEL_JSON_PARSE"
            elif isinstance(exc, HarnessStop):
                failure = SAFE_ERROR_CODES.get(str(exc),
                    "SPINE_SEMANTIC_VALIDATION" if diagnostic_phase == "SPINE_VALIDATION"
                    else "OTHER_CONTRACT_VALIDATION")
            else:
                failure = "UNEXPECTED_RUNTIME_FAILURE"
            usage = result.get("usage") if type(result) is dict else None
            diag = {
                "schema": DIAGNOSTIC_SCHEMA, "phase": diagnostic_phase,
                "safe_failure_code": failure,
                "provider_envelope_received": result is not None,
                "usage_object_present": type(usage) is dict,
                "billable_cost_field_present": type(usage) is dict and
                                               "cost" in usage,
                "provider_generation_id_present": type(result) is dict and
                                                   type(result.get("id")) is str,
                "secret_or_manuscript_recorded": False,
                "model_retry_attempts": 0,
                "provider_error_hint": exc.hint
                    if isinstance(exc, ProviderTransportFault) else None,
            }
            # Preserve verifiable usage/cost even if strict story validation
            # rejects the response. Do not turn a missing provider price into 0.
            known_charge = None
            safe_usage = None
            if type(usage) is dict:
                try:
                    if (type(usage.get("prompt_tokens")) is int and
                        type(usage.get("completion_tokens")) is int and
                        usage["prompt_tokens"] >= 0 and
                        usage["completion_tokens"] >= 0):
                        safe_usage = {
                            "prompt_tokens": usage["prompt_tokens"],
                            "completion_tokens": usage["completion_tokens"]}
                    known_charge = money(usage.get("cost"))
                except HarnessStop:
                    pass
            generation_id = result.get("id") if type(result) is dict else None
            if not (type(generation_id) is str and
                    re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}", generation_id)):
                generation_id = None
            if not (self.dir / f"{self.calls:02d}-{stage.lower()}-receipt.json").exists():
                try:
                    self._record(stage, body, cost=known_charge,
                                 usage=safe_usage, ok=False,
                                 diagnostic=diag, generation_id=generation_id)
                except Exception:
                    pass
            raise HarnessStop(
                "Stage failed; consumed without retry. Safe category: " + failure
            ) from None

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
    except urllib.error.HTTPError as exc:
        # The provider HTTP error body is untrusted and may contain a copied
        # prompt or other private material. Never persist or print it. Only
        # classify a few known syntax/support problems to static labels.
        try:
            raw_error = exc.read(8192)
            text_error = raw_error.decode("utf-8", "replace").lower()
        except Exception:
            text_error = ""
        if "maxitems" in text_error or "minitems" in text_error:
            hint = "SCHEMA_UNSUPPORTED_ARRAY_BOUNDS"
        elif "json_schema" in text_error or "response_format" in text_error:
            hint = "SCHEMA_OTHER"
        elif "unsupported" in text_error and "parameter" in text_error:
            hint = "PARAMETER_UNSUPPORTED"
        elif "not available" in text_error and "model" in text_error:
            hint = "MODEL_UNAVAILABLE"
        else:
            hint = "UNCLASSIFIED"
        raise ProviderTransportFault("HTTP_" + str(exc.code), hint) from None
    except HarnessStop:
        raise
    except Exception:
        raise ProviderTransportFault("NETWORK_OR_UNKNOWN") from None


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
    cli.add_argument("--run-variant", default="r01",
                     choices=("r01","r02","r03","r04","r05"))
    args = cli.parse_args()
    if not args.paid_one_shot:
        print(json.dumps(public_offline_status(args.repo_root), sort_keys=True))
        return
    must(os.getenv("LUMI_P417_ENABLE_PAID") == "ONE_SHOT_APPROVED_10_USD_USER_LIMIT",
         "Run-specific paid execution switch absent")
    must(args.case_id == "B01" and args.run_root and
         args.run_variant == "r05",
         "Paid higher-output-cap follow-up limited to B01 distinct r05 with durable claim")
    api_key = os.getenv(KEY_ENV, "")
    must(bool(api_key), "No pre-existing GitHub Actions OpenRouter inference secret")
    plan = load_plan(args.repo_root)
    pilot = BoundedOncePilot(args.run_root, case_id=args.case_id,
                             plan=plan, run_variant=args.run_variant)
    # Never print provider response or prompts, only redacted and hashed result.
    print(json.dumps(pilot.execute(
        transport=lambda body: https_post_once(api_key, body)), sort_keys=True))


if __name__ == "__main__":
    main()
