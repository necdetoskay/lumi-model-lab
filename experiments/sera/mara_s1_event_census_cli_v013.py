"""Read actual archived Mara Gemini+Haiku evidence and issue 25-event HOLD census.

No provider call, DB change, model retry, state commit, synthetic gold, or
guess at absolute scene times.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.mara_s1_event_census_v013 import run

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--full-report",required=True,type=Path)
    p.add_argument("--repairs",required=True,type=Path)
    p.add_argument("--versioned",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    source=json.loads(PATH.read_text(encoding="utf-8"))
    result=run(
        prose=source["prose"],world=entry_state(),
        full_report=json.loads(a.full_report.read_text(encoding="utf-8")),
        repairs=json.loads(a.repairs.read_text(encoding="utf-8")),
        versioned_simulation=json.loads(a.versioned.read_text(encoding="utf-8")),
    )
    if a.output.exists():
        raise CoverageError("V013_CENSUS_OUTPUT_ALREADY_EXISTS")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(
        result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "source_event_count":result["source_model_event_count"],
        "repair_count":result["candidate_repair_count"],
        "unregistered_refs":result["unregistered_or_provisional_refs"],
        "bodypart_refs":result["body_part_candidate_refs"],
        "blocker_frequency":result["blocker_frequency"],
        "canonical_events_authorized":result["events_qualified_for_canonical_commit"],
        "db_writes":result["production_database_writes"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
