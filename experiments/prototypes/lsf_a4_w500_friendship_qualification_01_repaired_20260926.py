from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.lsf_a4_w500_friendship_qualification_01_20260926 import (
    AUDIT_SYSTEM,
    TRANSLATION_SYSTEM,
    FIDELITY_SYSTEM,
    normalize_audit,
    meta_cost,
)
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.story_defect_detection import segment_story

FIXTURE=Path("experiments/fixtures/lsf_a4_w500_friendship_qualification_01_repaired_20260926.json")
OUT=Path("runs/lsf-a4-w500-friendship-qualification-01-repaired/result.json")

PRIMARY="anthropic/claude-sonnet-5"
SECONDARY="openai/gpt-5.6-sol"
TRANSLATOR="google/gemini-3.8-flash"
FIDELITY="openai/gpt-5.6-luna"

def audit(api_key:str, model:str, story:str, seed:int, request_class:str):
    seg=segment_story(story)
    payload,meta=structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={"exact_age":4,"story_family":"friendship_emotional_social","story_segments":seg},
        seed=seed,
        max_tokens=2600,
        request_class=request_class,
    )
    return normalize_audit(payload,{x["id"] for x in seg}),meta

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    story=fixture["english_story"]
    started=time.perf_counter()

    words=count_words(story)
    length_pass=375<=words<=625

    primary,pm=audit(key,PRIMARY,story,2026092711,"editorial_audit")
    secondary,sm=audit(key,SECONDARY,story,2026092712,"editorial_audit")
    english_pass=length_pass and not primary and not secondary

    tr=None
    trans_cost=0.0
    trans_usage=None
    fidelity_result=None
    fm=None
    fidelity_pass=False

    if english_pass:
        tr,body,_=call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=story,
            temperature=0.2,
            max_tokens=None,
            seed=2026092713,
            request_class="translation",
            structured_output=False,
        )
        trans_cost=float(parse_cost(body).usd or 0.0)
        trans_usage=parse_usage(body).model_dump(mode="json")
        fidelity_result,fm=structured_call(
            api_key=key,
            model=FIDELITY,
            system=FIDELITY_SYSTEM,
            payload={"source_language":"en","target_language":"tr","exact_age":4,"source_story":story,"translation":tr},
            seed=2026092714,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        findings=fidelity_result.get("findings") or []
        blocking=[x for x in findings if str(x.get("severity") or "") in {"serious","critical"}]
        fidelity_pass=bool(fidelity_result.get("fidelity_clean")) and not blocking

    costs={
        "primary_audit":meta_cost(pm),
        "secondary_audit":meta_cost(sm),
        "translator":trans_cost,
        "fidelity_gate":meta_cost(fm),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-a4-w500-friendship-qualification-01-repaired-result.v1",
        "profile":"LSF-A4-W500-v0.1",
        "source_run_id":fixture["source_run_id"],
        "repair":fixture["repair"],
        "english_story":story,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_model":PRIMARY,
        "primary_findings":primary,
        "secondary_model":SECONDARY,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "translator":TRANSLATOR,
        "turkish_translation":tr,
        "fidelity_model":FIDELITY,
        "fidelity_result":fidelity_result,
        "fidelity_pass":fidelity_pass,
        "publication_ready":english_pass and fidelity_pass,
        "cost_usd":costs,
        "translator_usage":trans_usage,
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"english.txt").write_text(story+"\n",encoding="utf-8")
    if tr:
        (OUT.parent/"turkish.txt").write_text(tr+"\n",encoding="utf-8")

    print(json.dumps({
        "english_words":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "fidelity_pass":fidelity_pass,
        "publication_ready":result["publication_ready"],
        "cost_usd":costs,
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
