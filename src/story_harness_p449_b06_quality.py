"""P4.49: independent real 12-family initial quality for original B06.

Reuses unchanged P4.22 audit_wire/verify_auditor_reply, but has a new
exact-case source reader and one-shot claim key. Zero provider calls by
default. Neither ACCEPT nor audit can authorize English Master, Q25,
frozen-v21 final approval or production writes.
"""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import sha
from src.story_harness_p417_live_pilot import (
    MODEL, STAGE_MAX_USD, USD_CAP, GLOBAL_USER_CAP, https_post_once, money
)
from src.story_harness_p422_independent_audit import (
    SCHEMA as AUDIT_SCHEMA, STAGE_COST_CAP, audit_wire, verify_auditor_reply
)
from src.story_harness_p446_b06_age12 import source_case, SOURCE_SHA
from src.story_harness_v1 import HarnessStop
from src.story_harness_p447_quality_diagnostics import sanitized_failure_receipt

SCHEMA = "lumi.story-harness-p449-b06-independent-age12-quality.v1"
SPINE_SHA = "f9a5ef2b212aa54c9331205f57ef1e1281795e5dd63d00c627bf5e434ca281e5"
STORY_SHA = "d7f1fa3158d2de18f0209bb545f3cb11bfb94e91736e34afd77d1b4859141870"
SPINE_ID = "gen-1791991380-nM2CyKyyLnN8YYznmX4v"
WRITER_ID = "gen-1791991404-Dkeh5JfuZ7wy4uwI1m3L"
GEN_COST = Decimal("0.081962")
PRIOR_RESERVED = Decimal("2.719558")
USER_CAP = Decimal("10.00")
CLAIM_NAME = "b06-" + SOURCE_SHA[:16] + "-r06"
AUDIT_DIR = "p449-b06-r06-" + STORY_SHA[:12]
PROVIDER_FILE_DIGESTS = {
    "spine-plan.json": "32bebdf530294761dcee909d80f38e86584c7884e8583c778400f7335d91698b",
    "story-draft.json": "e379e6c9809764859ecd2d332f58d75c90443fe7c5cae7562851e861a0786e76",
    "01-spineforge-receipt.json": "d88edc8faf3dc7325312b8557334e78d24c45dd77e9c529d9a443705fc3d7671",
    "02-writer-receipt.json": "4be729887dedf1fdfaf9aabf31f987586d6606c9847ab9e83c4f9754c05529ea",
}

def must(condition, reason):
    if not condition:
        raise HarnessStop(reason)

def _original_json(folder, filename):
    path = folder / filename
    must(path.is_file() and not path.is_symlink()
         and 0 < path.stat().st_size < 200000, "Missing bounded original B06 provider file")
    raw = path.read_bytes()
    must(hashlib.sha256(raw).hexdigest() == PROVIDER_FILE_DIGESTS[filename],
         "B06 provider artifact digest differs from original successful CI archive")
    return json.loads(raw)

def get_original_B06(repo_root, producer_root):
    _, pack = source_case(repo_root)
    root = Path(producer_root)
    must(root.is_dir() and not root.is_symlink(), "Protected B06 generation claim root missing")
    claims = list(root.glob("b06-*-r06"))
    must(len(claims) == 1 and claims[0].name == CLAIM_NAME
         and claims[0].is_dir() and not claims[0].is_symlink(),
         "Missing/non-unique or wrong B06 source claim")
    folder = claims[0]
    spine = _original_json(folder, "spine-plan.json")
    story = _original_json(folder, "story-draft.json")
    saved_root = Path(repo_root) / "evidence/story_harness_p448"
    original_files = {
        "spine-plan.json":"b06-r06-original-spine-plan.json",
        "story-draft.json":"b06-r06-original-writer-draft.json",
        "01-spineforge-receipt.json":"b06-r06-original-spineforge-receipt.json",
        "02-writer-receipt.json":"b06-r06-original-writer-receipt.json",
    }
    for name, frozen in original_files.items():
        p = saved_root / frozen
        must(p.is_file() and not p.is_symlink()
             and p.read_bytes() == (folder / name).read_bytes(),
             "B06 protected provider artifact must exactly match frozen evidence")
    first = _original_json(folder, "01-spineforge-receipt.json")
    second = _original_json(folder, "02-writer-receipt.json")
    must(spine.get("case_id") == "B06"
         and spine.get("schema") == "lumi.story-harness-p421-real-spine-artifact.v1"
         and spine.get("source_pack_sha256") == SOURCE_SHA
         and spine.get("spine_sha256") == SPINE_SHA
         and spine.get("spine_sha256") == sha(spine["spine"])
         and spine.get("provider_generation_id") == SPINE_ID
         and spine.get("original_semantic_quality_accepted") is False,
         "B06 original Spine or provider signature differs")
    must(story.get("schema") == "lumi.story-harness-p417-real-provider-pilot.v1"
         and story.get("source_pack_sha256") == SOURCE_SHA
         and story.get("spine_sha256") == SPINE_SHA
         and story.get("spine_artifact_path") == "spine-plan.json"
         and story.get("model_generated") is True
         and story.get("model") == MODEL
         and story.get("quality_accepted") is False
         and story.get("english_master_authorized") is False
         and story.get("q25_authorized") is False
         and story.get("story_state_write_authorized") is False
         and story.get("word_count") == 2285
         and isinstance(story.get("story_text"), str)
         and len(story["story_text"].split()) == 2285
         and hashlib.sha256(story["story_text"].encode("utf-8")).hexdigest() == STORY_SHA
         and story.get("story_sha256") == STORY_SHA,
         "B06 Writer source, word count or exact manuscript altered")
    paid = []
    for label, receipt, genid in (("SPINEFORGE", first, SPINE_ID),
                                  ("WRITER", second, WRITER_ID)):
        must(receipt.get("schema") == "lumi.story-harness-p417-real-provider-pilot.v1"
             and receipt.get("stage") == label
             and receipt.get("outcome") == "SETTLED"
             and receipt.get("retry_authorized") is False
             and receipt.get("provider_generation_id") == genid
             and isinstance(receipt.get("provider_usage"), dict),
             "B06 original model receipt not truly settled")
        charge = money(receipt.get("provider_reported_cost_usd"))
        must(0 < charge <= STAGE_MAX_USD[label],
             "B06 stage exceeded proven provider cost cap")
        paid.append(charge)
    must(paid == [Decimal("0.029098"), Decimal("0.052864")]
         and sum(paid) == GEN_COST == money(story["total_reported_usd"])
         and sum(paid) <= USD_CAP,
         "B06 actual provider cost reconciliation failed")
    must(PRIOR_RESERVED + STAGE_COST_CAP <= USER_CAP <= GLOBAL_USER_CAP,
         "B06 quality would exceed overall $10 user limit")
    return {
        "pack": pack, "spine": spine, "story": story,
        "case_id": "B06", "run_variant": "r06",
        "generation_cost_usd": format(GEN_COST, "f"),
        "original_claim_id": folder.name,
    }

def inspect_B06_audit(source):
    must(source.get("case_id") == "B06"
         and source["story"]["story_sha256"] == STORY_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["pack"]["reader_age"] == 12,
         "B06 independent QA cannot inherit any other story acceptance")
    body = audit_wire(source)
    payload = json.loads(body["messages"][1]["content"])
    must(payload["case_id"] == "B06"
         and payload["reader_age"] == 12
         and payload["story_sha256"] == STORY_SHA
         and payload["approved_spine_sha256"] == SPINE_SHA
         and body["model"] == MODEL
         and body["provider"]["allow_fallbacks"] is False
         and body["response_format"]["json_schema"]["name"] ==
             "lumi_b06_independent_initial_audit_v1"
         and "12 years old" in body["messages"][0]["content"],
         "B06 audit not independent, age-specific or source-bound")
    return body

def _write_once(path, obj):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical_json(obj) + b"\n")
        f.flush()
        os.fsync(f.fileno())

def audit_B06_once(source, quality_root, *, transport):
    body = inspect_B06_audit(source)
    root = Path(quality_root)
    must(root.is_dir() and not root.is_symlink(),
         "Protected B06 independent audit ledger missing")
    claim = root / AUDIT_DIR
    claim.mkdir(mode=0o700, exist_ok=False)
    _write_once(claim / "00-intent.json", {
        "schema": AUDIT_SCHEMA, "case_id": "B06",
        "source_story_sha256": STORY_SHA, "spine_sha256": SPINE_SHA,
        "exact_request_sha256": hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_quality_model_posts": 1,
        "stage_maximum_reported_usd": format(STAGE_COST_CAP, "f"),
        "prior_conservative_reserved_usd": format(PRIOR_RESERVED, "f"),
        "aggregate_user_approved_usd": format(USER_CAP, "f"),
        "automatic_retry": False, "production_state_write_authorized": False,
    })
    response = None
    try:
        response = transport(body)
        record = verify_auditor_reply(source, response)
        must(record["case_id"] == "B06"
             and record["source_pack_sha256"] == SOURCE_SHA
             and record["story_sha256"] == STORY_SHA
             and record["spine_sha256"] == SPINE_SHA
             and record["original_spine_generation_id"] == SPINE_ID
             and record["full_original_v21_final_audit_completed"] is False
             and record["english_master_authorized"] is False
             and record["q25_authorized"] is False
             and record["state_write_authorized"] is False,
             "B06 initial QA must never authorize downstream writes")
        _write_once(claim / "01-audit-outcome.json", record)
        return record
    except Exception as exc:
        if not (claim / "01-audit-outcome.json").exists():
            outcome = sanitized_failure_receipt(
                exc, response, case_id="B06", story_sha256=STORY_SHA
            )
            outcome["schema"] = AUDIT_SCHEMA
            _write_once(claim / "01-audit-outcome.json", outcome)
        raise HarnessStop("B06 quality audit consumed without retries") from None

def status():
    return {
        "schema": SCHEMA, "case_id": "B06",
        "source_pack_sha256": SOURCE_SHA,
        "spine_sha256": SPINE_SHA, "story_sha256": STORY_SHA,
        "reader_age": 12, "real_generation_cost_usd": format(GEN_COST, "f"),
        "prior_conservative_budget_reserved_usd": format(PRIOR_RESERVED, "f"),
        "new_quality_maximum_usd": format(STAGE_COST_CAP, "f"),
        "maximum_new_model_posts": 1,
        "provider_calls": 0, "initial_quality_accepted": False,
        "production_state_write_authorized": False,
    }

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--paid-audit-once", action="store_true")
    args = p.parse_args()
    if not args.paid_audit_once:
        print(json.dumps(status(), sort_keys=True))
        return
    must(os.getenv("LUMI_P449_B06_QA") == "ONE_REAL_INDEPENDENT_B06_SONNET_QUALITY",
         "B06 real QA requires an exact reviewed one-use grant")
    must(args.producer_root and args.quality_root,
         "Missing original protected B06 generation/QA claim directories")
    key = os.getenv("OPENROUTER_API_KEY", "")
    must(type(key) is str and key.startswith("sk-or-"),
         "Original OpenRouter inference key not configured")
    source = get_original_B06(args.repo_root, args.producer_root)
    result = audit_B06_once(source, args.quality_root,
                            transport=lambda body: https_post_once(key, body))
    print(json.dumps({
        "schema": SCHEMA, "case_id": "B06",
        "story_sha256": result["story_sha256"],
        "initial_quality_verdict": result["quality_initial_verdict"],
        "reader_score": result["reader_score"],
        "blockers": len(result["blocking_findings"]),
        "auditor_generation_id": result["auditor_generation_id"],
        "provider_quality_cost_usd": result["auditor_reported_cost_usd"],
        "english_master_authorized": False,
        "q25_authorized": False,
        "production_state_write_authorized": False,
    }, sort_keys=True))

if __name__ == "__main__":
    main()
