from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes.luna_cheap_gate_three_case_20260926 import MODEL, SYSTEM, meta_cost, normalize
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE=Path("experiments/fixtures/luna_cheap_gate_turkish_clean_guard_20260926.json")
OUT=Path("runs/luna-cheap-gate-turkish-clean-guard/result.json")

def main():
    load_dotenv()
    api_key=os.environ["OPENROUTER_API_KEY"]
    case=json.loads(FIXTURE.read_text(encoding="utf-8"))
    segments=segment_story(case["story"])
    started=time.perf_counter()
    payload,meta=structured_call(
        api_key=api_key,
        model=MODEL,
        system=SYSTEM,
        payload={
            "case_id":case["case_id"],
            "language":case["language"],
            "story_family":case["family"],
            "exact_age":4,
            "reading_mode":"READ_ALOUD",
            "audit_families":list(DEFECT_FAMILIES),
            "story_segments":segments,
        },
        seed=2026092630,
        max_tokens=2600,
        request_class="editorial_audit",
    )
    findings=normalize(payload,{x["id"] for x in segments})
    result={
        "schema_version":"luna-cheap-gate-turkish-clean-guard-result.v1",
        "model":MODEL,
        "case_id":case["case_id"],
        "findings":findings,
        "pass":len(findings)==0,
        "cost_usd":round(meta_cost(meta),6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
