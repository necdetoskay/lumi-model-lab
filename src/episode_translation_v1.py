from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_translation_semantic_guards import run_translation_semantic_guards
from src.generate import call_openrouter, count_words, parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_stage_common import extract_story, read_json, source_calls, write_json

DEFAULT_MODEL="google/gemini-3.8-flash"
DEFAULT_PROMPT=Path("prompts/translation_en_tr_v2_generic.md")


def run(
    *,
    source_path: Path,
    approved_path: Path,
    out_path: Path,
    tr_out_path: Path,
    prompt_path: Path=DEFAULT_PROMPT,
    model: str=DEFAULT_MODEL,
    api_key: str|None=None,
) -> dict[str, Any]:
    load_dotenv()
    source=read_json(source_path)
    approved=read_json(approved_path)
    english=extract_story(source)
    exact_age=int(approved["episode_spine"]["exact_age"])

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    started=time.perf_counter()
    translation,body,request=call_openrouter(
        api_key=key,
        model=model,
        system_prompt=prompt_path.read_text(encoding="utf-8").strip(),
        user_prompt=json.dumps({
            "exact_age":exact_age,
            "accepted_english_master":english,
        },ensure_ascii=False),
        temperature=0.2,
        max_tokens=8000,
        seed=2026093005,
        request_class="translation",
        structured_output=False,
    )
    latency=round(time.perf_counter()-started,3)

    semantic=run_translation_semantic_guards(english,translation)
    call=normalize_model_call(
        stage="translation",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=body.get("usage") or {},
        cost=parse_cost(body).model_dump(mode="json"),
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])
    clean=not semantic

    result={
        "schema_version":"episode-translation.v1",
        "status":"semantic_guard_clean" if clean else "semantic_guard_findings",
        "accepted_english_master":english,
        "english_word_count":count_words(english),
        "turkish_delivery":translation,
        "turkish_word_count":count_words(translation),
        "translation_semantic_findings":semantic,
        "translation_model":model,
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "translation_repair_attempts":0,
        "next_stage":"FIDELITY" if clean else "TRANSLATION_REPAIR",
        "next_stage_authorized":False,
    }
    write_json(out_path,result)
    tr_out_path.parent.mkdir(parents=True,exist_ok=True)
    tr_out_path.write_text(translation.rstrip()+"\n",encoding="utf-8")
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--approved",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--tr-out",type=Path,required=True)
    p.add_argument("--prompt",type=Path,default=DEFAULT_PROMPT)
    p.add_argument("--model",default=DEFAULT_MODEL)
    a=p.parse_args()
    result=run(
        source_path=a.source,approved_path=a.approved,out_path=a.out,
        tr_out_path=a.tr_out,prompt_path=a.prompt,model=a.model,
    )
    print(json.dumps({
        "status":result["status"],
        "semantic_findings":len(result["translation_semantic_findings"]),
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
