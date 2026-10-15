"""P4.36 — Original B03 real Q25 -> immutable read-only Final StoryState draft.

Replay original protected Spine/Writer/P4.33 ACCEPT/Master/P4.35 Sonnet Q25
using exact GitHub-frozen receipts. Re-verify every Q25 quote against
the accepted prose, preserve unknown facts, and retain OPEN river rule.
Absolutely no model calls, Canon mutation, final semantic certification or
production writes.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import sha
from src.story_harness_p424_q25_evidence import verify_candidate, COST_CAP
from src.story_harness_p435_b03_q25 import (
    load_b03_bundle, SCHEMA as Q25_SCHEMA, RUN_NAME as Q25_RUN_NAME,
    MODEL, SOURCE_SHA, SPINE_SHA, STORY_SHA,
)
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p436-b03-read-only-final-state-draft.v1"
Q25_REFERENCE = "evidence/story_harness_p435/b03-r06-original-q25-evidence.json"
Q25_RECEIPT_SHA = "dc6145aba4c714fb2d706dfd0639f524571fede4b58409be0d181f432641322c"
OUTPUT_DIR = "p436-b03-r06-" + STORY_SHA[:12]

def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def load_original_q25(repo_root, q25_root):
    root = Path(q25_root)
    must(root.is_dir() and not root.is_symlink(), "Original B03 protected Q25 root missing")
    folder = root / Q25_RUN_NAME
    must(folder.is_dir() and not folder.is_symlink(), "B03 original Q25 run missing")
    original = folder / "01-q25-evidence.json"
    frozen = Path(repo_root) / Q25_REFERENCE
    must(original.is_file() and frozen.is_file()
         and not original.is_symlink() and not frozen.is_symlink()
         and original.stat().st_size < 65000,
         "Missing original and frozen B03 Q25 evidence")
    raw = original.read_bytes()
    must(raw == frozen.read_bytes()
         and hashlib.sha256(raw).hexdigest() == Q25_RECEIPT_SHA,
         "Original B03 Q25 bytes differ from verified provider artifact")
    return json.loads(raw)

def qualify_q25(bundle, receipt):
    source = bundle["source"]
    must(source.get("case_id") == "B03"
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA
         and source["story"]["story_sha256"] == STORY_SHA
         and bundle["master"]["accepted_story_sha256"] == STORY_SHA,
         "B03 final-state source and English Master mismatch")
    must(type(receipt) is dict and receipt.get("schema") == Q25_SCHEMA
         and receipt.get("case_id") == "B03"
         and receipt.get("model") == MODEL
         and receipt.get("generation_id") == "gen-1791962013-EUhZDIwF6TSPzFoV4B9S"
         and receipt.get("source_pack_sha256") == SOURCE_SHA
         and receipt.get("spine_sha256") == SPINE_SHA
         and receipt.get("story_sha256") == STORY_SHA
         and receipt.get("provenance_verified") is True
         and receipt.get("quote_matching_verified") is True
         and receipt.get("prior_english_master_unchanged") is True
         and receipt.get("semantic_state_fully_certified") is False
         and receipt.get("final_story_state_committed") is False
         and receipt.get("production_state_write_authorized") is False,
         "B03 Q25 must be real, quote-grounded and read-only")
    cost = Decimal(str(receipt.get("provider_reported_cost_usd")))
    must(cost.is_finite() and cost == Decimal("0.031366")
         and Decimal("0") < cost <= COST_CAP,
         "Original B03 provider cost not reconciled to Q25 cap")
    usage = receipt.get("provider_usage")
    must(type(usage) is dict
         and usage.get("prompt_tokens") == 5383
         and usage.get("completion_tokens") == 2060,
         "Original B03 Q25 provider usage changed")
    proposed = receipt.get("evidence_proposal")
    must(type(proposed) is dict, "Original B03 Q25 proposal missing")
    verified = verify_candidate(bundle, {
        "source_pack_sha256": SOURCE_SHA,
        "spine_sha256": SPINE_SHA,
        "story_sha256": STORY_SHA,
        "evidence_json": json.dumps(proposed, ensure_ascii=False),
        "explanation": "Independent deterministic revalidation of real B03 Q25 quotations and Canon obligations.",
    })
    must(verified["final_location"]["location_id"] == "VILLAGE"
         and [x["location_id"] for x in verified["discovered_locations"]] == ["VILLAGE"]
         and [(x["object_name"], x["last_seen_relation"], x["ownership"])
              for x in verified["object_observations"]] == [
                  ("key", "AT_VILLAGE", "UNKNOWN"),
                  ("chest", "AT_VILLAGE", "UNKNOWN"),
                  ("sweet bread", "HELD_BY_PROTAGONIST", "UNKNOWN"),
              ],
         "B03 Q25 physical objects or village evidence unexpectedly changed")
    must([x["status"] for x in verified["open_obligation_outcomes"]] ==
         ["OPEN", "SATISFIED"],
         "B03 single-crossing obligation must remain OPEN")
    return verified, format(cost, "f")

def project_b03_final_state(bundle, receipt):
    evidence, cost = qualify_q25(bundle, receipt)
    canon = deepcopy(bundle["source"]["pack"]["canonical_state"])
    before = list(canon["protagonist"]["known_locations"])
    newly_known = [x["location_id"] for x in evidence["discovered_locations"]]
    known = before + [loc for loc in newly_known if loc not in before]
    must(known == ["RIVERBANK", "VILLAGE"]
         and canon["protagonist"]["location"] == "RIVERBANK"
         and evidence["final_location"]["location_id"] == "VILLAGE",
         "B03 quoted final location or initial Canon inconsistent")
    draft = {
        "schema": SCHEMA,
        "case_id": "B03",
        "artifact_classification": "READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON",
        "source_pack_sha256": SOURCE_SHA,
        "original_spine_sha256": SPINE_SHA,
        "english_master_sha256": STORY_SHA,
        "original_q25_receipt_sha256": Q25_RECEIPT_SHA,
        "canonical_start_snapshot_sha256": sha(canon),
        "original_protagonist_name": canon["protagonist"]["name"],
        "original_q25_generation_id": receipt["generation_id"],
        "original_q25_reported_cost_usd": cost,
        "last_protagonist_location_proposal": deepcopy(evidence["final_location"]),
        "new_discoveries_with_evidence": deepcopy(evidence["discovered_locations"]),
        "known_locations_proposal": known,
        "objects_not_admitted_to_canon": deepcopy(evidence["object_observations"]),
        "original_canonical_objects_unchanged": deepcopy(canon["objects"]),
        "original_open_obligations_unchanged": deepcopy(canon["open_obligations"]),
        "open_obligation_outcomes_unapproved": deepcopy(evidence["open_obligation_outcomes"]),
        "unknown_facts_retained": deepcopy(evidence["unknown_facts_retained"]),
        "world_time_initial_snapshot": canon["world_time"],
        "world_time_final": None,
        "world_time_status": "UNKNOWN_DELTA_NOT_COMMITTED",
        "independent_final_state_semantic_certification": False,
        "original_full_frozen_v21_4_final_quality_verified": False,
        "canon_commit_authorized": False,
        "production_change": False,
        "model_posts_for_projection": 0,
        "manual_story_prose_edits": 0,
    }
    must(draft["unknown_facts_retained"] == canon["unknown_facts"]
         and draft["original_open_obligations_unchanged"] == canon["open_obligations"]
         and all(x["ownership"] == "UNKNOWN" for x in draft["objects_not_admitted_to_canon"])
         and draft["world_time_final"] is None,
         "B03 final state attempted unproven owner, obligation or time mutation")
    return draft

def freeze_b03_state(bundle, receipt, final_root):
    root = Path(final_root)
    must(root.is_dir() and not root.is_symlink(),
         "Protected final-state draft directory missing")
    proposed = project_b03_final_state(bundle, receipt)
    folder = root / OUTPUT_DIR
    folder.mkdir(mode=0o700, exist_ok=False)
    path = folder / "final-state-draft.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical_json(proposed) + b"\n")
        f.flush()
        os.fsync(f.fileno())
    return proposed

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--final-root")
    p.add_argument("--freeze-once", action="store_true")
    a = p.parse_args()
    if not a.freeze_once:
        print(json.dumps({"schema": SCHEMA, "case_id": "B03",
                          "provider_calls": 0, "final_story_state_committed": False,
                          "production_state_write_authorized": False}, sort_keys=True))
        return
    must(all((a.producer_root, a.quality_root, a.master_root,
              a.q25_root, a.final_root)),
         "B03 source/quality/Master/Q25/final roots all required")
    bundle = load_b03_bundle(a.repo_root, a.producer_root, a.quality_root, a.master_root)
    receipt = load_original_q25(a.repo_root, a.q25_root)
    final = freeze_b03_state(bundle, receipt, a.final_root)
    print(json.dumps({
        "schema": SCHEMA,
        "case_id": "B03",
        "source_story_sha256": final["english_master_sha256"],
        "final_location_proposal": final["last_protagonist_location_proposal"]["location_id"],
        "discovered_locations": len(final["new_discoveries_with_evidence"]),
        "objects": len(final["objects_not_admitted_to_canon"]),
        "open_obligation_outcomes": [x["status"] for x in final["open_obligation_outcomes_unapproved"]],
        "world_time_final": None,
        "provider_calls": 0,
        "production_state_write_authorized": False,
    }, sort_keys=True))

if __name__ == "__main__":
    main()
