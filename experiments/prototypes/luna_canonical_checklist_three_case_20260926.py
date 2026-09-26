from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes.story_defect_natural_e2e_repair_proof_20260926 import (
    ADJUDICATOR_MODEL,
    call_checklist_detector,
    meta_cost,
)

SOURCE_POOL=Path("experiments/fixtures/story_defect_source_pool.tr-age4.v1.json")
PROOF_FIXTURE=Path("experiments/fixtures/story_defect_natural_e2e_repair_proof.v1.json")
OUT=Path("runs/luna-canonical-checklist-three-case/result.json")

CASE_IDS=["N1_RESPONSE","N2_STATE","N5_CLEAN"]

def main():
    load_dotenv()
    api_key=os.environ["OPENROUTER_API_KEY"]
    pool=json.loads(SOURCE_POOL.read_text(encoding="utf-8"))
    proof=json.loads(PROOF_FIXTURE.read_text(encoding="utf-8"))
    by_source={x["source_id"]:x for x in pool["sources"]}
    by_case={x["proof_id"]:x for x in proof["cases"]}
    started=time.perf_counter()
    results=[]
    total=0.0

    for i,case_id in enumerate(CASE_IDS):
        spec=by_case[case_id]
        source=by_source[spec["source_id"]]
        findings,meta=call_checklist_detector(
            api_key=api_key,
            model=ADJUDICATOR_MODEL,
            story_id=f"LUNA_CANONICAL_{case_id}",
            story_family=source["family"],
            story_text=source["story"],
            seed=2026092640+i,
        )
        total+=meta_cost(meta)
        row={
            "case_id":case_id,
            "kind":spec["kind"],
            "findings":findings,
            "cost_usd":round(meta_cost(meta),6),
            "pass":False,
        }
        if spec["kind"]=="clean":
            row["pass"]=len(findings)==0
            row["scoring"]={"clean_zero_findings":row["pass"]}
        else:
            gold=set(spec["expected_span_ids"])
            match=next((f for f in findings if f["family"]==spec["expected_family"] and gold.intersection(f["span_ids"])),None)
            row["pass"]=match is not None
            row["scoring"]={
                "expected_family":spec["expected_family"],
                "family_and_span_overlap":match is not None,
                "expected_scope":spec["expected_repair_scope"],
                "detected_scope":match["repair_scope"] if match else None,
            }
        results.append(row)

    passes=sum(1 for x in results if x["pass"])
    result={
        "schema_version":"luna-canonical-checklist-three-case-result.v1",
        "model":ADJUDICATOR_MODEL,
        "prompt_authority":"existing canonical CHECKLIST_DETECTOR_SYSTEM; unchanged",
        "status":"PASS" if passes==len(results) else "FAIL",
        "summary":{"cases":len(results),"passes":passes,"failures":len(results)-passes,"all_three_pass":passes==len(results)},
        "results":results,
        "total_cost_usd":round(total,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
