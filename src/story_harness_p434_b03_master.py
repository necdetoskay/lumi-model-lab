"""P4.34 — B03 source-sealed immutable PILOT English Master (zero model calls).

Requires the exact original r06 Sonnet SpineForge/Writer claim and the genuine
P4.33 independent ACCEPT receipt. Does not certify v21 final quality or write
production Canon. Existing B01/B02 paths are unchanged.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path

from src.story_harness_p410 import canonical_json
from src.story_harness_p423_master import SCHEMA, qualify_master, write_exclusive
from src.story_harness_p432_b03_quality import get_original_B03, SOURCE_SHA, SPINE_SHA, STORY_SHA
from src.story_harness_v1 import HarnessStop

AUDIT_PATH = "evidence/story_harness_p433/b03-r06-original-independent-quality-accept.json"
AUDIT_RECEIPT_SHA256 = "cbaa398028a373d2fbc398567148796e1ece75e87246aaff76ab685aef4dd552"
QUALITY_CLAIM = "p432-b03-r06-" + STORY_SHA[:12]
MASTER_DIR = "b03-" + STORY_SHA[:16]

def must(condition, reason):
    if not condition:
        raise HarnessStop(reason)

def load_b03_quality(repo_root, quality_claim_root):
    root = Path(quality_claim_root)
    must(root.is_dir() and not root.is_symlink(), "Protected B03 quality root missing")
    claim = root / QUALITY_CLAIM
    must(claim.is_dir() and not claim.is_symlink(), "Original B03 P4.33 quality claim missing")
    original = claim / "01-audit-outcome.json"
    saved = Path(repo_root) / AUDIT_PATH
    must(original.is_file() and saved.is_file()
         and not original.is_symlink() and not saved.is_symlink()
         and original.stat().st_size < 64000,
         "Missing original immutable B03 provider audit")
    raw = original.read_bytes()
    must(raw == saved.read_bytes()
         and hashlib.sha256(raw).hexdigest() == AUDIT_RECEIPT_SHA256,
         "B03 P4.33 audit differs from original GitHub Actions receipt")
    audit = json.loads(raw)
    must(audit.get("case_id") == "B03"
         and audit.get("source_pack_sha256") == SOURCE_SHA
         and audit.get("story_sha256") == STORY_SHA
         and audit.get("spine_sha256") == SPINE_SHA
         and audit.get("quality_initial_verdict") == "ACCEPT"
         and audit.get("quality_initial_audit_accepted") is True
         and audit.get("reader_score") == 4
         and audit.get("blocking_findings") == []
         and audit.get("auditor_generation_id") == "gen-1791956689-z15grh3ISk5XKZQt7NlY"
         and Decimal(str(audit.get("auditor_reported_cost_usd"))) == Decimal("0.027522")
         and audit.get("english_master_authorized") is False
         and audit.get("q25_authorized") is False
         and audit.get("state_write_authorized") is False
         and audit.get("full_original_v21_final_audit_completed") is False,
         "B03 original independent audit not a source-grounded initial ACCEPT")
    return audit

def seal_b03_once(source, audit, master_root):
    must(source.get("case_id") == "B03"
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["story"]["story_sha256"] == STORY_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA,
         "B03 Master source Canon/Spine/Writer mismatch")
    approved = qualify_master(source, audit)
    root = Path(master_root)
    must(root.is_dir() and not root.is_symlink(),
         "Protected B03 pilot Master root missing")
    original = source["story"]["story_text"].encode("utf-8")
    must(len(original.decode("utf-8").split()) == 1300
         and hashlib.sha256(original).hexdigest() == STORY_SHA,
         "B03 English source differs from original 1,300-word Writer artifact")
    folder = root / MASTER_DIR
    folder.mkdir(mode=0o700, exist_ok=False)
    write_exclusive(folder / "ENGLISH_MASTER.txt", original)
    result = {
        "schema": SCHEMA,
        "artifact_type": "PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER",
        "case_id": "B03",
        "source_pack_sha256": approved["source_pack_sha256"],
        "source_writer_model": "anthropic/claude-sonnet-5.5",
        "source_story_sha256": approved["story_sha256"],
        "accepted_story_sha256": hashlib.sha256(original).hexdigest(),
        "approved_spine_sha256": approved["spine_sha256"],
        "independent_auditor_generation_id": approved["auditor_generation_id"],
        "independent_initial_audit_verdict": "ACCEPT",
        "reader_score": approved["reader_score"],
        "audit_cost_usd": approved["audit_cost_usd"],
        "original_quality_receipt_sha256": AUDIT_RECEIPT_SHA256,
        "english_master_word_count": 1300,
        "text_path": "ENGLISH_MASTER.txt",
        "manual_text_edits": 0,
        "q25_read_only_extraction_allowed": True,
        "full_original_frozen_v21_4_production_quality_accepted": False,
        "production_master_published": False,
        "production_state_write_authorized": False,
    }
    write_exclusive(folder / "master-manifest.json", canonical_json(result) + b"\n")
    return result

def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--seal-pilot-once", action="store_true")
    a = p.parse_args()
    if not a.seal_pilot_once:
        print(json.dumps({"case_id": "B03", "model_posts": 0,
                          "english_master_sealed": False,
                          "production_state_write_authorized": False}, sort_keys=True))
        return
    must(a.producer_root and a.quality_root and a.master_root,
         "Cannot create Master without original protected claims")
    source = get_original_B03(a.repo_root, a.producer_root)
    audit = load_b03_quality(a.repo_root, a.quality_root)
    result = seal_b03_once(source, audit, a.master_root)
    print(json.dumps({"case_id": "B03", "story_sha256": result["source_story_sha256"],
                      "word_count": result["english_master_word_count"],
                      "reader_score": result["reader_score"],
                      "new_model_posts": 0,
                      "pilot_only": True,
                      "production_state_write_authorized": False}, sort_keys=True))

if __name__ == "__main__":
    main()
