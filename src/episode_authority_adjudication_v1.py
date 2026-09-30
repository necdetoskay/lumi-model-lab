from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_stage_common import read_json, source_calls, write_json
from src.storyforge.runtime import _structured_call

DEFAULT_MODEL="openai/gpt-5.6-sol"
DEFAULT_PROMPT=Path("prompts/story_authority_adjudicator_v1_generic.md")


def run(
    *,
    source_path: Path,
    out_path: Path,
    prompt_path: Path=DEFAULT_PROMPT,
    model: str=DEFAULT_MODEL,
    api_key: str|None=None,
) -> dict[str, Any]:
    load_dotenv()
    source=read_json(source_path)
    if source.get("schema_version")!="episode-authority-gate.v1":
        raise RuntimeError("Authority gate source schema mismatch.")
    findings=list(source.get("semantic_findings") or [])
    if not findings:
        raise RuntimeError("No semantic findings require adjudication.")

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    story=str(source["story"])
    packet=source["authority_packet"]
    started=time.perf_counter()
    payload,meta=_structured_call(
        api_key=key,
        model=model,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "authority_packet":packet,
            "story":story,
            "semantic_findings":findings,
        },
        seed=2026093003,
        request_class="editorial_audit",
        max_tokens=1800,
    )
    latency=round(time.perf_counter()-started,3)

    evaluations=list(payload.get("evaluations") or [])
    if len(evaluations)!=len(findings):
        raise RuntimeError("Adjudicator must evaluate every semantic finding.")

    confirmed_indices=[int(x) for x in (payload.get("confirmed_finding_indices") or [])]
    if any(i<0 or i>=len(findings) for i in confirmed_indices):
        raise RuntimeError("Adjudicator returned invalid finding index.")

    by_index={int(row["finding_index"]):row for row in evaluations}
    if set(by_index)!=set(range(len(findings))):
        raise RuntimeError("Adjudicator evaluation indices are incomplete.")

    confirmed=[]
    for i,row in by_index.items():
        decision=str(row.get("decision") or "")
        if decision not in {"CONFIRM","REJECT"}:
            raise RuntimeError("Invalid adjudication decision.")
        if (i in confirmed_indices)!=(decision=="CONFIRM"):
            raise RuntimeError("Adjudication indices and decisions disagree.")
        if decision=="CONFIRM":
            confirmed.append(findings[i])

    call=normalize_model_call(
        stage="semantic_authority_adjudication",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])

    result={
        "schema_version":"episode-authority-adjudication.v1",
        "status":"confirmed_findings" if confirmed else "clean_after_adjudication",
        "story":story,
        "authority_packet":packet,
        "original_semantic_findings":findings,
        "evaluations":evaluations,
        "confirmed_findings":confirmed,
        "adjudicator_model":model,
        "adjudication_meta":meta,
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "english_repair_attempts":int(source.get("english_repair_attempts") or 0),
        "next_stage":"BOUNDED_REPAIR" if confirmed else "TRANSLATION",
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
        "confirmed_findings":len(result["confirmed_findings"]),
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
