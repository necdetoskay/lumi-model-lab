"""Aion high/max paired receipt integrity + non-semantic metrics, offline only.

This is a *read-only* audit of existing paid result folders, NOT a writer or
judge; source-anchored cue matches are diagnostic text search, NEVER a claim
of semantic completeness or narrative superiority. Missing data => HOLD.
No API key is read, no provider URL is imported, no rewriting is performed.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from pathlib import Path
import re

from experiments.prototypes.aion35_mini_reasoning_high_max_once_20261017 import (
    MODEL, EFFORTS, SCHEMA, checked, digest, verify_equal_experiment,
)


CUES = {
    "protagonist_deniz": r"\bdeniz\b",
    "tick_sound": r"\btick(?:s|ing|ed)?\b",
    "flowerpot_exploration": r"\b(?:flowerpot|flowerpots|plant\s+pot|plant\s+pots|pots?)\b",
    "railing_investigation": r"\b(?:rail|railing|banister)\b",
    "wind_presence": r"\b(?:wind|breeze|gust)\b",
    "ring_presence": r"\b(?:ring|rings)\b",
    "physical_collision_cue": r"\b(?:touch|touches|touched|hit|hits|bump|bumps|collide|collided|strike|struck|tap|taps)\b",
    "palm_air_experiment": r"\b(?:palm|hand|hands)\b",
    "waiting_end": r"\b(?:wait|waits|waited|waiting|pause|paused|listened|listen)\b",
}


def _read(path):
    checked(path.is_file(), "PAIR_EVIDENCE_MISSING:" + path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value, label):
    if value is None:
        return None
    checked(not isinstance(value, bool), "PAIR_INVALID_NUMBER:" + label)
    try:
        v = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RuntimeError("PAIR_INVALID_NUMBER:" + label) from exc
    checked(v.is_finite() and v >= 0, "PAIR_INVALID_NUMBER:" + label)
    return v


def _simple_cues(story):
    """Presence-only indicators. A detected cue is NOT semantic event proof."""
    lower = story.casefold()
    indicators = {}
    for key, pattern in CUES.items():
        hits = list(re.finditer(pattern, lower, flags=re.IGNORECASE))
        indicators[key] = {
            "lexical_indicator_present": bool(hits),
            "count": len(hits),
            "first_quote": (
                story[hits[0].start():hits[0].end()] if hits else None
            ),
        }
    last = story[-max(300, len(story)//5):]
    indicators["closing_wait_and_tick"] = {
        "lexical_indicator_present": bool(
            re.search(CUES["tick_sound"], last, flags=re.I) and
            re.search(CUES["waiting_end"], last, flags=re.I)
        ),
        "count": None, "first_quote": None,
    }
    return indicators


def _repetition(story):
    # Exact normalized repeated 5-grams are a *risk signal*, not style rating.
    words = re.findall(r"[a-zA-ZÀ-ÿ']+", story.casefold())
    grams = [" ".join(words[i:i+5]) for i in range(max(0, len(words)-4))]
    if not grams:
        return {"repeated_fivegrams": 0, "duplicate_fivegram_ratio": None}
    duplicate = len(grams)-len(set(grams))
    return {
        "repeated_fivegrams": duplicate,
        "duplicate_fivegram_ratio": round(duplicate/len(grams),4),
    }


def _one(root, effort, frozen):
    receipt = _read(root/(effort+".receipt.json"))
    summary = _read(root/(effort+".summary.json"))
    textfile = root/(effort+".txt")
    checked(textfile.is_file(), "PAIR_ORIGINAL_STORY_MISSING")
    story = receipt.get("story")
    checked(isinstance(story,str) and story.strip(),
            "PAIR_PROVIDER_STORY_EMPTY")
    checked(textfile.read_text(encoding="utf-8") == story+"\n",
            "PAIR_STORY_CHANGED_FROM_ORIGINAL_RECEIPT")
    story_sha = sha256(story.encode("utf-8")).hexdigest()
    request_sha = frozen[effort+"_request_sha256"]
    checked(summary.get("effort")==effort and
            summary.get("model")==MODEL and
            summary.get("returned_model")==MODEL and
            summary.get("request_sha256")==request_sha and
            summary.get("story_sha256")==story_sha and
            summary.get("generation_id")==receipt.get("generation_id") and
            summary.get("finish_reason")==receipt.get("finish_reason") and
            summary.get("words")==len(story.split()),
            "PAIR_RECEIPT_SUMMARY_PROVENANCE_DRIFT")
    # Only a complete returned model receipt, never a partial SSE completion.
    checked(receipt.get("returned_model")==MODEL and
            receipt.get("finish_reason")=="stop" and
            isinstance(receipt.get("generation_id"),str) and
            bool(receipt.get("generation_id")),
            "PAIR_PROVIDER_COMPLETION_UNQUALIFIED")
    usage = receipt.get("usage") or {}
    breakdown = usage.get("completion_tokens_details") or {}
    checked(summary.get("usage",{}).get("reasoning_tokens")==
            breakdown.get("reasoning_tokens") and
            summary.get("usage",{}).get("cost_usd_observed")==
            usage.get("cost"),
            "PAIR_USAGE_PROVENANCE_DRIFT")
    output = _number(usage.get("completion_tokens"),
                     "completion_tokens")
    reasoning = _number(breakdown.get("reasoning_tokens"),
                        "reasoning_tokens")
    cost = _number(usage.get("cost"),"cost_usd")
    latency = _number(receipt.get("elapsed_seconds"),"elapsed_seconds")
    return {
        "effort":effort,
        "generation_id":receipt["generation_id"],
        "story_sha256":story_sha,
        "word_count":len(story.split()),
        "within_original_hard_word_range":375<=len(story.split())<=625,
        "completion_tokens":int(output) if output is not None else None,
        "reasoning_tokens":int(reasoning) if reasoning is not None else None,
        "reported_cost_usd":str(cost) if cost is not None else None,
        "latency_seconds":float(latency) if latency is not None else None,
        "lexical_cues_non_authoritative":_simple_cues(story),
        "repetition_indicator":_repetition(story),
        "story_validated_against_physical_truth":False,
        "story_evaluated_by_independent_semantic_judge":False,
    }


def evaluate(root):
    root=Path(root)
    expected=verify_equal_experiment()
    inputs=_read(root/"inputs.json")
    checked(inputs==expected, "PAIR_INPUT_SOURCE_OR_SCOPE_DRIFT")
    final=_read(root/"result.json")
    checked(final.get("schema")==SCHEMA and
            final.get("source_input")==expected and
            final.get("manual_story_repairs")==0 and
            final.get("editor_or_judge_provider_calls")==0 and
            final.get("canonical_world_writes")==0 and
            final.get("production_db_writes")==0 and
            final.get("model_output_token_limit_set") is False,
            "PAIR_UNAUTHORIZED_PROVIDER_OR_WORLD_ACTIONS")
    if final.get("status")!="TWO_GENUINE_PROVIDER_ANSWERS_COMPARABLE":
        return {
            "schema":"aion35-mini-deniz-highmax-integrity-diagnostics-v1",
            "status":"HOLD_INCOMPLETE_PROVIDER_PAIR",
            "comparison_authorized":False,
            "winner":"UNDETERMINED",
            "reason":"One or both original provider responses are missing or unqualified",
            "manual_story_repairs":0,
            "new_provider_calls":0,
            "canonical_world_writes":0,
        }
    checked(final.get("completed_real_provider_replies")==2 and
            final.get("real_paid_posts_started")==2 and
            final.get("both_provider_generations_distinct_and_complete") is True,
            "PAIR_RESULT_STATUS_NOT_SUPPORTED")
    h=_one(root,"high",expected)
    m=_one(root,"max",expected)
    checked(h["generation_id"]!=m["generation_id"],
            "PAIR_DUPLICATE_PROVIDER_GENERATION")
    # No arithmetic on missing usage, unknown spend is never silently zero.
    d={}
    for k in ("word_count","completion_tokens","reasoning_tokens",
              "latency_seconds"):
        a,b=h[k],m[k]
        d[k+"_max_minus_high"]=round(b-a,5) if a is not None and b is not None else None
    a,b=h["reported_cost_usd"],m["reported_cost_usd"]
    d["reported_cost_usd_max_minus_high"]=str(Decimal(b)-Decimal(a)) if a is not None and b is not None else None
    # Numeric differences are observations; with a single sample, no winner.
    return {
        "schema":"aion35-mini-deniz-highmax-integrity-diagnostics-v1",
        "status":"PAIRED_RECEIPTS_VERIFIED_QUALITY_UNDETERMINED",
        "comparison_authorized":True,
        "winner":"UNDETERMINED_NOT_SEMANTICALLY_JUDGED",
        "story_input_hash":expected["common_request_sha256"],
        "model":MODEL,
        "high":h,
        "max":m,
        "max_minus_high":d,
        "lexical_cues_do_not_establish_causality":True,
        "one_pair_cannot_establish_model_superiority":True,
        "new_provider_calls":0,
        "manual_story_repairs":0,
        "canonical_world_writes":0,
    }


def main():
    p=argparse.ArgumentParser(description="Read-only report of existing Aion high/max artifacts")
    p.add_argument("--input-root",required=True,type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    report=evaluate(a.input_root)
    content=json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(content,encoding="utf-8")
    print(content,end="")


if __name__=="__main__":
    main()
