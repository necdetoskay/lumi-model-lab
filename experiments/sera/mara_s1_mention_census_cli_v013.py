"""Mara all-mention evidence runner, using exactly seven previously paid batches."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_sweep_pilot_v010 import prepare
from experiments.sera.mara_s1_v010_forensics import read_evidence,replay
from experiments.sera.sentence_sweep_v010 import bind_batch
from experiments.sera.mara_s1_mention_census_v013 import run

def run_from_archives(*,six_dir:Path,pilot_zip:Path)->dict:
    source=prepare()
    pilot=read_evidence(pilot_zip)
    forensic=replay(evidence=pilot)  # source/old API response pinned exactly
    if forensic["paid_model_calls_during_replay"]!=0:
        raise CoverageError("MENTION_PILOT_NOT_OFFLINE")
    original=bind_batch(
        plan=source["plan"],batch_id="batch_003",
        raw=pilot["raw_extraction"],prose=source["prose"]
    )
    batches=[original]
    for req in source["plan"]["batches"]:
        if req["batch_id"]=="batch_003":
            continue
        path=six_dir/(req["batch_id"]+".json")
        if not path.is_file():
            raise CoverageError("MENTION_PAID_BATCH_NOT_FOUND:"+req["batch_id"])
        data=json.loads(path.read_text(encoding="utf-8"))
        bound=data.get("bound_batch")
        if data.get("request_sha256")!=req["request_sha256"] or not isinstance(
            bound,dict
        ):
            raise CoverageError("MENTION_PAID_BATCH_PROVENANCE_INVALID")
        if bound.get("request_sha256")!=req["request_sha256"]:
            raise CoverageError("MENTION_PAID_BOUND_REQUEST_MISMATCH")
        batches.append(bound)
    return run(prose=source["prose"],world=entry_state(),
               plan=source["plan"],bound_batches=batches)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--six-dir",required=True,type=Path)
    p.add_argument("--pilot-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    result=run_from_archives(six_dir=a.six_dir,pilot_zip=a.pilot_zip)
    if a.output.exists():
        raise CoverageError("MENTION_OUTPUT_EXISTS")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(
        result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "mentions":result["total_source_bound_mentions"],
        "unique_refs":result["unique_mentioned_refs"],
        "unregistered_refs":result["unregistered_or_provisional_mentions"],
        "anatomical_refs":result["anatomical_parts_not_inventory"],
        "entities_auto_created":result["automatic_new_entities_created"],
        "canonical_commit_authorized":result["canonical_commit_authorized"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
