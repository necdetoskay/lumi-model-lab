"""One generic, read-only producer source adapter for every frozen benchmark case.

The old B01/B07 adapters remain intact as original historic truth sources.
This never calls a provider, never accepts a quality result, and requires
pre-pinned SHA-256 digests of *all four* genuine provider artifact bytes.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, sha
from src.story_harness_p417_live_pilot import MODEL, STAGE_MAX_USD, USD_CAP, money
from src.story_harness_v1 import HarnessStop

ORIGINAL_FILES = (
    "spine-plan.json", "story-draft.json",
    "01-spineforge-receipt.json", "02-writer-receipt.json",
)
SHA = re.compile(r"[0-9a-f]{64}\Z")


def must(ok, reason):
    if not ok:
        raise HarnessStop("COHORT_SOURCE_STOP_" + reason)


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        must(key not in out, "DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def _strict_artifact(folder, name, expected_hash):
    p = folder / name
    must(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 200000,
         "MISSING_OR_UNSAFE_ARTIFACT")
    raw = p.read_bytes()
    must(hashlib.sha256(raw).hexdigest() == expected_hash, "ARTIFACT_SHA_MISMATCH")
    return json.loads(raw, object_pairs_hook=_unique_object)


def load_original_case(repo_root, producer_root, *, case_id, trusted_file_sha256):
    """Return the P4.22 initial audit-compatible source for any of ten cases.

    trusted_file_sha256 MUST be provided by a separately sealed, read-only
    immutable evidence registry. Hashes inferred from local writable files
    are not acceptable to this source-admission function.
    """
    must(type(trusted_file_sha256) is dict and
         set(trusted_file_sha256) == set(ORIGINAL_FILES) and
         all(type(v) is str and SHA.fullmatch(v) is not None
             for v in trusted_file_sha256.values()), "TRUST_REGISTRY_REQUIRED")
    plan = load_plan(repo_root)
    must(type(case_id) is str and re.fullmatch(r"B(0[1-9]|10)", case_id)
         and case_id in [x["id"] for x in plan["cases"]], "UNREGISTERED_CASE")
    case = next(c for c in plan["cases"] if c["id"] == case_id)
    pack = compile_case(case)
    root = Path(producer_root)
    must(root.is_dir() and not root.is_symlink(), "UNSAFE_PRODUCER_ROOT")
    folder = root / (case_id.lower() + "-" + pack["pack_sha256"][:16] + "-r06")
    must(folder.is_dir() and not folder.is_symlink(), "CASE_CLAIM_MISSING")
    artifacts = {
        name: _strict_artifact(folder, name, trusted_file_sha256[name])
        for name in ORIGINAL_FILES
    }
    spine = artifacts["spine-plan.json"]
    story = artifacts["story-draft.json"]
    must(spine.get("schema") == "lumi.story-harness-p421-real-spine-artifact.v1"
         and spine.get("case_id") == case_id
         and spine.get("source_pack_sha256") == pack["pack_sha256"]
         and type(spine.get("spine")) is dict
         and spine.get("spine_sha256") == sha(spine["spine"])
         and spine.get("original_semantic_quality_accepted") is False
         and spine.get("english_master_authorized") is False
         and spine.get("no_manual_spine_edits") is True,
         "SPINE_LINEAGE")
    text = story.get("story_text")
    must(story.get("schema") == "lumi.story-harness-p417-real-provider-pilot.v1"
         and story.get("model") == MODEL
         and story.get("model_generated") is True
         and story.get("source_pack_sha256") == pack["pack_sha256"]
         and story.get("spine_sha256") == spine["spine_sha256"]
         and story.get("spine_artifact_path") == "spine-plan.json"
         and type(text) is str
         and hashlib.sha256(text.encode("utf-8")).hexdigest() == story.get("story_sha256")
         and len(text.split()) == story.get("word_count")
         and pack["word_targets"]["min"] <= story["word_count"] <= pack["word_targets"]["max"]
         and story.get("quality_accepted") is False
         and story.get("english_master_authorized") is False
         and story.get("q25_authorized") is False
         and story.get("story_state_write_authorized") is False,
         "STORY_LINEAGE_OR_QUALITY_OVERCLAIM")
    charges = []
    for label, receipt in (
        ("SPINEFORGE", artifacts["01-spineforge-receipt.json"]),
        ("WRITER", artifacts["02-writer-receipt.json"]),
    ):
        usage = receipt.get("provider_usage")
        charge = money(receipt.get("provider_reported_cost_usd"))
        must(receipt.get("schema") == "lumi.story-harness-p417-real-provider-pilot.v1"
             and receipt.get("stage") == label
             and receipt.get("outcome") == "SETTLED"
             and receipt.get("provider_call_attempted") is True
             and receipt.get("retry_authorized") is False
             and type(receipt.get("provider_generation_id")) is str
             and receipt["provider_generation_id"].startswith("gen-")
             and type(usage) is dict
             and type(usage.get("prompt_tokens")) is int
             and type(usage.get("completion_tokens")) is int
             and usage["prompt_tokens"] >= 0 and usage["completion_tokens"] >= 0
             and Decimal("0") < charge <= STAGE_MAX_USD[label],
             "UNVERIFIED_PROVIDER_STAGE")
        charges.append(charge)
    must(spine.get("provider_generation_id") ==
         artifacts["01-spineforge-receipt.json"]["provider_generation_id"],
         "SPINE_PROVIDER_ID_MISMATCH")
    must(sum(charges) <= USD_CAP and
         sum(charges) == money(story["total_reported_usd"]),
         "GENERATION_COST_MISMATCH")
    must(artifacts["02-writer-receipt.json"]["cumulative_reported_usd"] ==
         story["total_reported_usd"], "WRITER_TOTAL_MISMATCH")
    return {
        "pack": pack, "spine": spine, "story": story,
        "case_id": case_id, "run_variant": "r06",
        "original_claim_id": folder.name,
        "generation_cost_usd": format(sum(charges), "f"),
        "producer_file_sha256": dict(trusted_file_sha256),
        "quality_accepted": False,
        "english_master_authorized": False,
        "q25_authorized": False,
        "production_state_write_authorized": False,
    }
