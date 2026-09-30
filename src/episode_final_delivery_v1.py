from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.generate import count_words
from src.story_stage_common import read_json, source_calls, write_json
from src.model_usage_rollup import rollup_model_calls


def run(
    *,
    source_path:Path,
    approved_path:Path,
    out_path:Path,
)->dict[str,Any]:
    source=read_json(source_path)
    approved=read_json(approved_path)
    if source.get("publication_ready") is not True:
        raise RuntimeError("Finalization requires publication_ready=true.")
    english=str(source.get("accepted_english_master") or "").strip()
    turkish=str(source.get("turkish_delivery") or "").strip()
    if not english or not turkish:
        raise RuntimeError("Finalization source is missing English or Turkish delivery.")

    rollup=rollup_model_calls(source_calls(source))
    result={
        "schema_version":"episode-final-delivery.v1",
        "status":"publication_ready",
        "publication_ready":True,
        "exact_age":int(approved["episode_spine"]["exact_age"]),
        "source_spine_run_id":approved.get("source_run_id"),
        "accepted_english_master":english,
        "english_word_count":count_words(english),
        "turkish_delivery":turkish,
        "turkish_word_count":count_words(turkish),
        "pipeline_usage_rollup":rollup,
        "product_path_api_calls":rollup["totals"]["api_calls"],
        "product_path_tokens":rollup["totals"]["total_tokens"],
        "product_path_cost_usd":rollup["totals"]["cost_usd"],
        "product_path_latency_seconds":rollup["totals"]["latency_seconds"],
        "local_currency_report":{
            "currency":"TRY",
            "rate":None,
            "rate_timestamp":None,
            "amount":None,
            "note":"Filled at final reporting time using the then-current USD/TRY rate."
        }
    }
    write_json(out_path,result)
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--approved",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=run(source_path=a.source,approved_path=a.approved,out_path=a.out)
    print(json.dumps({
        "status":result["status"],
        "api_calls":result["product_path_api_calls"],
        "tokens":result["product_path_tokens"],
        "cost_usd":result["product_path_cost_usd"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
