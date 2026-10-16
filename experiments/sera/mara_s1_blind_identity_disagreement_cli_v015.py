"""SERA v0.15 blind-versus-historical identity hypothesis audit, offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.identity_disagreement_v015 import compare

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--blind-forensic",required=True,type=Path)
    p.add_argument("--prior-hypotheses",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    report=compare(
        forensic=json.loads(args.blind_forensic.read_text(encoding="utf-8")),
        prior=json.loads(args.prior_hypotheses.read_text(encoding="utf-8")),
    )
    if args.output.exists():
        raise CoverageError("V015_CONTRAST_OUTPUT_EXISTS")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(
        report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "checked":report["original_model_mentioned_refs"],
        "source_bound":report["blind_source_bound_proposal_count"],
        "quarantined":report["blind_quarantined_count"],
        "classification_agreement_not_accuracy":
            report["category_agreement_count_NOT_SEMANTIC_ACCURACY"],
        "full_tuple_agreement_not_gold":
            report["full_tuple_agreement_count_NOT_GOLD"],
        "review_flags":report["review_flag_frequency"],
        "new_model_calls":0,
        "canonical_commit_authorized":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
