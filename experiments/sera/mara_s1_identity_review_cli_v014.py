"""SERA v0.14 real Mara identity review from two archived independent ledgers.

Use the full seven-batch paid model mention inventory and the
25-event source qualification census. No provider calls or world writes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH,EXPECTED_SHA
from experiments.sera.mara_s1_identity_review_v014 import qualify

def run(*,mentions:dict,events:dict)->dict:
    source=json.loads(PATH.read_text(encoding="utf-8"))
    if source.get("source_prose_sha256")!=EXPECTED_SHA:
        raise CoverageError("V014_SOURCE_SHA_CHANGED")
    return qualify(prose=source["prose"],mentions=mentions,events=events)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mentions",required=True,type=Path)
    p.add_argument("--events",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    proposal=run(
        mentions=json.loads(args.mentions.read_text(encoding="utf-8")),
        events=json.loads(args.events.read_text(encoding="utf-8")),
    )
    if args.output.exists():
        raise CoverageError("V014_IDENTITY_OUTPUT_ALREADY_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(
        proposal,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":proposal["status"],
        "source_mentions":proposal["original_model_entity_mentions"],
        "source_events":proposal["original_model_event_candidates"],
        "provisional_refs":proposal["all_unregistered_refs_proposed"],
        "physical_object_candidates":proposal["physical_item_candidate_refs"],
        "events_with_provisional_refs":
            proposal["source_events_with_unregistered_refs"],
        "negative_markers_not_entities":
            proposal["negative_markers_must_not_be_created"],
        "canonical_commit_authorized":False,
        "real_provider_calls":proposal["new_model_calls"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
