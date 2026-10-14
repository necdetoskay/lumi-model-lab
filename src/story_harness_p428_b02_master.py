"""P4.28: seal B02 only as an immutable PILOT English Master, no model calls.

Requires B02's exact P4.27 real independent ACCEPT and the original
protected model response byte-identical to frozen repository evidence.
Does not modify the existing B01 English Master admission path.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from src.story_harness_p410 import canonical_json
from src.story_harness_p423_master import SCHEMA, qualify_master, write_exclusive
from src.story_harness_p427_b02_quality import get_b02_original,STORY_SHA,SPINE_SHA,SOURCE_SHA
from src.story_harness_v1 import HarnessStop

AUDIT_FILE="evidence/story_harness_p427/b02-r06-independent-quality-accept.json"
MASTER_DIR="b02-"+STORY_SHA[:16]


def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)


def load_b02_quality(repo_root,quality_root):
    folder=Path(quality_root)/("p427-b02-r06-"+STORY_SHA[:12])
    path=folder/"01-audit-outcome.json"
    saved=Path(repo_root)/AUDIT_FILE
    must(path.is_file() and saved.is_file()
         and not path.is_symlink() and not saved.is_symlink()
         and path.stat().st_size<=64000,
         "B02 actual independent quality evidence missing")
    must(path.read_bytes()==saved.read_bytes(),
         "Original B02 provider audit no longer byte-equal to GitHub evidence")
    a=json.loads(path.read_bytes())
    must(a.get("case_id")=="B02"
         and a.get("quality_initial_verdict")=="ACCEPT"
         and a.get("quality_initial_audit_accepted") is True
         and a.get("reader_score")==5
         and a.get("blocking_findings")==[]
         and a.get("story_sha256")==STORY_SHA
         and a.get("spine_sha256")==SPINE_SHA,
         "B02 independent quality not genuinely source-approved")
    return a


def seal_b02_once(source,audit,master_root):
    must(source.get("case_id")=="B02"
         and source["pack"]["pack_sha256"]==SOURCE_SHA
         and source["story"]["story_sha256"]==STORY_SHA
         and source["spine"]["spine_sha256"]==SPINE_SHA
         and audit.get("case_id")=="B02"
         and audit.get("production_state_write_authorized") in (None,False),
         "B01/other-case or self-authorizing English Master promotion refused")
    approved=qualify_master(source,audit)
    root=Path(master_root)
    must(root.is_dir() and not root.is_symlink(),
         "B02 protected pilot English Master directory missing")
    folder=root/MASTER_DIR
    folder.mkdir(mode=0o700,exist_ok=False)
    text=source["story"]["story_text"].encode("utf-8")
    must(len(text.decode("utf-8").split())==561,"B02 prose count drift")
    write_exclusive(folder/"ENGLISH_MASTER.txt",text)
    manifest={
        "schema":SCHEMA,
        "artifact_type":"PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER",
        "case_id":"B02",
        "source_pack_sha256":approved["source_pack_sha256"],
        "source_writer_model":"anthropic/claude-sonnet-5.5",
        "source_story_sha256":approved["story_sha256"],
        "accepted_story_sha256":hashlib.sha256(text).hexdigest(),
        "approved_spine_sha256":approved["spine_sha256"],
        "independent_auditor_generation_id":approved["auditor_generation_id"],
        "independent_initial_audit_verdict":"ACCEPT",
        "reader_score":approved["reader_score"],
        "audit_cost_usd":approved["audit_cost_usd"],
        "english_master_word_count":561,
        "text_path":"ENGLISH_MASTER.txt",
        "manual_text_edits":0,
        "q25_read_only_extraction_allowed":True,
        "full_original_frozen_v21_4_production_quality_accepted":False,
        "production_master_published":False,
        "production_state_write_authorized":False,
    }
    write_exclusive(folder/"master-manifest.json",canonical_json(manifest)+b"\n")
    return manifest


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--producer-claims")
    parser.add_argument("--quality-claims")
    parser.add_argument("--master-root")
    parser.add_argument("--seal-pilot-once",action="store_true")
    args=parser.parse_args()
    if not args.seal_pilot_once:
        print(json.dumps({"case_id":"B02","schema":SCHEMA,"model_posts":0,
                          "english_master_sealed":False,
                          "production_state_write_authorized":False},sort_keys=True))
        return
    must(args.producer_claims and args.quality_claims and args.master_root,
         "Required real B02 sources absent")
    src=get_b02_original(args.repo_root,args.producer_claims)
    audit=load_b02_quality(args.repo_root,args.quality_claims)
    record=seal_b02_once(src,audit,args.master_root)
    print(json.dumps({
        "case_id":"B02","story_sha256":record["source_story_sha256"],
        "word_count":record["english_master_word_count"],
        "independent_reader_score":record["reader_score"],
        "pilot_only":True,"new_model_posts":0,
        "production_state_write_authorized":False},sort_keys=True))


if __name__=="__main__":
    main()
