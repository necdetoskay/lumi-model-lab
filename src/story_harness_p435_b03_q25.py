"""P4.35 — B03-only one-shot real Q25 evidence proposal (never Canon commit).

Adapts the original P4.24 source-quote-bound validator for B03 river/village
Canon. Requires genuine P4.33 ACCEPT and the immutable P4.34 pilot Master.
All entry points default to zero model calls; a separate reviewed grant is
required for a single inference POST. No retry, fallback or production writes.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p424_q25_evidence import (
    extraction_wire, verify_model_response, SAFE_FAILURE_CODE, COST_CAP, MODEL,
    money,
)
from src.story_harness_p432_b03_quality import (
    get_original_B03, SOURCE_SHA, SPINE_SHA, STORY_SHA,
)
from src.story_harness_p434_b03_master import (
    load_b03_quality, MASTER_DIR, AUDIT_RECEIPT_SHA256,
)
from src.story_harness_p423_master import qualify_master
from src.story_harness_p417_live_pilot import https_post_once
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p435-b03-evidence-proposal.v1"
RUN_NAME = "p435-b03-r06-q25-evidence-v01"
PREVIOUS_RESERVED_USD = Decimal("1.489558")
USER_CAP_USD = Decimal("10.00")

def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def load_b03_bundle(repo_root, producer_root, quality_root, master_root):
    source = get_original_B03(repo_root, producer_root)
    audit = load_b03_quality(repo_root, quality_root)
    accepted = qualify_master(source, audit)
    root = Path(master_root)
    folder = root / MASTER_DIR
    must(root.is_dir() and folder.is_dir()
         and not root.is_symlink() and not folder.is_symlink(),
         "Original B03 protected pilot English Master missing")
    manifest_path, prose_path = folder / "master-manifest.json", folder / "ENGLISH_MASTER.txt"
    must(manifest_path.is_file() and prose_path.is_file()
         and not manifest_path.is_symlink() and not prose_path.is_symlink()
         and manifest_path.stat().st_size < 64000 and prose_path.stat().st_size < 150000,
         "B03 Master evidence unreadable or mutable")
    manifest = json.loads(manifest_path.read_bytes())
    raw = prose_path.read_bytes()
    must(manifest.get("schema") == "lumi.story-harness-p423-pilot-english-master.v1"
         and manifest.get("artifact_type") == "PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER"
         and manifest.get("case_id") == "B03"
         and manifest.get("source_pack_sha256") == SOURCE_SHA
         and manifest.get("approved_spine_sha256") == SPINE_SHA
         and manifest.get("source_story_sha256") == STORY_SHA
         and manifest.get("accepted_story_sha256") == STORY_SHA
         and manifest.get("original_quality_receipt_sha256") == AUDIT_RECEIPT_SHA256
         and manifest.get("independent_auditor_generation_id") == accepted["auditor_generation_id"]
         and manifest.get("independent_initial_audit_verdict") == "ACCEPT"
         and manifest.get("reader_score") == 4
         and manifest.get("audit_cost_usd") == "0.027522"
         and manifest.get("english_master_word_count") == 1300
         and manifest.get("manual_text_edits") == 0
         and manifest.get("q25_read_only_extraction_allowed") is True
         and manifest.get("production_master_published") is False
         and manifest.get("production_state_write_authorized") is False
         and manifest.get("full_original_frozen_v21_4_production_quality_accepted") is False,
         "B03 Master not genuinely promoted from same-source P4.33")
    must(hashlib.sha256(raw).hexdigest() == STORY_SHA
         and raw.decode("utf-8") == source["story"]["story_text"],
         "B03 Master prose was changed after initial ACCEPT")
    must(PREVIOUS_RESERVED_USD + COST_CAP <= USER_CAP_USD,
         "B03 real Q25 would exceed approved $10 aggregate budget")
    return {"source": source, "audit": audit, "master": manifest,
            "english_master_text": raw.decode("utf-8")}

def b03_q25_wire(bundle):
    must(bundle["source"].get("case_id") == "B03", "Cross-story B03 Q25 denied")
    wire = extraction_wire(bundle)
    system = wire["messages"][0]["content"]
    must(wire["response_format"]["json_schema"]["name"] ==
         "lumi_b03_q25_evidence_proposal_v1"
         and "AT_RIVERBANK" in system and "AT_VILLAGE" in system
         and "AT_HOME" not in system and "AT_MEADOW" not in system
         and json.loads(wire["messages"][1]["content"])["case_id"] == "B03",
         "B03 Q25 spatial grammar/source not taken from original Canon")
    wire["messages"][0]["content"] += (
        " In this exact B03 story Duru finishes in VILLAGE, not RIVERBANK; "
        "support final VILLAGE with a verbatim late-story quotation mentioning "
        "the village square. Use an actual earlier village discovery quote. "
        "Do not assert that Duru returned across the river, or that the "
        "key's observed holder necessarily has legal ownership."
    )
    must(len(canonical_json(wire)) < 24000, "B03 Q25 request too large")
    return wire

def verify_b03_q25_response(bundle, response):
    result = verify_model_response(bundle, response)
    evidence = result["evidence_proposal"]
    final = evidence["final_location"]
    discoveries = evidence["discovered_locations"]
    must(result.get("case_id") == "B03"
         and result.get("source_pack_sha256") == SOURCE_SHA
         and result.get("story_sha256") == STORY_SHA
         and result.get("spine_sha256") == SPINE_SHA
         and result.get("production_state_write_authorized") is False
         and result.get("semantic_state_fully_certified") is False
         and result.get("final_story_state_committed") is False,
         "B03 Q25 not source-bounded, read-only evidence")
    must(final["location_id"] == "VILLAGE"
         and "square" in final["quote"].lower()
         and len([d for d in discoveries if d["location_id"] == "VILLAGE"]) == 1
         and any(x in discoveries[0]["quote"].lower()
                 for x in ("village", "square")),
         "B03 final or discovered village not unambiguously quote-grounded")
    result["schema"] = SCHEMA
    return result

def write_once(path, payload):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical_json(payload) + b"\n")
        f.flush()
        os.fsync(f.fileno())

def q25_once(bundle, claim_root, *, transport):
    root = Path(claim_root)
    must(root.is_dir() and not root.is_symlink(), "Missing protected B03 Q25 ledger")
    body = b03_q25_wire(bundle)
    folder = root / RUN_NAME
    folder.mkdir(mode=0o700, exist_ok=False)
    write_once(folder / "00-intent.json", {
        "schema": SCHEMA, "case_id": "B03",
        "source_pack_sha256": SOURCE_SHA,
        "story_sha256": STORY_SHA, "spine_sha256": SPINE_SHA,
        "request_sha256": hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_model_posts": 1,
        "stage_cost_cap_usd": format(COST_CAP, "f"),
        "prior_conservative_budget_reserved_usd": format(PREVIOUS_RESERVED_USD, "f"),
        "user_total_cap_usd": format(USER_CAP_USD, "f"),
        "automatic_retry": False, "production_state_write_authorized": False,
    })
    response = None
    try:
        response = transport(body)
        record = verify_b03_q25_response(bundle, response)
        write_once(folder / "01-q25-evidence.json", record)
        return record
    except Exception as exc:
        usage = response.get("usage") if type(response) is dict else None
        charge = None
        if type(usage) is dict:
            try:
                charge = money(usage.get("cost"))
            except HarnessStop:
                pass
        generation = response.get("id") if type(response) is dict else None
        if not (type(generation) is str
                and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}", generation)):
            generation = None
        reason = (SAFE_FAILURE_CODE.get(str(exc), "B03_Q25_SOURCE_OR_CONTRACT_REJECT")
                  if isinstance(exc, HarnessStop) else "B03_Q25_PROVIDER_OR_UNKNOWN")
        if not (folder / "01-q25-evidence.json").exists():
            write_once(folder / "01-q25-evidence.json", {
                "schema": SCHEMA, "case_id": "B03",
                "status": "STOP_UNKNOWN_OR_INVALID",
                "safe_failure_code": reason,
                "provider_generation_id": generation,
                "provider_reported_cost_usd": format(charge, "f") if charge is not None else None,
                "source_story_sha256": STORY_SHA,
                "model_post_attempt_consumed": True,
                "automatic_retry": False,
                "production_state_write_authorized": False,
            })
        raise HarnessStop("B03 Q25 consumed; no retry; reason=" + reason) from None

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--paid-once", action="store_true")
    args = p.parse_args()
    if not args.paid_once:
        print(json.dumps({"case_id": "B03", "schema": SCHEMA, "model_calls": 0,
                          "stage_cap_usd": "0.050",
                          "production_state_write_authorized": False}, sort_keys=True))
        return
    must(os.getenv("LUMI_P435_Q25_B03") == "ONE_REVIEWED_B03_MASTER_Q25",
         "No separate reviewed B03 Q25 single-use grant")
    must(all((args.producer_root, args.quality_root, args.master_root, args.q25_root)),
         "Original B03 protected source chain missing")
    key = os.getenv("OPENROUTER_API_KEY", "")
    must(type(key) is str and key.startswith("sk-or-"), "No approved OpenRouter inference key")
    bundle = load_b03_bundle(args.repo_root, args.producer_root, args.quality_root, args.master_root)
    receipt = q25_once(bundle, args.q25_root, transport=lambda body: https_post_once(key, body))
    print(json.dumps({"case_id": "B03", "schema": SCHEMA,
                      "story_sha256": receipt["story_sha256"],
                      "final_location_proposal": receipt["evidence_proposal"]["final_location"]["location_id"],
                      "provider_reported_cost_usd": receipt["provider_reported_cost_usd"],
                      "q25_generation_id": receipt["generation_id"],
                      "state_committed": False,
                      "production_state_write_authorized": False}, sort_keys=True))

if __name__ == "__main__":
    main()
