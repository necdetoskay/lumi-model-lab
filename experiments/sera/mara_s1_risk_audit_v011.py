"""SERA v0.11: read-only forensic checks for full 28-sentence model evidence.

Accepts the signed-in GitHub Actions artifact ZIP, a JSON sweep report,
or the full_scene_assurance.json file. It makes no provider requests
and cannot authorize any state/event commit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.semantic_risks_v011 import audit_risks


def read_source_evidence(path: Path) -> dict:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            members = z.namelist()
            if "full_scene_assurance.json" not in members:
                raise CoverageError("RISK_SOURCE_ZIP_MISSING_FULL_REPORT")
            return json.loads(z.read("full_scene_assurance.json"))
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema")!="sera.blind-sweep-bound.v0.10":
        raise CoverageError("RISK_SOURCE_NOT_SWEEP_REPORT")
    return data


def run(*, report: dict) -> dict:
    source=json.loads(PATH.read_text(encoding="utf-8"))
    prose=source["prose"]
    if source.get("source_prose_sha256")!=EXPECTED_SHA:
        raise CoverageError("RISK_FROZEN_SOURCE_TAMPERED")
    audit=audit_risks(prose=prose,report=report)
    if audit["source_prose_sha256"]!=EXPECTED_SHA:
        raise CoverageError("RISK_AUDIT_SHA_MISMATCH")
    return audit


def main():
    p=argparse.ArgumentParser()
    p.add_argument("evidence",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=run(report=read_source_evidence(args.evidence))
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        if args.output.exists():
            raise CoverageError("RISK_OUTPUT_ALREADY_EXISTS")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered,encoding="utf-8")
    print(json.dumps({
        "schema":result["schema"],
        "status":result["status"],
        "targeted_task_count":result["targeted_task_count"],
        "findings":result["findings"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
