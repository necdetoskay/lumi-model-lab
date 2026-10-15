"""P4.40: original B04 independent ACCEPT -> immutable PILOT English Master.

No model calls and no original prose edits. Source and auditor receipts must
match both protected runner originals and committed frozen evidence bytes.
A repeated CI run only verifies the previously sealed output, never rewrites.
"""
from __future__ import annotations
from decimal import Decimal
from pathlib import Path
import hashlib
import json

from src.story_harness_p410 import canonical_json
from src.story_harness_p423_master import SCHEMA, qualify_master, write_exclusive
from src.story_harness_p439_b04_quality import (
    get_original_B04, SOURCE_SHA, SPINE_SHA, STORY_SHA, AUDIT_DIR
)
from src.story_harness_v1 import HarnessStop

AUDIT_PATH = "evidence/story_harness_p439/b04-r06-original-independent-quality-accept.json"
AUDIT_SHA = "a180ce649af3d6593343689c4aa23ca81df3b3f2568df9e8f42f96fe570c3245"
AUDITOR_ID = "gen-1791965588-E4mEjrm7iNORBdKq4sHA"
MASTER_DIR = "b04-" + STORY_SHA[:16]
SOURCE_FILES = {
    "spine-plan.json": "b04-r06-original-spine-plan.json",
    "story-draft.json": "b04-r06-original-writer-draft.json",
    "01-spineforge-receipt.json": "b04-r06-original-spineforge-receipt.json",
    "02-writer-receipt.json": "b04-r06-original-writer-receipt.json",
}

def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def load_b04_quality(repo_root, quality_root):
    root = Path(quality_root)
    claim = root / AUDIT_DIR
    must(root.is_dir() and not root.is_symlink()
         and claim.is_dir() and not claim.is_symlink(),
         "B04 immutable P4.39 audit claim missing")
    original = claim / "01-audit-outcome.json"
    saved = Path(repo_root) / AUDIT_PATH
    must(original.is_file() and saved.is_file()
         and not original.is_symlink() and not saved.is_symlink()
         and original.stat().st_size < 64000,
         "Original B04 audit file missing or unsafe")
    raw = original.read_bytes()
    must(hashlib.sha256(raw).hexdigest() == AUDIT_SHA
         and raw == saved.read_bytes(),
         "B04 audit not byte-for-byte original provider receipt")
    audit = json.loads(raw)
    must(audit.get("case_id") == "B04"
         and audit.get("source_pack_sha256") == SOURCE_SHA
         and audit.get("spine_sha256") == SPINE_SHA
         and audit.get("story_sha256") == STORY_SHA
         and audit.get("auditor_generation_id") == AUDITOR_ID
         and audit.get("quality_initial_verdict") == "ACCEPT"
         and audit.get("quality_initial_audit_accepted") is True
         and audit.get("reader_score") == 4
         and audit.get("blocking_findings") == []
         and Decimal(str(audit.get("auditor_reported_cost_usd"))) == Decimal("0.02468")
         and audit.get("english_master_authorized") is False
         and audit.get("q25_authorized") is False
         and audit.get("state_write_authorized") is False
         and audit.get("full_original_v21_final_audit_completed") is False,
         "B04 initial independent ACCEPT admission failed")
    return audit

def original_b04(repo_root, producer_root):
    source = get_original_B04(repo_root, producer_root)
    claim = Path(producer_root) / source["original_claim_id"]
    root = Path(repo_root) / "evidence/story_harness_p438"
    for name, frozen in SOURCE_FILES.items():
        original = claim / name
        saved = root / frozen
        must(original.is_file() and saved.is_file()
             and not original.is_symlink() and not saved.is_symlink()
             and original.read_bytes() == saved.read_bytes(),
             "B04 true original SpineForge/Writer/provider bytes missing or changed")
    return source

def manifest_for(source, audit):
    must(source.get("case_id") == "B04"
         and source["pack"]["pack_sha256"] == SOURCE_SHA
         and source["spine"]["spine_sha256"] == SPINE_SHA
         and source["story"]["story_sha256"] == STORY_SHA,
         "B04 Master cannot cross-source")
    must(audit.get("case_id") == "B04"
         and audit.get("auditor_generation_id") == AUDITOR_ID
         and audit.get("source_pack_sha256") == SOURCE_SHA
         and audit.get("spine_sha256") == SPINE_SHA
         and audit.get("story_sha256") == STORY_SHA
         and audit.get("full_original_v21_final_audit_completed") is False,
         "B04 Master auditor identity/lineage mismatch")
    qualified = qualify_master(source, audit)
    raw = source["story"]["story_text"].encode("utf-8")
    must(len(source["story"]["story_text"].split()) == 1277
         and hashlib.sha256(raw).hexdigest() == STORY_SHA,
         "B04 1277-word Writer changed")
    manifest = {
        "schema": SCHEMA,
        "artifact_type": "PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER",
        "case_id": "B04",
        "source_pack_sha256": SOURCE_SHA,
        "source_writer_model": "anthropic/claude-sonnet-5.5",
        "source_story_sha256": STORY_SHA,
        "accepted_story_sha256": STORY_SHA,
        "approved_spine_sha256": SPINE_SHA,
        "independent_auditor_generation_id": qualified["auditor_generation_id"],
        "independent_initial_audit_verdict": "ACCEPT",
        "reader_score": qualified["reader_score"],
        "audit_cost_usd": qualified["audit_cost_usd"],
        "original_quality_receipt_sha256": AUDIT_SHA,
        "english_master_word_count": 1277,
        "text_path": "ENGLISH_MASTER.txt",
        "manual_text_edits": 0,
        "q25_read_only_extraction_allowed": True,
        "full_original_frozen_v21_4_production_quality_accepted": False,
        "production_master_published": False,
        "production_state_write_authorized": False,
    }
    return raw, manifest

def seal_or_verify(source, audit, master_root):
    root = Path(master_root)
    must(root.is_dir() and not root.is_symlink(), "B04 protected Master root missing")
    raw, manifest = manifest_for(source, audit)
    folder = root / MASTER_DIR
    if folder.exists():
        must(folder.is_dir() and not folder.is_symlink(),
             "B04 Master folder unsafe")
        prose, metadata = folder / "ENGLISH_MASTER.txt", folder / "master-manifest.json"
        must(prose.is_file() and metadata.is_file()
             and not prose.is_symlink() and not metadata.is_symlink()
             and prose.read_bytes() == raw
             and metadata.read_bytes() == canonical_json(manifest) + b"\n",
             "Previously sealed B04 Master bytes differ; no overwrite allowed")
        return manifest, False
    folder.mkdir(mode=0o700, exist_ok=False)
    write_exclusive(folder / "ENGLISH_MASTER.txt", raw)
    write_exclusive(folder / "master-manifest.json", canonical_json(manifest) + b"\n")
    return manifest, True

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--seal-or-verify", action="store_true")
    a=p.parse_args()
    if not a.seal_or_verify:
        print(json.dumps({"case_id":"B04","model_calls":0,
                          "master_sealed":False,"production_state_write_authorized":False}))
        return
    must(a.producer_root and a.quality_root and a.master_root,
         "B04 original producer, auditor and Master roots required")
    source=original_b04(a.repo_root,a.producer_root)
    audit=load_b04_quality(a.repo_root,a.quality_root)
    result,created=seal_or_verify(source,audit,a.master_root)
    print(json.dumps({"case_id":"B04","story_sha256":result["accepted_story_sha256"],
                      "word_count":result["english_master_word_count"],
                      "independent_auditor_id":result["independent_auditor_generation_id"],
                      "master_sealed":True,"created_this_run":created,"model_calls":0,
                      "production_state_write_authorized":False},sort_keys=True))
if __name__=="__main__":
    main()
