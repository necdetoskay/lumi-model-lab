"""SERA v0.12 actual Mara source-only typed facet shadow projection.

Run only from the previously verified candidate repair report; never
apply world_state_v02.apply_event, write production DB or alter prose.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.mara_s1_v04_audit import PATH,EXPECTED_SHA
from experiments.sera.shadow_aspect_projection_v012 import project_mara

def run(*,corrections:dict)->dict:
    source=json.loads(PATH.read_text(encoding="utf-8"))
    if source.get("source_prose_sha256")!=EXPECTED_SHA:
        raise CoverageError("MARA_SHADOW_FROZEN_SOURCE_CHANGED")
    return project_mara(
        world=entry_state(),prose=source["prose"],
        corrections=corrections,
    )

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--corrections",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=run(corrections=json.loads(
        args.corrections.read_text(encoding="utf-8")
    ))
    if args.output.exists():
        raise CoverageError("SHADOW_OUTPUT_FILE_ALREADY_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status":result["status"],
        "world_state_unchanged":result["world_state_unchanged"],
        "facet_changes":result["facets_applied_noncanonically"],
        "watch_case_state":result["typed_shadow_facet_state"]
                          ["facets"]["openable"]["case_position"],
        "notebook_observed_append_count":len(
            result["typed_shadow_facet_state"]["facets"]
                  ["document"]["observed_appends"]
        ),
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
