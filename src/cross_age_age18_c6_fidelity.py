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
from src.storyforge.runtime import FIDELITY_SYSTEM, _structured_call

FIDELITY_MODEL = "openai/gpt-5.6-luna"

DEFAULT_C5 = Path(
    "data/specifications/story_lab/age18_cross_age_c5_run_36620129124.json"
)
DEFAULT_OUT = Path("runs/sonnet55-cross-age-age18-c6/result.json")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _blocking(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in findings
        if str(row.get("severity") or "").lower() in {"serious", "critical"}
    ]


def run(
    *,
    c5_path: Path,
    out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    c5 = _read(c5_path)
    if c5.get("status") != "translated_awaiting_fidelity":
        raise RuntimeError("C5 translation source is not awaiting fidelity.")

    english = str(c5["accepted_english_master"]).strip()
    turkish = str(c5["turkish_delivery"]).strip()
    if not english or not turkish:
        raise RuntimeError("C5 source is missing English or Turkish text.")

    require_qualification_runtime_profile(FIDELITY_MODEL)

    started = time.perf_counter()
    fidelity, meta = _structured_call(
        api_key=key,
        model=FIDELITY_MODEL,
        system=FIDELITY_SYSTEM,
        payload={
            "exact_age": 18,
            "source_story_en": english,
            "translation_tr": turkish,
        },
        seed=2026092945,
        request_class="editorial_audit",
        max_tokens=2200,
    )
    latency = round(time.perf_counter() - started, 3)

    call = normalize_model_call(
        stage="age18_c6_fidelity",
        model=FIDELITY_MODEL,
        provider=runtime_profile_identity(FIDELITY_MODEL).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    fidelity_rollup = rollup_model_calls([call])
    source_calls = list((c5.get("pipeline_usage_rollup") or {}).get("calls") or [])
    pipeline_rollup = rollup_model_calls(source_calls + [call])

    findings = list(fidelity.get("findings") or [])
    blocking = _blocking(findings)
    direct_clean = bool(fidelity.get("fidelity_clean")) and not blocking

    result = {
        "schema_version": "cross-age-age18-c6-fidelity.v1",
        "status": "fidelity_clean" if direct_clean else "fidelity_flagged",
        "source_c5_run_id": 36620129124,
        "model": FIDELITY_MODEL,
        "accepted_english_master": english,
        "turkish_delivery": turkish,
        "fidelity": fidelity,
        "blocking_findings": blocking,
        "fidelity_usage_rollup": fidelity_rollup,
        "pipeline_usage_rollup": pipeline_rollup,
        "incremental_cost_usd": fidelity_rollup["totals"]["cost_usd"],
        "incremental_latency_seconds": fidelity_rollup["totals"]["latency_seconds"],
        "pipeline_cost_usd": pipeline_rollup["totals"]["cost_usd"],
        "publication_ready": direct_clean,
        "next_stage_authorized": False,
        "next_stage": (
            "FINALIZE_AGE18_DELIVERY"
            if direct_clean
            else "HUMAN_ADJUDICATE_FIDELITY_FINDINGS"
        ),
    }
    _write(out_path, result)
    print(json.dumps({
        "status": result["status"],
        "blocking_findings": len(blocking),
        "incremental_cost_usd": result["incremental_cost_usd"],
        "incremental_latency_seconds": result["incremental_latency_seconds"],
        "pipeline_cost_usd": result["pipeline_cost_usd"],
        "publication_ready": result["publication_ready"],
        "next_stage_authorized": False,
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c5", type=Path, default=DEFAULT_C5)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(c5_path=args.c5, out_path=args.out)


if __name__ == "__main__":
    main()
