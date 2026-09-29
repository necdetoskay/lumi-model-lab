from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.episode_postprocess_v2 import _hard_constraints, _validate_source
from src.generate import call_openrouter, count_words, parse_cost
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.storyforge.runtime import FIDELITY_SYSTEM, TRANSLATION_SYSTEM, _structured_call
from src.translation_fidelity_recovery import (
    ADJUDICATION_SYSTEM,
    TRANSLATION_REPAIR_SYSTEM,
    _apply_repairs,
    _blocking,
    _meta_calls,
)

TRANSLATOR_MODEL = "google/gemini-3.8-flash"
FIDELITY_MODEL = "openai/gpt-5.6-luna"

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v4.json"
)
DEFAULT_APPROVED = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_p27_approved.json"
)
DEFAULT_CLEAN_GATE = Path(
    "data/specifications/story_lab/sonnet55_final_compact_authority_gate_run_36566995937.json"
)
DEFAULT_OUT = Path("runs/sonnet55-final-delivery-v2/result.json")
DEFAULT_EN_OUT = Path("runs/sonnet55-final-delivery-v2/final_en.txt")
DEFAULT_TR_OUT = Path("runs/sonnet55-final-delivery-v2/final_tr.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _checkpoint(
    *,
    evidence: dict[str, Any],
    calls: list[dict[str, Any]],
    delivery_calls: list[dict[str, Any]],
    out_path: Path,
    status: str,
    translation: str | None = None,
) -> None:
    evidence["status"] = status
    if translation is not None:
        evidence["turkish_delivery_story"] = translation
        evidence["turkish_word_count"] = count_words(translation)
    total = rollup_model_calls(calls)
    delivery = rollup_model_calls(delivery_calls)
    evidence["pipeline_usage_rollup"] = total
    evidence["delivery_usage_rollup"] = delivery
    evidence["total_cost_usd"] = total["totals"]["cost_usd"]
    evidence["delivery_cost_usd"] = delivery["totals"]["cost_usd"]
    _write(out_path, evidence)


def run(
    *,
    source_path: Path,
    approved_path: Path,
    clean_gate_path: Path,
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
    approved = _read(approved_path)
    clean_gate = _read(clean_gate_path)
    _validate_source(source, approved)

    if clean_gate.get("status") != "completed" or not bool(clean_gate.get("pass")):
        raise RuntimeError("Final compact authority gate must be GREEN before translation.")
    if clean_gate.get("findings"):
        raise RuntimeError("Final compact authority gate contains findings.")

    require_qualification_runtime_profile(TRANSLATOR_MODEL)
    require_qualification_runtime_profile(FIDELITY_MODEL)

    english = str(source["english_story"]).strip()
    spine = approved["episode_spine"]
    exact_age = int(spine["exact_age"])
    hard_constraints = _hard_constraints(spine)

    source_calls = list((clean_gate.get("pipeline_usage_rollup") or {}).get("calls") or [])
    calls = list(source_calls)
    delivery_calls: list[dict[str, Any]] = []

    evidence: dict[str, Any] = {
        "schema_version": "sonnet55-final-delivery-v2.evidence.v1",
        "status": "initialized",
        "publication_ready": False,
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "english_clean_gate_run_id": 36566995937,
        "models": {
            "translation": TRANSLATOR_MODEL,
            "fidelity": FIDELITY_MODEL,
        },
        "accepted_english_master": english,
        "english_word_count": count_words(english),
        "translation_attempts": [],
        "fidelity_cycles": [],
        "adjudication_cycles": [],
        "applied_translation_repairs": [],
    }
    _checkpoint(
        evidence=evidence,
        calls=calls,
        delivery_calls=delivery_calls,
        out_path=out_path,
        status="translation_start",
    )

    translation_input = {
        "exact_age": exact_age,
        "hard_constraints": hard_constraints,
        "accepted_english_master": english,
    }
    started = time.perf_counter()
    translation, tr_body, tr_request = call_openrouter(
        api_key=key,
        model=TRANSLATOR_MODEL,
        system_prompt=TRANSLATION_SYSTEM,
        user_prompt=json.dumps(translation_input, ensure_ascii=False),
        temperature=0.2,
        max_tokens=8000,
        seed=2026092980,
        request_class="translation",
        structured_output=False,
    )
    tr_latency = round(time.perf_counter() - started, 3)
    tr_call = normalize_model_call(
        stage="translation",
        model=TRANSLATOR_MODEL,
        provider=runtime_profile_identity(TRANSLATOR_MODEL).get("provider"),
        raw_usage=tr_body.get("usage") or {},
        cost=parse_cost(tr_body).model_dump(mode="json"),
        latency_seconds=tr_latency,
    )
    calls.append(tr_call)
    delivery_calls.append(tr_call)
    evidence["translation_attempts"].append({
        "stage": "translation",
        "latency_seconds": tr_latency,
        "request": {
            "temperature": tr_request.get("temperature"),
            "max_tokens": tr_request.get("max_tokens"),
            "reasoning": tr_request.get("reasoning"),
        },
        "word_count": count_words(translation),
    })
    _checkpoint(
        evidence=evidence,
        calls=calls,
        delivery_calls=delivery_calls,
        out_path=out_path,
        status="translation_complete",
        translation=translation,
    )
    tr_out_path.parent.mkdir(parents=True, exist_ok=True)
    tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")

    for cycle in range(0, 4):
        fidelity_stage = "fidelity" if cycle == 0 else f"fidelity_recheck_{cycle}"
        started = time.perf_counter()
        fidelity, fidelity_meta = _structured_call(
            api_key=key,
            model=FIDELITY_MODEL,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language": "en",
                "target_language": "tr",
                "exact_age": exact_age,
                "hard_constraints": hard_constraints,
                "source_story": english,
                "translation": translation,
            },
            seed=2026092981 + cycle,
            request_class="defect_locator",
            max_tokens=2200,
        )
        fidelity_latency = round(time.perf_counter() - started, 3)
        stage_calls = _meta_calls(
            stage=fidelity_stage,
            model=FIDELITY_MODEL,
            meta=fidelity_meta,
            latency_seconds=fidelity_latency,
        )
        calls.extend(stage_calls)
        delivery_calls.extend(stage_calls)

        flagged = _blocking(list(fidelity.get("findings") or []))
        evidence["fidelity_cycles"].append({
            "cycle": cycle,
            "stage": fidelity_stage,
            "result": fidelity,
            "latency_seconds": fidelity_latency,
            "flagged_findings": flagged,
        })
        _checkpoint(
            evidence=evidence,
            calls=calls,
            delivery_calls=delivery_calls,
            out_path=out_path,
            status=f"{fidelity_stage}_complete",
            translation=translation,
        )

        if bool(fidelity.get("fidelity_clean")) and not flagged:
            confirmed: list[dict[str, Any]] = []
        elif flagged:
            adjudication_stage = f"fidelity_adjudication_{cycle}"
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
                seed=2026092990 + cycle,
                request_class="defect_locator",
                max_tokens=2200,
            )
            adjudication_latency = round(time.perf_counter() - started, 3)
            adj_calls = _meta_calls(
                stage=adjudication_stage,
                model=FIDELITY_MODEL,
                meta=adjudication_meta,
                latency_seconds=adjudication_latency,
            )
            calls.extend(adj_calls)
            delivery_calls.extend(adj_calls)

            evaluations = list(adjudication.get("evaluations") or [])
            if len(evaluations) != len(flagged):
                raise RuntimeError("Fidelity adjudication did not evaluate every flagged finding.")
            confirmed = _blocking(list(adjudication.get("confirmed_findings") or []))
            adj_clean = bool(adjudication.get("fidelity_clean")) and not confirmed
            evidence["adjudication_cycles"].append({
                "cycle": cycle,
                "stage": adjudication_stage,
                "result": adjudication,
                "latency_seconds": adjudication_latency,
                "pass": adj_clean,
            })
            _checkpoint(
                evidence=evidence,
                calls=calls,
                delivery_calls=delivery_calls,
                out_path=out_path,
                status=f"{adjudication_stage}_complete",
                translation=translation,
            )
            if adj_clean:
                confirmed = []
        else:
            confirmed = []

        if not confirmed:
            total = rollup_model_calls(calls)
            delivery = rollup_model_calls(delivery_calls)
            evidence.update({
                "status": "publication_ready",
                "publication_ready": True,
                "turkish_delivery_story": translation,
                "turkish_word_count": count_words(translation),
                "final_fidelity_gate": {
                    "pass": True,
                    "basis": (
                        "direct_fidelity_clean"
                        if bool(fidelity.get("fidelity_clean")) and not flagged
                        else "contextual_adjudication"
                    ),
                    "confirmed_findings": [],
                },
                "pipeline_usage_rollup": total,
                "delivery_usage_rollup": delivery,
                "total_cost_usd": total["totals"]["cost_usd"],
                "delivery_cost_usd": delivery["totals"]["cost_usd"],
            })
            _write(out_path, evidence)
            en_out_path.parent.mkdir(parents=True, exist_ok=True)
            en_out_path.write_text(english.rstrip() + "\n", encoding="utf-8")
            tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")
            print(json.dumps({
                "status": "publication_ready",
                "english_word_count": evidence["english_word_count"],
                "turkish_word_count": evidence["turkish_word_count"],
                "translation_repairs": len(evidence["applied_translation_repairs"]),
                "delivery_cost_usd": evidence["delivery_cost_usd"],
                "total_cost_usd": evidence["total_cost_usd"],
                "total_tokens": total["totals"]["total_tokens"],
                "model_latency_seconds": total["totals"]["latency_seconds"],
            }, ensure_ascii=False, indent=2))
            return evidence

        if cycle >= 3:
            break

        repair_stage = f"translation_repair_{cycle + 1}"
        started = time.perf_counter()
        repair_payload, repair_meta = _structured_call(
            api_key=key,
            model=TRANSLATOR_MODEL,
            system=TRANSLATION_REPAIR_SYSTEM,
            payload={
                "accepted_english_master": english,
                "turkish_translation": translation,
                "confirmed_fidelity_defects": confirmed,
            },
            seed=2026093000 + cycle,
            request_class="translation",
            max_tokens=2200,
        )
        repair_latency = round(time.perf_counter() - started, 3)
        rep_calls = _meta_calls(
            stage=repair_stage,
            model=TRANSLATOR_MODEL,
            meta=repair_meta,
            latency_seconds=repair_latency,
        )
        calls.extend(rep_calls)
        delivery_calls.extend(rep_calls)

        translation, applied = _apply_repairs(translation, repair_payload)
        evidence["applied_translation_repairs"].extend(
            [{**row, "repair_cycle": cycle + 1} for row in applied]
        )
        _checkpoint(
            evidence=evidence,
            calls=calls,
            delivery_calls=delivery_calls,
            out_path=out_path,
            status=f"{repair_stage}_complete",
            translation=translation,
        )
        tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")

    total = rollup_model_calls(calls)
    delivery = rollup_model_calls(delivery_calls)
    evidence.update({
        "status": "translation_rejected",
        "publication_ready": False,
        "pipeline_usage_rollup": total,
        "delivery_usage_rollup": delivery,
        "total_cost_usd": total["totals"]["cost_usd"],
        "delivery_cost_usd": delivery["totals"]["cost_usd"],
    })
    _write(out_path, evidence)
    raise RuntimeError("Translation fidelity remained blocked after maximum bounded cycles.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved", type=Path, default=DEFAULT_APPROVED)
    parser.add_argument("--clean-gate", type=Path, default=DEFAULT_CLEAN_GATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--en-out", type=Path, default=DEFAULT_EN_OUT)
    parser.add_argument("--tr-out", type=Path, default=DEFAULT_TR_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        approved_path=args.approved,
        clean_gate_path=args.clean_gate,
        out_path=args.out,
        en_out_path=args.en_out,
        tr_out_path=args.tr_out,
    )


if __name__ == "__main__":
    main()
