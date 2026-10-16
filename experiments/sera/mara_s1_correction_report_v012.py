"""Forensic offline v0.12 Mara correction proposal from real provider evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile
from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH,EXPECTED_SHA
from experiments.sera.mara_s1_candidate_corrections_v012 import (
    evidence_bundle_from_last_artifact,propose,
)

def load_last_haiku_zip(file:Path)->dict:
    if not zipfile.is_zipfile(file):
        raise CoverageError("V012_EXPECTED_HAIKU_ZIP")
    with zipfile.ZipFile(file) as archive:
        files=archive.namelist()
        if set(files)!={"manifest.json","reused-task-001.json",
                       "reused-task-002.json","task_003.json"}:
            raise CoverageError("V012_HAIKU_ZIP_EXTRA_OR_MISSING_FILE")
        return {name:json.loads(archive.read(name)) for name in files}

def run(*,full:dict,haiku_archive:dict)->dict:
    raw=json.loads(PATH.read_text(encoding="utf-8"))
    if raw.get("source_prose_sha256")!=EXPECTED_SHA:
        raise CoverageError("V012_SOURCE_REPLACED")
    bundle=evidence_bundle_from_last_artifact(last_artifact=haiku_archive)
    return propose(prose=raw["prose"],full_report=full,bundle=bundle)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--full-scene",required=True,type=Path)
    p.add_argument("--haiku-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    full=json.loads(args.full_scene.read_text(encoding="utf-8"))
    out=run(full=full,haiku_archive=load_last_haiku_zip(args.haiku_zip))
    if args.output.exists():
        raise CoverageError("V012_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({
        "schema":out["schema"],
        "status":out["status"],
        "model_event_candidates":out["original_model_event_count"],
        "proposed_event_corrections":len(out["replacements"]),
        "proposed_facet_changes":len(out["shadow_facet_proposals"]),
        "blockers":out["blockers"],
        "canonical_commit_authorized":out["canonical_commit_authorized"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
