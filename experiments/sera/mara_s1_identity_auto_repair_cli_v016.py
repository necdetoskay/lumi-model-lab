"""Offline proof: SERA v0.16 automatic repair of original paid v0.15 reply.

Forensics are only the immutable input-evidence provenance check;
the actual recovery, relation routing and abstention happen in the
generic identity_auto_repair_v016.repair stage, without any Mara-specific
identity rules, hand edits or new provider calls.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.identity_auto_repair_v016 import repair
from experiments.sera.mara_s1_blind_identity_pilot_v015 import prepare
from experiments.sera.paid_blind_identity_forensics_v015 import verify_paid_provenance

def run(*,paid:dict,mentions:dict)->dict:
    prose,world,request=prepare(mentions)
    verify_paid_provenance(evidence=paid,request=request)
    result=repair(
        prose=prose,world=world,census=mentions,
        raw_provider_content=paid["raw_provider_content"],
        model_repair=None,
        max_targeted_calls=0,
    )
    if result["request_sha256"]!=paid["request_sha256"] or (
        result["original_response_sha256"]==
        paid.get("wrong_original_response_sha256","NOT_GIVEN")
    ):
        raise CoverageError("V016_REPLAY_REQUEST_OR_RAW_INVALID")
    return {
        **result,
        "original_paid_run_id":38872615837,
        "original_provider_reported_cost_usd":paid["provider_reported_cost"],
        "new_provider_calls_during_replay":0,
        "offline_replay_only":True,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--paid",required=True,type=Path)
    p.add_argument("--mentions",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=run(
        paid=json.loads(args.paid.read_text(encoding="utf-8")),
        mentions=json.loads(args.mentions.read_text(encoding="utf-8")),
    )
    if args.output.exists():
        raise CoverageError("V016_AUTO_REPAIR_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({
        "schema":result["schema"],
        "status":result["status"],
        "source_bound_rows":result["accepted_source_bound_count"],
        "automatic_abstains":result["automatic_abstain_count"],
        "deterministic_repairs":result["deterministically_repaired_count"],
        "new_model_calls":result["new_provider_calls_during_replay"],
        "world_db_writes":result["world_db_writes"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
