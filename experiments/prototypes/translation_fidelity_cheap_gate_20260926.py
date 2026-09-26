from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE=Path("experiments/fixtures/translation_fidelity_cheap_gate_three_case_20260926.json")
OUT=Path("runs/translation-fidelity-cheap-gate/result.json")
MODEL="openai/gpt-5.6-luna"

SYSTEM=r"""
You are a strict bilingual EN->TR translation fidelity gate for children's read-aloud stories.

You receive:
- one authoritative English source story;
- one Turkish translation.

Your job is NOT to improve style. Report ONLY serious or critical translation defects that change meaning or story state.

Serious/critical defect classes:
- omission: meaningful source content missing
- addition: invented event/dialogue/canon/meaning
- character_shift: who acts/speaks/perceives changes
- object_shift: object identity materially changes
- state_shift: physical/object/action state changes
- causal_shift: cause/effect or physical rule changes
- knowledge_shift: discovery/knowledge order changes
- ending_shift: ending meaning/closure/open-endedness materially changes

Do NOT report:
- minor wording preferences
- punctuation
- harmless sentence restructuring
- small register differences
- stylistic translation choices that preserve meaning
- nonblocking sound-effect spelling differences by themselves

For every finding include short exact source and translation quotes when possible.

Return JSON only:
{
  "findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"short exact source quote",
      "translation_quote":"short exact translation quote",
      "why":"brief reason"
    }
  ],
  "fidelity_clean":true
}
""".strip()

def cost(meta:dict[str,Any]|None)->float:
    if not meta: return 0.0
    c=meta.get("cost")
    if isinstance(c,dict) and isinstance(c.get("usd"),(int,float)): return float(c["usd"])
    if isinstance(c,(int,float)): return float(c)
    return 0.0

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    source=fixture["source_story"]
    results=[]
    total=0.0
    started=time.perf_counter()

    for i,case in enumerate(fixture["cases"]):
        payload,meta=structured_call(
            api_key=key,
            model=MODEL,
            system=SYSTEM,
            payload={
                "source_language":"en",
                "target_language":"tr",
                "exact_age":4,
                "source_story":source,
                "translation":case["translation"],
            },
            seed=2026092670+i,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        total+=cost(meta)
        findings=payload.get("findings") or []
        clean=payload.get("fidelity_clean")
        if not isinstance(findings,list) or not isinstance(clean,bool):
            raise RuntimeError("invalid_output_shape")
        serious=[x for x in findings if str(x.get("severity") or "") in {"serious","critical"}]
        passed=(len(serious)==0) if case["kind"]=="clean" else (len(serious)>0)
        results.append({
            "case_id":case["case_id"],
            "kind":case["kind"],
            "findings":serious,
            "model_declared_clean":clean,
            "cost_usd":round(cost(meta),6),
            "pass":passed,
        })

    passes=sum(1 for x in results if x["pass"])
    result={
        "schema_version":"translation-fidelity-cheap-gate-result.v1",
        "model":MODEL,
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
