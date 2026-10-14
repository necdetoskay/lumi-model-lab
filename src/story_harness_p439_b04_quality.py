"""P4.39: independent real 12-family initial quality for original B04.

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
from src.story_harness_p438_b04_age10 import source_case, SOURCE_SHA
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p439-b04-independent-age10-quality.v1"
SPINE_SHA = "af7e8520ba8f06a24906dfffe02cd32d39ff75ff4727f3d3c5e450d515bfa236"
STORY_SHA = "1648b29b47a830cb7c524e3264f6171ac750a390665207e8453f434d36413557"
SPINE_ID = "gen-1791964646-Ji5krc5hQOiyGfz89qKM"
WRITER_ID = "gen-1791964669-IWfJ0pbhobSncWHBgDBZ"
GEN_COST = Decimal("0.059076")
PRIOR_RESERVED = Decimal("1.889558")
USER_CAP = Decimal("10.00")
CLAIM_NAME = "b04-" + SOURCE_SHA[:16] + "-r06"
AUDIT_DIR = "p439-b04-r06-" + STORY_SHA[:12]
PROVIDER_FILE_DIGESTS = {
    "spine-plan.json": "a178dec5cebe3becdb23a54e580f4587a88f0805602a761adab411f59d317671",
    "story-draft.json": "da4b6a14cf112b0782e8b16f5647649214181850e0b143aca9daaec2f82a3c16",
    "01-spineforge-receipt.json": "aba3e1341d9c230e7fbfad8319bdac95b3b5a8347a82c2df3dcc3d3f015d3c0f",
    "02-writer-receipt.json": "301ca36f309871aad40dbf46a10e5c10a1a244db9cbab8a93f0d83602afbd300",
}

def must(condition, reason):
    if not condition:
        raise HarnessStop(reason)

def _original_json(folder, filename):
    path = folder / filename
    must(path.is_file() and not path.is_symlink()
         and 0 < path.stat().st_size < 200000, "Missing bounded original B04 provider file")
    raw = path.read_bytes()
    must(hashlib.sha256(raw).hexdigest() == PROVIDER_FILE_DIGESTS[filename],
         "B04 provider artifact digest differs from original successful CI archive")
    return json.loads(raw)

def get_original_B04(repo_root, producer_root):
    _, pack = source_case(repo_root)
    root = Path(producer_root)
    must(root.is_dir() and not root.is_symlink(), "Protected B04 generation claim root missing")
    claims = list(root.glob("b04-*-r06"))
    must(len(claims) == 1 and claims[0].name == CLAIM_NAME
         and claims[0].is_dir() and not claims[0].is_symlink(),
         "Missing/non-unique or wrong B04 source claim")
    folder = claims[0]
    spine = _original_json(folder, "spine-plan.json")
    story = _original_json(folder, "story-draft.json")
    first = _original_json(folder, "01-spineforge-receipt.json")
    second = _original_json(folder, "02-writer-receipt.json")
    must(spine.get("case_id") == "B04"
         and spine.get("schema") == "lumi.story-harness-p421-real-spine-artifact.v1"
         and spine.get("source_pack_sha256") == SOURCE_SHA
         and spine.get("spine_sha256") == SPINE_SHA
         and spine.get("spine_sha256") == sha(spine["spine"])
         and spine.get("provider_generation_id") == SPINE_ID
         and spine.get("original_semantic_quality_accepted") is False,
         "B04 original Spine or provider signature differs")
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
         and story.get("word_count") == 1277
         and isinstance(story.get("story_text"), str)
         and len(story["story_text"].split()) == 1277
         and hashlib.sha256(story["story_text"].encode("utf-8")).hexdigest() == STORY_SHA
         and story.get("story_sha256") == STORY_SHA,
         "B04 Writer source, word count or exact manuscript altered")
    paid = []
    for label, receipt, genid in (("SPINEFORGE", first, SPINE_ID),
                                  ("WRITER", second, WRITER_ID)):
        must(receipt.get("schema") == "lumi.story-harness-p417-real-provider-pilot.v1"
             and receipt.get("stage") == label
             and receipt.get("outcome") == "SETTLED"
             and receipt.get("retry_authorized") is False
             and receipt.get("provider_generation_id") == genid
             and isinstance(receipt.get("provider_usage"), dict),
             "B04 original model receipt not truly settled")
        charge = money(receipt.get("provider_reported_cost_usd"))
        must(0 < charge <= STAGE_MAX_USD[label],
             "B04 stage exceeded proven provider cost cap")
        paid.append(charge)
    must(paid == [Decimal("0.026102"), Decimal("0.032974")]
         and sum(paid) == GEN_COST == money(story["total_reported_usd"])
         and sum(paid) <= USD_CAP,
         "B04 actual provider cost reconciliation failed")
    must(PRIOR_RESERVED + STAGE_COST_CAP <= USER_CAP <= GLOBAL_USER_CAP,
         "B04 quality would exceed overall $10 user limit")
    return {
        "pack": pack, "spine": spine, "story": story,
        "case_id": "B04", "run_variant": "r06",
        "generation_cost_usd": format(GEN_COST, "f"),
        "original_claim_id": folder.name,
    }

def inspect_B04_audit(source):
    must(source.get("case_id") == "B04"
         and source["story"]["story_sha256"] == STORY_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["pack"]["reader_age"] == 10,
         "B04 independent QA cannot inherit any other story acceptance")
    body = audit_wire(source)
    payload = json.loads(body["messages"][1]["content"])
    must(payload["case_id"] == "B04"
         and payload["reader_age"] == 10
         and payload["story_sha256"] == STORY_SHA
         and payload["approved_spine_sha256"] == SPINE_SHA
         and body["model"] == MODEL
         and body["provider"]["allow_fallbacks"] is False
         and body["response_format"]["json_schema"]["name"] ==
             "lumi_b04_independent_initial_audit_v1"
         and "10 years old" in body["messages"][0]["content"],
         "B04 audit not independent, age-specific or source-bound")
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

def audit_B04_once(source, quality_root, *, transport):
    body = inspect_B04_audit(source)
    root = Path(quality_root)
    must(root.is_dir() and not root.is_symlink(),
         "Protected B04 independent audit ledger missing")
    claim = root / AUDIT_DIR
    claim.mkdir(mode=0o700, exist_ok=False)
    _write_once(claim / "00-intent.json", {
        "schema": AUDIT_SCHEMA, "case_id": "B04",
        "source_story_sha256": STORY_SHA, "spine_sha256": SPINE_SHA,
        "exact_request_sha256": hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_quality_model_posts": 1,
        "stage_maximum_reported_usd": format(STAGE_COST_CAP, "f"),
        "prior_conservative_reserved_usd": format(PRIOR_RESERVED, "f"),
        "aggregate_user_approved_usd": format(USER_CAP, "f"),
        "automatic_retry": False, "production_state_write_authorized": False,
    })
    try:
        record = verify_auditor_reply(source, transport(body))
        must(record["case_id"] == "B04"
             and record["source_pack_sha256"] == SOURCE_SHA
             and record["story_sha256"] == STORY_SHA
             and record["spine_sha256"] == SPINE_SHA
             and record["original_spine_generation_id"] == SPINE_ID
             and record["full_original_v21_final_audit_completed"] is False
             and record["english_master_authorized"] is False
             and record["q25_authorized"] is False
             and record["state_write_authorized"] is False,
             "B04 initial QA must never authorize downstream writes")
        _write_once(claim / "01-audit-outcome.json", record)
        return record
    except Exception:
        if not (claim / "01-audit-outcome.json").exists():
            _write_once(claim / "01-audit-outcome.json", {
                "schema": AUDIT_SCHEMA, "case_id": "B04",
                "source_story_sha256": STORY_SHA,
                "quality_initial_verdict": "STOP_UNKNOWN_OR_INVALID",
                "auditor_reported_cost_usd": None,
                "english_master_authorized": False,
                "retry_allowed": False,
                "production_state_write_authorized": False,
            })
        raise HarnessStop("B04 quality audit consumed without retries") from None

def status():
    return {
        "schema": SCHEMA, "case_id": "B04",
        "source_pack_sha256": SOURCE_SHA,
        "spine_sha256": SPINE_SHA, "story_sha256": STORY_SHA,
        "reader_age": 10, "real_generation_cost_usd": format(GEN_COST, "f"),
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
    must(os.getenv("LUMI_P439_B04_QA") == "ONE_REAL_INDEPENDENT_B04_SONNET_QUALITY",
         "B04 real QA requires an exact reviewed one-use grant")
    must(args.producer_root and args.quality_root,
         "Missing original protected B04 generation/QA claim directories")
    key = os.getenv("OPENROUTER_API_KEY", "")
    must(type(key) is str and key.startswith("sk-or-"),
         "Original OpenRouter inference key not configured")
    source = get_original_B04(args.repo_root, args.producer_root)
    result = audit_B04_once(source, args.quality_root,
                            transport=lambda body: https_post_once(key, body))
    print(json.dumps({
        "schema": SCHEMA, "case_id": "B04",
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
