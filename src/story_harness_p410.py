"""Story Harness P4.10 — build actual OpenRouter request previews, never dispatch.

Validate original v21 adapter callback keyword arguments against P4.8's exact
Writer/Spine hashes, construct strict JSON-schema routing with no fallback,
and simulate once-only stage budget reservations. This module has NO network
client, user-authenticated grant or provider spending capability.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p49 import (
    PROFILE_PATH, STORY_SHA, SPINE, exact_file, inspect, must,
)
from src.story_harness_v1 import HarnessStop

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-5.5"
PROVIDER = "Anthropic"
PRICE_INPUT_PER_M = Decimal("2")
PRICE_OUTPUT_PER_M = Decimal("10")
PUBLIC_PRICE_IS_AUTHENTICATED = False
STAGES = {
    "INITIAL_AUDIT": ("spineforge_v21_initial_blocking_audit", 3000),
    "SCENE_REPAIR": ("spineforge_v21_scene_repair", 3500),
    "FINAL_AUDIT": ("spineforge_v21_targeted_final_audit", 1800),
}
STAGE_FILES = {"INITIAL_AUDIT": "01-initial.json",
               "SCENE_REPAIR": "02-repair.json",
               "FINAL_AUDIT": "03-final.json"}
RUN_ID = re.compile(r"^[a-z][a-z0-9_-]{3,47}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
ZERO = Decimal("0")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def bounded_money(value, *, allow_zero=False) -> Decimal:
    must(type(value) in (str, int, Decimal), "Money must be decimal text")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HarnessStop("Invalid money value") from exc
    must(number.is_finite() and number <= Decimal("1") and
         (number >= ZERO if allow_zero else number > ZERO),
         "Invalid or unlimited budget")
    return number


def _load_story(root: Path):
    profile = json.loads(exact_file(root, PROFILE_PATH))
    writer = json.loads(exact_file(root, profile["source_story"]["artifact_path"]))
    story = exact_file(root, writer["repaired_story_path"]).decode("utf-8").rstrip("\n")
    must(digest(story.encode("utf-8")) == STORY_SHA, "Wrong source manuscript SHA")
    return profile, writer, story


def _wire_story(segments):
    must(isinstance(segments, dict) and
         isinstance(segments.get("spans"), list) and
         len(segments["spans"]) == 228 and
         isinstance(segments.get("trailing_whitespace"), str),
         "Initial audit missing exact 228 lossless story spans")
    pieces = []
    for index, span in enumerate(segments["spans"], 1):
        must(type(span) is list and len(span) == 3 and
             span[0] == f"S{index:03d}" and
             all(type(x) is str for x in span),
             "Initial audit lost/changed source segment identity")
        pieces.append(span[1] + span[2])
    return "".join(pieces) + segments["trailing_whitespace"]


def _verify_payload(stage: str, payload: dict, profile: dict, story: str, writer: dict):
    must(type(payload) is dict
         and payload.get("source_story_sha256") == STORY_SHA,
         "Provider request uses a different story identity")
    if "approved_spine_hash" in payload:
        must(payload["approved_spine_hash"] == SPINE,
             "Provider request changed approved Spine")
    if stage == "INITIAL_AUDIT":
        must(payload.get("approved_spine_hash") == SPINE and
             payload.get("reader_profile", {}).get("exact_age") == 12 and
             _wire_story(payload.get("story_segments")) == story,
             "Initial audit does not contain exact full Writer story")
    elif stage == "SCENE_REPAIR":
        cluster = payload.get("scene_cluster") or {}
        must(cluster.get("start_span_id") == "S167"
             and cluster.get("end_span_id") == "S203"
             and (payload.get("entry_boundary") or {}).get("span_id") == "S166"
             and (payload.get("exit_boundary") or {}).get("span_id") == "S204",
             "Provider scene-repair request broadens provisional scope")
        scene = payload.get("source_scene_segments")
        must(type(scene) is dict
             and type(scene.get("spans")) is list
             and len(scene["spans"]) == 37
             and type(scene.get("trailing_whitespace")) is str
             and not scene["trailing_whitespace"].strip(),
             "Scene repair omitted/broadened 37 source segments")
        # Do not trust the attached SHA alone: a syntactically correct source
        # ID with changed scene prose could otherwise reach a live provider.
        from_writer = writer["repaired_segments"]
        for n, row in enumerate(scene["spans"], 167):
            must(type(row) is list and len(row) == 3
                 and row[0] == f"S{n:03d}"
                 and type(row[1]) is str and not row[1].strip()
                 and row[2] == from_writer[n - 1]["repaired_text"],
                 "Scene repair wire prose differs from immutable new Writer")
    else:
        must((payload.get("routing_policy") or {}).get("scope")
             == "REPAIRED_SCENE_PLUS_BOUNDARIES"
             and "story_segments" not in payload
             and "full_story" not in payload,
             "Final audit must be targeted, never full-story")
    must(profile["candidate_scene_scope_review_status"] ==
         "REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED",
         "Provisional scene scope promoted without independent review")


def request_preview(*, repo_root, stage, callback_kwargs):
    """Build a complete in-memory request body from actual v21 callback args.

    The returned request includes manuscript/prompt text; callers MUST NOT
    commit/log it. JSON summaries should use request_receipt(), not this dict.
    No API key or network method is accepted.
    """
    root = Path(repo_root).resolve(strict=True)
    ready = inspect(repo_root=root)  # never skips P4.9 full source checks
    must(ready["paid_dispatch_possible"] is False and
         ready["independent_quality_accepted"] is False,
         "P4.10 cannot inherit an accepted quality/paid authority")
    must(stage in STAGES, "Unknown stage")
    must(type(callback_kwargs) is dict, "Expected authentic callback mapping")
    expected_class, cap = STAGES[stage]
    must(set(callback_kwargs) == {
        "api_key", "model", "system_prompt", "user_prompt", "temperature",
        "max_tokens", "seed", "request_class", "schema_name", "schema",
    }, "Unexpected model adapter callback fields")
    must(callback_kwargs["api_key"] == ""
         and callback_kwargs["model"] == MODEL
         and callback_kwargs["request_class"] == expected_class
         and callback_kwargs["max_tokens"] == cap
         and type(callback_kwargs["max_tokens"]) is int
         and callback_kwargs["temperature"] == 0.0
         and callback_kwargs["seed"] is None,
         "Model request diverges from frozen bounded stage policy")
    prompt = callback_kwargs["system_prompt"]
    user = callback_kwargs["user_prompt"]
    must(type(prompt) is str and prompt.strip() and len(prompt) <= 30000
         and type(user) is str and len(user) <= 175000,
         "Empty or oversized prompt")
    schema_name = callback_kwargs["schema_name"]
    schema = callback_kwargs["schema"]
    must(type(schema_name) is str and
         re.fullmatch(r"spineforge_v21_[a-z_]+_v1", schema_name) is not None
         and type(schema) is dict and schema.get("type") == "object"
         and schema.get("additionalProperties") is False and
         len(canonical_json(schema)) <= 4096,
         "Strict v21 JSON schema missing/unsupported")
    expected_schema_name = {
        "INITIAL_AUDIT": "spineforge_v21_initial_blocking_audit_v1",
        "SCENE_REPAIR": "spineforge_v21_scene_repair_v1",
        "FINAL_AUDIT": "spineforge_v21_targeted_final_audit_v1",
    }[stage]
    must(schema_name == expected_schema_name, "Schema/stage confusion")
    try:
        payload = json.loads(user, parse_constant=lambda v: (_ for _ in ()).throw(
            ValueError("Non-finite JSON value")))
    except (ValueError, TypeError) as exc:
        raise HarnessStop("Invalid wire JSON") from exc
    profile, writer, story = _load_story(root)
    must(profile["source_story"]["story_sha256"] == STORY_SHA
         and writer["artifact_id"] == ready["writer_artifact_id"]
         and profile["approved_spine_hash"] == SPINE,
         "P4.10 source not the reviewed P4.8 candidate")
    _verify_payload(stage, payload, profile, story, writer)

    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": prompt},
                     {"role": "user", "content": user}],
        "temperature": 0.0,
        "max_tokens": cap,
        "stream": False,
        "provider": {"only": [PROVIDER], "allow_fallbacks": False,
                     "require_parameters": True},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": schema_name, "strict": True, "schema": schema,
        }},
    }
    return {"endpoint": ENDPOINT, "method": "POST", "stage": stage,
            "body": body, "live_dispatch_allowed": False,
            "authenticated_provider_route": False,
            "source_story_sha256": STORY_SHA}


def request_receipt(preview: dict, declared_input_ceiling_tokens: int):
    """Safe metadata-only receipt, NOT a tokenizer-verified request estimate."""
    must(preview["endpoint"] == ENDPOINT
         and preview["method"] == "POST"
         and preview["live_dispatch_allowed"] is False
         and preview["authenticated_provider_route"] is False
         and preview["source_story_sha256"] == STORY_SHA,
         "Forged live routing/request admission")
    stage = preview["stage"]
    must(stage in STAGES, "Invalid preview stage")
    body = preview["body"]
    must(body.get("model") == MODEL
         and body.get("provider") == {
             "only": [PROVIDER], "allow_fallbacks": False,
             "require_parameters": True,
         } and body.get("response_format", {}).get("type") == "json_schema"
         and body.get("response_format", {}).get("json_schema", {}).get("strict") is True
         and body.get("max_tokens") == STAGES[stage][1]
         and body.get("stream") is False,
         "Unchecked provider fallback or output cap")
    must(type(declared_input_ceiling_tokens) is int
         and 1 <= declared_input_ceiling_tokens <= 100000,
         "Missing validated input-token ceiling")
    estimate = (
        Decimal(declared_input_ceiling_tokens) * PRICE_INPUT_PER_M
        + Decimal(STAGES[stage][1]) * PRICE_OUTPUT_PER_M
    ) / Decimal(1000000)
    return {
        "schema": "lumi.story-harness-p410-request-receipt.v1",
        "stage": stage, "story_sha256": STORY_SHA,
        "provider": PROVIDER, "fallback_allowed": False,
        "json_schema_strict": True,
        "body_sha256": digest(canonical_json(body)),
        "declared_input_ceiling_tokens": declared_input_ceiling_tokens,
        "input_ceiling_provider_verified": False,
        "max_output_tokens": STAGES[stage][1],
        "conditional_exposure_usd": format(estimate, "f"),
        "request_time_provider_price_verified": False,
        "live_dispatch_allowed": False,
    }


def _json_create_once(path: Path, value: dict) -> None:
    data = canonical_json(value) + b"\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


class OfflineReservationLedger:
    """Synthetic sequential stage spending reservation. NOT a live grant store.

    A crash consumes the run/stage identifier. No resume, retry, release or
    reallocation. Concurrent use of the same run ID can never create two
    initial claims. All receipts are marked synthetic/non-authoritative.
    """

    def __init__(self, root, run_id, *, total_limit="0.25"):
        must(type(run_id) is str and RUN_ID.fullmatch(run_id) is not None,
             "Invalid reservation run ID")
        self.root = Path(root).resolve(strict=True)
        must(self.root.is_dir() and not self.root.is_symlink(),
             "Unsafe reservation root")
        self.run_id = run_id
        self.limit = bounded_money(total_limit)
        self.directory = self.root / run_id
        self.directory.mkdir(mode=0o700, exist_ok=False)
        _json_create_once(self.directory / "claim.json", {
            "schema": "lumi.story-harness-p410-offline-claim.v1",
            "run_id": run_id, "story_sha256": STORY_SHA,
            "synthetic": True, "authenticated_user_grant": False,
            "live_provider_dispatch_allowed": False,
            "total_limit_usd": format(self.limit, "f"),
        })

    def reserve(self, receipt: dict):
        must(type(receipt) is dict
             and receipt.get("schema") == "lumi.story-harness-p410-request-receipt.v1"
             and receipt.get("story_sha256") == STORY_SHA
             and receipt.get("input_ceiling_provider_verified") is False
             and receipt.get("request_time_provider_price_verified") is False
             and receipt.get("live_dispatch_allowed") is False
             and receipt.get("fallback_allowed") is False
             and SHA.fullmatch(receipt.get("body_sha256", "")) is not None,
             "Only safe simulated request receipts can be reserved")
        stage = receipt["stage"]
        must(stage in STAGES, "Unknown reservation stage")
        index = list(STAGES).index(stage)
        previous = list(STAGES)[:index]
        if stage == "INITIAL_AUDIT":
            must(not any((self.directory / STAGE_FILES[s]).exists()
                         for s in STAGES), "Initial attempt already started")
        else:
            must(all((self.directory / STAGE_FILES[s]).is_file()
                     and not (self.directory / STAGE_FILES[s]).is_symlink()
                     for s in previous),
                 "Out-of-order stage or missing preceding reservation")
        must(not (self.directory / STAGE_FILES[stage]).exists(),
             "Duplicate model stage reservation")
        spent = ZERO
        for prev in previous:
            p = self.directory / STAGE_FILES[prev]
            must(not p.is_symlink(), "Ledger stage receipt symlink")
            stored = json.loads(p.read_text(encoding="utf-8"))
            must(stored.get("stage") == prev
                 and stored.get("story_sha256") == STORY_SHA
                 and stored.get("synthetic") is True,
                 "Corrupted earlier stage claim")
            spent += bounded_money(stored["reserved_usd"])
        reserved = bounded_money(receipt.get("conditional_exposure_usd"))
        must(spent + reserved <= self.limit,
             "Offline budget exhausted: STOP; never auto retry")
        entry = {
            "schema": "lumi.story-harness-p410-offline-reservation.v1",
            "run_id": self.run_id, "stage": stage,
            "story_sha256": STORY_SHA, "body_sha256": receipt["body_sha256"],
            "reserved_usd": format(reserved, "f"),
            "cumulative_usd": format(spent + reserved, "f"),
            "synthetic": True, "authenticated_user_grant": False,
            "provider_dispatch_count": 0,
        }
        _json_create_once(self.directory / STAGE_FILES[stage], entry)
        return entry


def block_live_dispatch(*args, **kwargs):
    raise HarnessStop("P410_OFFLINE_CONTRACT_ONLY_NO_USER_AUTHENTICATED_LIVE_DISPATCH")


def status(*, repo_root):
    prior = inspect(repo_root=repo_root)
    return {
        "schema": "lumi.story-harness-p410-offline-routing-and-ledger.v1",
        "story_sha256": prior["story_sha256"],
        "writer_segments": prior["full_story_segment_count"],
        "route_preview_endpoint": ENDPOINT,
        "model": MODEL, "only_provider": PROVIDER,
        "provider_fallbacks_in_preview": False,
        "strict_json_schema": True,
        "max_stage_output_tokens": list(cap for _, cap in STAGES.values()),
        "live_routing_provider_authenticated": False,
        "provider_token_ceiling_authenticated": False,
        "authenticated_user_grant_consumed": False,
        "single_run_offline_reservation_simulation_available": True,
        "new_provider_calls": 0, "new_cost_usd": "0",
        "english_master_authorized": False,
        "q25_authorized": False, "state_write_authorized": False,
        "stop_reason": "P410_OFFLINE_ROUTING_AND_LEDGER_QUALIFIED_LIVE_DISABLED",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(json.dumps(status(repo_root=args.repo_root), sort_keys=True, indent=2))
