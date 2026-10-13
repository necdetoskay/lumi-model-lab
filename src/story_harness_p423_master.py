"""P4.23 pilot English Master: seal ONLY genuine source-linked P4.22 ACCEPT.

No model call, no prod state write and no claim of original frozen v21.4
positive quality on a 4-year-old story. The admission gate is an independent
versioned P422 initial audit with zero blocking families.
"""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from src.story_harness_p422_independent_audit import load_source,STAGE_COST_CAP
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA="lumi.story-harness-p423-pilot-english-master.v1"


def must(x,reason):
    if not x:raise HarnessStop(reason)


def read_audit(source,audit_root):
    root=Path(audit_root)
    must(root.is_dir() and not root.is_symlink(),
         "No trusted independent quality audit claim root")
    sha=source["story"]["story_sha256"]
    folder=root/("p422-b01-r06-"+sha[:12])
    must(folder.is_dir() and not folder.is_symlink(),
         "Missing same-story quality audit")
    path=folder/"01-audit-outcome.json"
    must(path.is_file() and not path.is_symlink()
         and path.stat().st_size<=64000,
         "Missing bounded original independent audit receipt")
    return json.loads(path.read_bytes())


def qualify_master(source,audit):
    story=source["story"]
    spine=source["spine"]
    pack=source["pack"]
    must(type(audit) is dict and
         audit.get("schema")=="lumi.story-harness-p422-independent-initial-audit.v1"
         and audit.get("source_pack_sha256")==pack["pack_sha256"]
         and audit.get("story_sha256")==story["story_sha256"]
         and audit.get("spine_sha256")==spine["spine_sha256"]
         and audit.get("original_spine_generation_id")==spine["provider_generation_id"],
         "Quality source, original model Spine or story SHA mismatch")
    must(audit.get("quality_initial_verdict")=="ACCEPT"
         and audit.get("quality_initial_audit_accepted") is True
         and audit.get("blocking_findings")==[]
         and type(audit.get("reader_score")) is int
         and audit["reader_score"]>=4,
         "Not independently accepted with zero blockers and reading quality")
    must(audit.get("english_master_authorized") is False
         and audit.get("q25_authorized") is False
         and audit.get("state_write_authorized") is False,
         "Audit cannot self-authorize downstream production writes")
    must(type(audit.get("auditor_generation_id")) is str
         and audit["auditor_generation_id"].startswith("gen-")
         and audit.get("auditor_model")=="anthropic/claude-sonnet-5.5",
         "Unverified independent model auditor identity")
    try:
        cost=Decimal(audit["auditor_reported_cost_usd"])
    except Exception:
        raise HarnessStop("Unknown audit cost") from None
    must(cost.is_finite() and 0<cost<=STAGE_COST_CAP,
         "Audit charged outside approved stage policy")
    text=story["story_text"]
    must(hashlib.sha256(text.encode()).hexdigest()==story["story_sha256"],
         "English Master byte hash differs from accepted story")
    must(len(text.split())==story["word_count"],
         "Master prose word count was edited after ACCEPT")
    return {"story_sha256":story["story_sha256"],
            "spine_sha256":spine["spine_sha256"],
            "source_pack_sha256":pack["pack_sha256"],
            "auditor_generation_id":audit["auditor_generation_id"],
            "audit_cost_usd":format(cost,"f"),
            "reader_score":audit["reader_score"]}


def write_exclusive(path,content):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def seal_pilot_master(source,audit,master_root):
    qualified=qualify_master(source,audit)
    root=Path(master_root)
    must(root.is_dir() and not root.is_symlink(),
         "No protected pilot Master claim root")
    folder=root/("b01-"+qualified["story_sha256"][:16])
    folder.mkdir(mode=0o700,exist_ok=False)
    story=source["story"]
    text=story["story_text"].encode()
    write_exclusive(folder/"ENGLISH_MASTER.txt",text)
    result={
        "schema":SCHEMA,
        "artifact_type":"PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER",
        "case_id":"B01",
        "source_pack_sha256":qualified["source_pack_sha256"],
        "source_writer_model":"anthropic/claude-sonnet-5.5",
        "source_story_sha256":qualified["story_sha256"],
        "accepted_story_sha256":hashlib.sha256(text).hexdigest(),
        "approved_spine_sha256":qualified["spine_sha256"],
        "independent_auditor_generation_id":qualified["auditor_generation_id"],
        "independent_initial_audit_verdict":"ACCEPT",
        "reader_score":qualified["reader_score"],
        "audit_cost_usd":qualified["audit_cost_usd"],
        "english_master_word_count":story["word_count"],
        "text_path":"ENGLISH_MASTER.txt",
        "manual_text_edits":0,
        "q25_read_only_extraction_allowed":True,
        "full_original_frozen_v21_4_production_quality_accepted":False,
        "production_master_published":False,
        "production_state_write_authorized":False,
    }
    write_exclusive(folder/"master-manifest.json",canonical_json(result)+b"\n")
    return result


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--producer-claims")
    parser.add_argument("--quality-claims")
    parser.add_argument("--master-root")
    parser.add_argument("--seal-pilot-once",action="store_true")
    args=parser.parse_args()
    if not args.seal_pilot_once:
        print(json.dumps({"schema":SCHEMA,
                          "model_calls":0,"sealed_master":False,
                          "production_state_write_authorized":False},
                         sort_keys=True))
    else:
        must(args.producer_claims and args.quality_claims and args.master_root,
             "Missing immutable same-story source roots")
        source=load_source(args.repo_root,args.producer_claims)
        audit=read_audit(source,args.quality_claims)
        result=seal_pilot_master(source,audit,args.master_root)
        print(json.dumps(result,sort_keys=True))
