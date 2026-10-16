"""Rebind original paid one-call Haiku identity evidence OFFLINE, no LLM."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.mara_s1_v04_audit import PATH,EXPECTED_SHA
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.paid_blind_identity_forensics_v015 import forensic_rebind

def run(*,original:dict,census:dict)->dict:
    source=json.loads(PATH.read_text(encoding="utf-8"))
    if source.get("source_prose_sha256")!=EXPECTED_SHA:
        raise CoverageError("V015_FORENSIC_FROZEN_PROSE_METADATA_INVALID")
    return forensic_rebind(
        prose=source["prose"],world=entry_state(),
        census=census,evidence=original,
    )

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--paid",required=True,type=Path)
    p.add_argument("--mentions",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    original=json.loads(args.paid.read_text(encoding="utf-8"))
    census=json.loads(args.mentions.read_text(encoding="utf-8"))
    result=run(original=original,census=census)
    if args.output.exists():
        raise CoverageError("V015_FORENSIC_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(
        result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":result["status"],
        "returned_model_rows":result["all_original_model_rows_returned"],
        "safe_json_quote_escapes":
            result["syntax_repair_audit"]["fixed_support_quote_lines"],
        "source_quote_typography_fixes":
            len(result["typographic_source_quote_mapping"]),
        "source_bound_rows":result["source_bound_count"],
        "quarantined_rows":result["quarantine_count"],
        "quarantine_reasons":[{
            "ref":x["entity_ref"],"error":x["error_code"],
        } for x in result["quarantined_original_model_rows"]],
        "new_provider_calls":result["paid_model_calls_during_recovery"],
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
