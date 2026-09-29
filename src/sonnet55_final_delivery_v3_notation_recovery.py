from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.model_registry import require_qualification_runtime_profile
from src.model_usage_rollup import rollup_model_calls
from src.storyforge.runtime import FIDELITY_SYSTEM, _structured_call
from src.translation_fidelity_recovery import (
    ADJUDICATION_SYSTEM,
    _blocking,
    _meta_calls,
)
from src.generate import count_words

FIDELITY_MODEL = "openai/gpt-5.6-luna"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/sonnet55_final_delivery_v2_run_36580391689.json"
)
DEFAULT_OUT = Path("runs/sonnet55-final-delivery-v3/result.json")
DEFAULT_EN_OUT = Path("runs/sonnet55-final-delivery-v3/final_en.txt")
DEFAULT_TR_OUT = Path("runs/sonnet55-final-delivery-v3/final_tr.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _apply_notation_patch(text: str) -> tuple[str, dict[str, Any]]:
    old = "*G — tek düzenek.*"
    new = "*P — tek düzenek.*"
    if text.count(old) != 1:
        raise RuntimeError(
            f"Expected exactly one Turkish notation mismatch {old!r}, found {text.count(old)}"
        )
    patched = text.replace(old, new, 1)
    if patched.count(new) != 1:
        raise RuntimeError("Corrected P notation must appear exactly once.")
    if "*G — tek düzenek.*" in patched:
        raise RuntimeError("G notation remains after deterministic patch.")
    return patched, {
        "old": old,
        "new": new,
        "why": "Match the accepted English master's exact mentor notation: P — single setup.",
        "mode": "deterministic_exact_replacement",
    }


def run(
    *,
    source_path: Path,
    out_path: Path,
    en_out_path: Path,
    tr_out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read(source_path)
    if source.get("schema_version") != "sonnet55-final-delivery-v2.evidence.v1":
        raise RuntimeError("Unexpected V2 source schema.")
    if not source.get("publication_ready"):
        raise RuntimeError("V2 source must be publication_ready before notation recovery.")

    require_qualification_runtime_profile(FIDELITY_MODEL)

    english = str(source["accepted_english_master"]).strip()
    translation = str(source["turkish_delivery_story"]).strip()
    translation, patch = _apply_notation_patch(translation)

    calls = list((source.get("pipeline_usage_rollup") or {}).get("calls") or [])
    recovery_calls: list[dict[str, Any]] = []

    evidence: dict[str, Any] = {
        "schema_version": "sonnet55-final-delivery-v3.evidence.v1",
        "status": "notation_patched",
        "publication_ready": False,
        "source_v2_run_id": 36580391689,
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "accepted_english_master": english,
        "turkish_delivery_story": translation,
        "english_word_count": count_words(english),
        "turkish_word_count": count_words(translation),
        "deterministic_patches": [patch],
        "deterministic_checks": {
            "p_notation_count": translation.count("*P — tek düzenek.*"),
            "g_notation_count": translation.count("*G — tek düzenek.*"),
            "notation_alignment_pass": (
                translation.count("*P — tek düzenek.*") == 1
                and translation.count("*G — tek düzenek.*") == 0
            ),
        },
    }
    _write(out_path, evidence)
    tr_out_path.parent.mkdir(parents=True, exist_ok=True)
    tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")

    started = time.perf_counter()
    fidelity, fidelity_meta = _structured_call(
        api_key=key,
        model=FIDELITY_MODEL,
        system=FIDELITY_SYSTEM,
        payload={
            "source_language": "en",
            "target_language": "tr",
            "exact_age": 12,
            "source_story": english,
            "translation": translation,
        },
        seed=2026093010,
        request_class="defect_locator",
        max_tokens=2200,
    )
    fidelity_latency = round(time.perf_counter() - started, 3)
    stage_calls = _meta_calls(
        stage="final_fidelity_v3",
        model=FIDELITY_MODEL,
        meta=fidelity_meta,
        latency_seconds=fidelity_latency,
    )
    calls.extend(stage_calls)
    recovery_calls.extend(stage_calls)

    flagged = _blocking(list(fidelity.get("findings") or []))
    evidence["fidelity"] = {
        "result": fidelity,
        "latency_seconds": fidelity_latency,
        "flagged_findings": flagged,
    }
    evidence["pipeline_usage_rollup"] = rollup_model_calls(calls)
    evidence["recovery_usage_rollup"] = rollup_model_calls(recovery_calls)
    _write(out_path, evidence)

    confirmed: list[dict[str, Any]]
    basis: str
    if bool(fidelity.get("fidelity_clean")) and not flagged:
        confirmed = []
        basis = "direct_fidelity_clean"
    elif flagged:
        started = time.perf_counter()
        adjudication, adjudication_meta = _structured_call(
            api_key=key,
            model=FIDELITY_MODEL,
            system=ADJUDICATION_SYSTEM,
            payload={
                "source_story": english,
                "translation": translation,
                "flagged_findings": flagged,
            },
            seed=2026093011,
            request_class="defect_locator",
            max_tokens=2200,
        )
        adjudication_latency = round(time.perf_counter() - started, 3)
        adj_calls = _meta_calls(
            stage="final_fidelity_adjudication_v3",
            model=FIDELITY_MODEL,
            meta=adjudication_meta,
            latency_seconds=adjudication_latency,
        )
        calls.extend(adj_calls)
        recovery_calls.extend(adj_calls)
        evaluations = list(adjudication.get("evaluations") or [])
        if len(evaluations) != len(flagged):
            raise RuntimeError("V3 adjudication did not evaluate every flagged finding.")
        confirmed = _blocking(list(adjudication.get("confirmed_findings") or []))
        evidence["adjudication"] = {
            "result": adjudication,
            "latency_seconds": adjudication_latency,
            "confirmed_findings": confirmed,
        }
        basis = "contextual_adjudication"
    else:
        confirmed = []
        basis = "no_blocking_findings"

    total = rollup_model_calls(calls)
    recovery = rollup_model_calls(recovery_calls)
    notation_pass = bool(evidence["deterministic_checks"]["notation_alignment_pass"])
    ready = notation_pass and not confirmed

    evidence.update({
        "status": "publication_ready" if ready else "translation_rejected",
        "publication_ready": ready,
        "turkish_delivery_story": translation,
        "turkish_word_count": count_words(translation),
        "final_fidelity_gate": {
            "pass": ready,
            "basis": basis,
            "confirmed_findings": confirmed,
        },
        "pipeline_usage_rollup": total,
        "recovery_usage_rollup": recovery,
        "total_cost_usd": total["totals"]["cost_usd"],
        "v3_recovery_cost_usd": recovery["totals"]["cost_usd"],
    })
    _write(out_path, evidence)

    if not ready:
        raise RuntimeError(
            f"Final V3 delivery is not publication ready: notation_pass={notation_pass}, "
            f"confirmed_findings={len(confirmed)}"
        )

    en_out_path.parent.mkdir(parents=True, exist_ok=True)
    en_out_path.write_text(english.rstrip() + "\n", encoding="utf-8")
    tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")

    print(json.dumps({
        "status": evidence["status"],
        "publication_ready": evidence["publication_ready"],
        "english_word_count": evidence["english_word_count"],
        "turkish_word_count": evidence["turkish_word_count"],
        "confirmed_fidelity_findings": len(confirmed),
        "p_notation_count": evidence["deterministic_checks"]["p_notation_count"],
        "g_notation_count": evidence["deterministic_checks"]["g_notation_count"],
        "v3_recovery_cost_usd": evidence["v3_recovery_cost_usd"],
        "total_cost_usd": evidence["total_cost_usd"],
        "total_tokens": total["totals"]["total_tokens"],
        "model_latency_seconds": total["totals"]["latency_seconds"],
    }, ensure_ascii=False, indent=2))
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--en-out", type=Path, default=DEFAULT_EN_OUT)
    parser.add_argument("--tr-out", type=Path, default=DEFAULT_TR_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        out_path=args.out,
        en_out_path=args.en_out,
        tr_out_path=args.tr_out,
    )


if __name__ == "__main__":
    main()
