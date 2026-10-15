"""P4.9: source-bound, read-only review packet before ONE paid quality attempt.

NO live provider integration, no signed grant verifier, no dispatch code.
A GREEN packet reports verifiable prerequisites and exact blocking conditions;
it NEVER authorizes API calls, independent quality ACCEPT, Q25, or production.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from src.story_harness_p48 import PROFILE_SHA, STORY_SHA, SPINE
from src.story_harness_v1 import HarnessStop

PROFILE_PATH = "configs/story_harness_p48_source_profile.json"
MAX_REPAIR_SPANS = 40
ORIGINAL_OUTPUT_CAPS = (3000, 3500, 1800)
HISTORICAL_INPUT_TOKENS = (9949, 5034, 5106)
PRICE_REFERENCE = "https://openrouter.ai/anthropic/claude-sonnet-5.5/providers"


def must(test: bool, explanation: str) -> None:
    if not test:
        raise HarnessStop(explanation)


def exact_file(root: Path, path: str) -> bytes:
    must(isinstance(path, str) and re.fullmatch(r"[A-Za-z0-9_.\-/]+", path)
         and ".." not in Path(path).parts and not path.startswith("/"),
         "Unsafe P4.9 artifact path")
    target = root
    for part in Path(path).parts:
        target = target / part
        must(not target.is_symlink(), "P4.9 symlink artifact forbidden")
    must(target.is_file() and target.resolve().is_relative_to(root)
         and target.stat().st_size < 300000, "Missing or oversized P4.9 file")
    return target.read_bytes()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def conditional_three_stage_cost(input_tokens, output_caps=ORIGINAL_OUTPUT_CAPS,
                                 input_price="2", output_price="10") -> Decimal:
    """Illustrative token arithmetic only; NOT a provider quote or hard cap."""
    must(len(input_tokens) == len(output_caps) == 3, "Expected three quality stages")
    for n in (*input_tokens, *output_caps):
        must(type(n) is int and n >= 0 and n <= 1000000,
             "Invalid/unbounded stage token count")
    try:
        inp, out = Decimal(str(input_price)), Decimal(str(output_price))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HarnessStop("Invalid pricing amount") from exc
    must(inp.is_finite() and out.is_finite() and inp >= 0 and out >= 0,
         "Nonfinite or negative pricing")
    return (Decimal(sum(input_tokens)) * inp
            + Decimal(sum(output_caps)) * out) / Decimal(1000000)


def review_packet(profile: dict, writer: dict, story_bytes: bytes) -> dict:
    """Validate cross-artifact identity and expose BLOCKERS, never paid permission."""
    source = profile.get("source_story", {})
    must(profile.get("schema") == "lumi.story-harness-p48-new-writer-source.v1"
         and source.get("story_sha256") == STORY_SHA
         and writer.get("repaired_story_text_sha256") == STORY_SHA
         and writer.get("artifact_id") == source.get("artifact_id")
         and source.get("artifact_id") == "story-writer-candidate:" + STORY_SHA
         and profile.get("approved_spine_hash") == SPINE
         and writer.get("approved_spine_hash") == SPINE
         and profile.get("reader_profile", {}).get("exact_age") == 12
         and writer.get("word_count") == 2491
         and writer.get("model_generated") is False
         and writer.get("semantic_quality_accepted") is False,
         "P4.9 wrong Writer/Spine/source identity")
    must(sha(story_bytes) == writer.get("repaired_story_file_sha256"),
         "P4.9 story file bytes changed")
    story = story_bytes.decode("utf-8").rstrip("\n")
    must(sha(story.encode("utf-8")) == STORY_SHA, "P4.9 story text SHA mismatch")
    segments = writer.get("repaired_segments")
    must(type(segments) is list and len(segments) == 228, "Wrong segment count")
    cursor = 0
    for index, span in enumerate(segments, 1):
        must(span.get("span_id") == f"S{index:03d}"
             and span.get("source_text") == span.get("repaired_text")
             and type(span.get("repaired_text")) is str,
             "P4.9 segments changed or reordered")
        part = span["repaired_text"]
        location = story.find(part, cursor)
        must(location >= cursor and not story[cursor:location].strip(),
             "P4.9 segments not faithful to current full text")
        cursor = location + len(part)
    must(not story[cursor:].strip(), "P4.9 unaccounted manuscript text")

    scope = profile.get("candidate_scene_scope", {})
    bridge = profile.get("bridge_full_scene_span_range", {})
    must(scope == {"start_span_id": "S167", "end_span_id": "S203",
                   "span_count": 37,
                   "outside_scope_blocking_policy": "REJECT_UNBOUNDED_REPAIR_SCOPE"}
         and bridge == {"start_span_id": "S162", "end_span_id": "S206",
                        "span_count": 45,
                        "fully_bounded_one_scene_repair_feasible": False}
         and profile.get("candidate_scene_scope_review_status")
             == "REMAP_OF_ORIGINAL_APPROVED_BEAT_NOT_HUMAN_REAPPROVED"
         and bridge["span_count"] > MAX_REPAIR_SPANS >= scope["span_count"],
         "P4.9 unapproved scene remap or repair span limit changed")
    must(segments[161]["repaired_text"].startswith("They ran to the root bridge")
         and segments[166]["repaired_text"].startswith("A living tree leaned")
         and segments[202]["repaired_text"].startswith("Across the gap")
         and segments[205]["repaired_text"] == '"Always."',
         "P4.9 scene-coordinate source anchors changed")
    must(profile.get("max_quality_calls") == 3
         and profile.get("max_repairs") == 1
         and profile.get("full_story_final_reaudit_forbidden") is True
         and profile.get("model_slots") == {
             "BLOCKING_AUDITOR": "anthropic/claude-sonnet-5.5",
             "SCENE_REPAIRER": "anthropic/claude-sonnet-5.5"},
         "P4.9 bounded model topology changed")
    must(profile.get("real_provider_dispatch_allowed") is False
         and profile.get("explicit_finite_paid_execution_grant") is None
         and profile.get("pricing_routing_request_count_verified") is False
         and profile.get("real_provider_spend_guaranteed") is False
         and profile.get("independent_quality_accept") is False
         and profile.get("english_master_authorized") is False
         and profile.get("q25_authorized") is False
         and profile.get("state_write_authorized") is False
         and profile.get("proposed_paid_total_ceiling_usd") == 0.25,
         "P4.9 has no authenticated grant or quality/paid authority")
    must(profile.get("source_story", {}).get("artifact_id")
         != "story-writer-candidate:" + "4f64a28eca70f29689e06d1baad3d3a471682bf3e4fce86dabad1c641410f636",
         "Cannot use original paid story identity")

    cost = conditional_three_stage_cost(HISTORICAL_INPUT_TOKENS)
    must(cost == Decimal("0.123178"), "Unexpected illustrative price arithmetic")
    blockers = [
        "NEW_SCENE_REMAP_NOT_HUMAN_REAPPROVED",
        "PROVIDER_ROUTE_AND_REQUEST_TIME_PRICE_NOT_AUTHENTICATED",
        "FUTURE_STAGE_INPUT_TOKEN_CEILINGS_NOT_VERIFIED",
        "FINITE_ONE_ATTEMPT_USER_GRANT_MISSING",
        "VERSIONED_LIVE_DISPATCH_AND_SPEND_RESERVATION_NOT_IMPLEMENTED",
    ]
    return {
        "schema": "lumi.story-harness-p49-paid-readiness.v1",
        "story_sha256": STORY_SHA,
        "writer_artifact_id": writer["artifact_id"],
        "approved_spine_hash": SPINE,
        "full_story_word_count": writer["word_count"],
        "full_story_segment_count": len(segments),
        "full_bridge_scene": {"first": "S162", "last": "S206", "count": 45},
        "provisional_scene_repair": {"first": "S167", "last": "S203",
                                      "count": 37, "max_count": MAX_REPAIR_SPANS,
                                      "human_reapproved": False},
        "out_of_scope_blocker_result": "REJECT_UNBOUNDED_REPAIR_SCOPE",
        "historical_actual_input_tokens": list(HISTORICAL_INPUT_TOKENS),
        "original_max_output_tokens": list(ORIGINAL_OUTPUT_CAPS),
        "public_price_reference_url": PRICE_REFERENCE,
        "public_list_price_input_per_million_usd": "2",
        "public_list_price_output_per_million_usd": "10",
        "conditional_old_input_plus_max_output_cost_usd": format(cost, "f"),
        "conditional_estimate_is_actual_new_request": False,
        "price_or_hard_cap_provider_authenticated": False,
        "proposed_total_cost_limit_usd": "0.25",
        "proposed_limit_is_approved_grant": False,
        "paid_attempt_authorized": False,
        "paid_dispatch_possible": False,
        "independent_quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False,
        "state_write_authorized": False,
        "new_provider_calls": 0,
        "new_provider_cost_usd": "0",
        "blockers": blockers,
        "stop_reason": "P49_SOURCE_VERIFIED_LIVE_PAID_ATTEMPT_NOT_READY",
    }


def inspect(*, repo_root: str | Path) -> dict:
    root = Path(repo_root).resolve(strict=True)
    prof_bytes = exact_file(root, PROFILE_PATH)
    must(sha(prof_bytes) == PROFILE_SHA, "P4.9 wrong original P4.8 profile hash")
    profile = json.loads(prof_bytes)
    source = profile["source_story"]
    writer_bytes = exact_file(root, source["artifact_path"])
    must(sha(writer_bytes) == source["artifact_sha256"],
         "P4.9 Writer artifact digest mismatch")
    writer = json.loads(writer_bytes)
    manuscript = exact_file(root, writer["repaired_story_path"])
    return review_packet(profile, writer, manuscript)


def require_paid_dispatch(*args, **kwargs):
    """This version intentionally contains no live dispatch capability."""
    raise HarnessStop("P49_OFFLINE_ONLY_AUTHENTICATED_LIVE_GRANT_AND_ROUTING_REQUIRED")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    options = parser.parse_args()
    print(json.dumps(inspect(repo_root=options.repo_root),
                     sort_keys=True, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
