"""Replay v0.11 Haiku initial historical provider evidence, never pay again."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import recover_historical_first

def read_artifact(path: Path) -> dict:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            files=set(z.namelist())
            if not {"manifest.json","task_001.json"} <= files:
                raise CoverageError("HAIKU_HISTORICAL_ZIP_MISSING_FILES")
            return {
                "manifest":json.loads(z.read("manifest.json")),
                "first":json.loads(z.read("task_001.json"))
            }
    raise CoverageError("HAIKU_EXPECTED_IMMUTABLE_ZIP")

def replay(*,source_risks:dict,historical:dict) -> dict:
    recovered=recover_historical_first(
        audit=source_risks,manifest=historical["manifest"],
        task_artifact=historical["first"],
    )
    return recovered

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--risks",required=True,type=Path)
    parser.add_argument("--historical-zip",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    audit=json.loads(args.risks.read_text(encoding="utf-8"))
    result=replay(source_risks=audit,historical=read_artifact(args.historical_zip))
    if args.output.exists():
        raise CoverageError("HAIKU_REPLAY_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "model_verdict":result["bound_advisory"]["verdict_model_proposed"],
        "model_kind":result["bound_advisory"]["kind_model_proposed"],
        "quote_binding_method":result["quote_binding_method"],
        "paid_calls_during_recovery":result["model_calls_during_recovery"],
        "canonical_commit_authorized":result["canonical_commit_authorized"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
