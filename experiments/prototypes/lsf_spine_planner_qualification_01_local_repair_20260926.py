from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.lsf_spine_planner_qualification_01_20260926 import (
    PRIMARY_AUDITOR,
    SECONDARY_AUDITOR,
    TRANSLATOR,
    FIDELITY_GATE,
    TRANSLATION_SYSTEM,
    FIDELITY_SYSTEM,
    audit_story,
    meta_cost,
)
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.generate import call_openrouter, count_words, parse_cost, parse_usage

FIXTURE=Path("experiments/fixtures/lsf_spine_planner_qualification_01_local_repair_20260926.json")
OUT=Path("runs/lsf-spine-planner-qualification-01-local-repair/result.json")
SEED=2026092751

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    started=time.perf_counter()

    source=fixture["source_story"]
    repair=fixture["repair"]
    old=repair["old"]
    new=repair["replacement"]

    if source.count(old)!=1:
        raise RuntimeError(f"repair_span_count:{source.count(old)}")

    story=source.replace(old,new,1)
    words=count_words(story)
    length_pass=375<=words<=625

    audit_fixture={
        "story_intent":fixture["story_intent"],
        "context_packet":fixture["context_packet"],
    }

    primary,pm=audit_story(
        api_key=key,
        model=PRIMARY_AUDITOR,
        fixture=audit_fixture,
        plan=fixture["validated_plan"],
        story=story,
        seed=SEED,
    )
    secondary,sm=audit_story(
        api_key=key,
        model=SECONDARY_AUDITOR,
        fixture=audit_fixture,
        plan=fixture["validated_plan"],
        story=story,
        seed=SEED+1,
    )

    english_pass=length_pass and not primary and not secondary

    tr=None
    trans_cost=0.0
    trans_usage=None
    fidelity=None
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
            seed=SEED+2,
            request_class="translation",
            structured_output=False,
        )
        trans_cost=float(parse_cost(body).usd or 0.0)
        trans_usage=parse_usage(body).model_dump(mode="json")

        fidelity,fm=structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language":"en",
                "target_language":"tr",
                "exact_age":4,
                "source_story":story,
                "translation":tr,
            },
            seed=SEED+3,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        blocking=[
            x for x in (fidelity.get("findings") or [])
            if str(x.get("severity") or "") in {"serious","critical"}
        ]
        fidelity_pass=bool(fidelity.get("fidelity_clean")) and not blocking

    costs={
        "primary_story_audit":meta_cost(pm),
        "secondary_story_audit":meta_cost(sm),
        "translator":trans_cost,
        "fidelity_gate":meta_cost(fm),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-spine-planner-qualification-01-local-repair-result.v1",
        "source_run_id":fixture["source_run_id"],
        "profile":fixture["profile"],
        "repair":repair,
        "english_story":story,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "turkish_translation":tr,
        "fidelity_result":fidelity,
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
        "english_word_count":words,
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
