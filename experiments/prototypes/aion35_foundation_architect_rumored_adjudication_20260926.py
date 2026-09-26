from __future__ import annotations
import json, os, time
from pathlib import Path
from dotenv import load_dotenv
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE=Path("experiments/fixtures/aion35_foundation_architect_rumored_adjudication_20260926.json")
OUT=Path("runs/aion35-foundation-architect-rumored-adjudication/result.json")
MODEL="anthropic/claude-sonnet-5"

SYSTEM="""
Adjudicate the disputed validation findings using the supplied canonical definition.
RUMORED means the Character has hearsay-level awareness only.
It must not be treated as visited, observed interior detail, confirmed route, or confirmed knowledge of contents.
Hearing of the place, wondering about it, or remembering that it was mentioned can be consistent with RUMORED if no visit or content is asserted.
Return JSON only:
{"decisions":[{"finding_index":0,"verdict":"UPHOLD|OVERTURN","why":"brief"}],
"remaining_serious_or_critical":0,
"qualification_effect":"PASS_IF_NO_OTHER_BLOCKERS|FAIL"}
""".strip()

def main():
    load_dotenv()
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    started=time.perf_counter()
    result,meta=structured_call(
        api_key=os.environ["OPENROUTER_API_KEY"], model=MODEL, system=SYSTEM,
        payload=fixture, seed=2026092831, max_tokens=1800, request_class="editorial_audit")
    decisions=result.get("decisions") or []
    upheld=sum(1 for x in decisions if x.get("verdict")=="UPHOLD")
    clean=(len(decisions)==len(fixture["disputed_findings"]) and upheld==0
           and int(result.get("remaining_serious_or_critical",999) or 0)==0
           and result.get("qualification_effect")=="PASS_IF_NO_OTHER_BLOCKERS")
    payload={"source_run":fixture["source_run"],"arbiter":MODEL,"result":result,
             "dispute_clean":clean,
             "cost_usd":float((((meta or {}).get("cost") or {}).get("usd")) or 0.0),
             "elapsed_seconds":round(time.perf_counter()-started,3)}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
