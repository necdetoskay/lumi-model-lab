from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_translation_semantic_guards import run_translation_semantic_guards
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_stage_common import extract_turkish, read_json, source_calls, write_json
from src.storyforge.runtime import _structured_call

DEFAULT_MODEL="openai/gpt-5.6-luna"
DEFAULT_PROMPT=Path("prompts/translation_fidelity_gate_v2_generic.md")


def _blocking(payload:dict[str,Any])->list[dict[str,Any]]:
    return [
        row for row in (payload.get("findings") or [])
        if str(row.get("severity") or "").lower() in {"serious","critical"}
    ]


def run(
    *,
    source_path:Path,
    out_path:Path,
    prompt_path:Path=DEFAULT_PROMPT,
    model:str=DEFAULT_MODEL,
    api_key:str|None=None,
)->dict[str,Any]:
    load_dotenv()
    source=read_json(source_path)
    english=str(source.get("accepted_english_master") or "").strip()
    turkish=extract_turkish(source)
    if not english:
        raise RuntimeError("Fidelity source is missing accepted English master.")

    hard=run_translation_semantic_guards(english,turkish)
    if hard:
        rollup=rollup_model_calls(source_calls(source))
        result={
            "schema_version":"episode-fidelity.v1",
            "status":"deterministic_semantic_findings",
            "accepted_english_master":english,
            "turkish_delivery":turkish,
            "deterministic_findings":hard,
            "fidelity_findings":[],
            "confirmed_fidelity_findings":hard,
            "model_called":False,
            "translation_repair_attempts":int(source.get("translation_repair_attempts") or 0),
            "pipeline_usage_rollup":rollup,
            "total_cost_usd":rollup["totals"]["cost_usd"],
            "publication_ready":False,
            "next_stage":"TRANSLATION_REPAIR",
            "next_stage_authorized":False,
        }
        write_json(out_path,result)
        return result

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    started=time.perf_counter()
    fidelity,meta=_structured_call(
        api_key=key,
        model=model,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "source_language":"en",
            "target_language":"tr",
            "source_story":english,
            "translation":turkish,
        },
        seed=2026093007,
        request_class="defect_locator",
        max_tokens=2200,
    )
    latency=round(time.perf_counter()-started,3)
    findings=_blocking(fidelity)

    call=normalize_model_call(
        stage="translation_fidelity_gate",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])
    clean=bool(fidelity.get("fidelity_clean")) and not findings

    result={
        "schema_version":"episode-fidelity.v1",
        "status":"clean" if clean else "findings_need_adjudication",
        "accepted_english_master":english,
        "turkish_delivery":turkish,
        "deterministic_findings":[],
        "fidelity_findings":findings,
        "confirmed_fidelity_findings":[],
        "model_called":True,
        "fidelity_model":model,
        "fidelity_meta":meta,
        "translation_repair_attempts":int(source.get("translation_repair_attempts") or 0),
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "publication_ready":clean,
        "next_stage":"FINALIZE" if clean else "FIDELITY_ADJUDICATION",
        "next_stage_authorized":False,
    }
    write_json(out_path,result)
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--prompt",type=Path,default=DEFAULT_PROMPT)
    p.add_argument("--model",default=DEFAULT_MODEL)
    a=p.parse_args()
    result=run(source_path=a.source,out_path=a.out,prompt_path=a.prompt,model=a.model)
    print(json.dumps({
        "status":result["status"],
        "findings":len(result["fidelity_findings"])+len(result["deterministic_findings"]),
        "model_called":result["model_called"],
        "publication_ready":result["publication_ready"],
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
