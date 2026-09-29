from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_defect_detection import segment_story
from src.storyforge.runtime import (
    AUDIT_SYSTEM,
    FIDELITY_SYSTEM,
    REPAIR_SYSTEM,
    TRANSLATION_SYSTEM,
    _apply_local_repairs,
    _dedupe_findings,
    _normalize_audit,
    _structured_call,
)

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_writer_run_36526379349.json"
)
DEFAULT_SPINE = Path(
    "data/specifications/story_lab/age12_episode1_spine_revision_05_approved.json"
)
DEFAULT_OUT = Path("runs/episode-postprocess-v2-age12/result.json")
DEFAULT_EN_OUT = Path("runs/episode-postprocess-v2-age12/accepted_en.txt")
DEFAULT_TR_OUT = Path("runs/episode-postprocess-v2-age12/delivery_tr.txt")

PRIMARY_MODEL = "anthropic/claude-sonnet-5"
SECONDARY_MODEL = "openai/gpt-5.6-sol"
REPAIR_MODEL = "openai/gpt-5.6-sol"
TRANSLATOR_MODEL = "google/gemini-3.8-flash"
FIDELITY_MODEL = "openai/gpt-5.6-luna"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hard_constraints(spine: dict[str, Any]) -> list[str]:
    out = list(spine.get("writer_rules") or [])
    reversal = spine.get("reversal") or {}
    ceiling = str(reversal.get("inference_ceiling") or "").strip()
    unresolved = str(reversal.get("unresolved_after_reversal") or "").strip()
    if ceiling:
        out.append("INFERENCE CEILING: " + ceiling)
    if unresolved:
        out.append("MUST REMAIN UNRESOLVED: " + unresolved)
    return out


def _call_from_meta(
    *,
    stage: str,
    model: str,
    meta: dict[str, Any],
    latency_seconds: float,
) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    failures = meta.get("parse_failures") or []
    for idx, row in enumerate(failures, start=1):
        calls.append(
            normalize_model_call(
                stage=f"{stage}_format_attempt_{idx}",
                model=model,
                provider=runtime_profile_identity(model).get("provider"),
                raw_usage=row.get("raw_usage") or {},
                cost=row.get("cost") or {},
                latency_seconds=None,
                status="parse_failed",
                attempt=idx,
            )
        )
    calls.append(
        normalize_model_call(
            stage=stage,
            model=model,
            provider=runtime_profile_identity(model).get("provider"),
            raw_usage=meta.get("raw_usage") or {},
            cost=meta.get("cost") or {},
            latency_seconds=latency_seconds,
            attempt=len(failures) + 1,
        )
    )
    return calls


def _audit_once(
    *,
    api_key: str,
    stage: str,
    model: str,
    story: str,
    approved: dict[str, Any],
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], float, list[dict[str, Any]]]:
    spine = approved["episode_spine"]
    segments = segment_story(story)
    started = time.perf_counter()
    payload, meta = _structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={
            "story_intent": approved["approved_premise"]["premise"],
            "hard_constraints": _hard_constraints(spine),
            "context_packet": approved["projection"],
            "validated_spine": spine,
            "story_segments": segments,
        },
        seed=seed,
        request_class="editorial_audit",
        max_tokens=2800,
    )
    latency = round(time.perf_counter() - started, 3)
    findings = _normalize_audit(payload, segments)
    calls = _call_from_meta(stage=stage, model=model, meta=meta, latency_seconds=latency)
    return findings, meta, latency, calls


def _validate_source(source: dict[str, Any], approved: dict[str, Any]) -> None:
    if source.get("schema_version") != "episode-postprocess-source.v1":
        raise RuntimeError("Postprocess source schema mismatch.")
    if int(source.get("source_spine_run_id") or 0) != int(approved.get("source_run_id") or -1):
        raise RuntimeError("Writer source and approved spine run mismatch.")
    if not str(source.get("english_story") or "").strip():
        raise RuntimeError("Writer source story is empty.")
    checks = source.get("deterministic_checks") or {}
    if checks.get("length_pass") is not True:
        raise RuntimeError("Writer source did not pass deterministic length gate.")
    if (approved.get("human_review") or {}).get("verdict") != "APPROVE":
        raise RuntimeError("Spine human approval is missing.")
    if (approved.get("gate") or {}).get("decision") != "ACCEPT":
        raise RuntimeError("Spine semantic gate is not ACCEPT.")


def run(
    *,
    source_path: Path,
    approved_spine_path: Path,
    out_path: Path,
    en_out_path: Path,
    tr_out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    source = _read_json(source_path)
    approved = _read_json(approved_spine_path)
    _validate_source(source, approved)

    for model in (
        PRIMARY_MODEL,
        SECONDARY_MODEL,
        REPAIR_MODEL,
        TRANSLATOR_MODEL,
        FIDELITY_MODEL,
    ):
        require_qualification_runtime_profile(model)

    story = str(source["english_story"]).strip()
    spine = approved["episode_spine"]
    min_words = int(spine["target_words_min"])
    max_words = int(spine["target_words_max"])
    calls: list[dict[str, Any]] = list(
        (source.get("source_pipeline_usage_rollup") or {}).get("calls") or []
    )
    evidence: dict[str, Any] = {
        "schema_version": "episode-postprocess-v2-evidence.v1",
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "models": {
            "primary_audit": PRIMARY_MODEL,
            "secondary_audit": SECONDARY_MODEL,
            "repair": REPAIR_MODEL,
            "translation": TRANSLATOR_MODEL,
            "fidelity": FIDELITY_MODEL,
        },
        "stage_latency_seconds": {},
        "audit_cycles": [],
        "applied_repairs": [],
    }

    seed = 2026092910

    primary, primary_meta, primary_latency, primary_calls = _audit_once(
        api_key=key,
        stage="primary_audit",
        model=PRIMARY_MODEL,
        story=story,
        approved=approved,
        seed=seed,
    )
    calls.extend(primary_calls)
    evidence["stage_latency_seconds"]["primary_audit"] = primary_latency

    secondary, secondary_meta, secondary_latency, secondary_calls = _audit_once(
        api_key=key,
        stage="secondary_audit",
        model=SECONDARY_MODEL,
        story=story,
        approved=approved,
        seed=seed + 1,
    )
    calls.extend(secondary_calls)
    evidence["stage_latency_seconds"]["secondary_audit"] = secondary_latency
    findings = _dedupe_findings(primary, secondary)
    evidence["initial_audit"] = {
        "primary_findings": primary,
        "secondary_findings": secondary,
        "primary_meta": primary_meta,
        "secondary_meta": secondary_meta,
    }

    for cycle in range(1, 4):
        if not findings:
            break
        if any(row["repair_scope"] != "local" for row in findings):
            rollup = rollup_model_calls(calls)
            evidence["status"] = "story_rejected_non_local"
            evidence["blocking_findings"] = findings
            evidence["pipeline_usage_rollup"] = rollup
            evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
            _write_json(out_path, evidence)
            return evidence

        repair_stage = "repair" if cycle == 1 else f"repair_{cycle}"
        started = time.perf_counter()
        repair_payload, repair_meta = _structured_call(
            api_key=key,
            model=REPAIR_MODEL,
            system=REPAIR_SYSTEM,
            payload={
                "story_intent": approved["approved_premise"]["premise"],
                "context_packet": approved["projection"],
                "hard_constraints": _hard_constraints(spine),
                "validated_spine": spine,
                "story": story,
                "confirmed_local_defects": findings,
                "repair_cycle": cycle,
                "max_repair_cycles": 3,
            },
            seed=seed + 2 + ((cycle - 1) * 3),
            request_class="editorial_audit",
            max_tokens=1800,
        )
        repair_latency = round(time.perf_counter() - started, 3)
        evidence["stage_latency_seconds"][repair_stage] = repair_latency
        calls.extend(
            _call_from_meta(
                stage=repair_stage,
                model=REPAIR_MODEL,
                meta=repair_meta,
                latency_seconds=repair_latency,
            )
        )
        before = story
        story, cycle_repairs = _apply_local_repairs(story, repair_payload)
        evidence["applied_repairs"].extend(
            [{**row, "repair_cycle": cycle} for row in cycle_repairs]
        )

        p_stage = f"primary_reaudit_{cycle}"
        s_stage = f"secondary_reaudit_{cycle}"
        primary, pmeta, plat, pcalls = _audit_once(
            api_key=key,
            stage=p_stage,
            model=PRIMARY_MODEL,
            story=story,
            approved=approved,
            seed=seed + 3 + ((cycle - 1) * 3),
        )
        secondary, smeta, slat, scalls = _audit_once(
            api_key=key,
            stage=s_stage,
            model=SECONDARY_MODEL,
            story=story,
            approved=approved,
            seed=seed + 4 + ((cycle - 1) * 3),
        )
        calls.extend(pcalls)
        calls.extend(scalls)
        evidence["stage_latency_seconds"][p_stage] = plat
        evidence["stage_latency_seconds"][s_stage] = slat
        findings = _dedupe_findings(primary, secondary)
        evidence["audit_cycles"].append(
            {
                "cycle": cycle,
                "story_changed": story != before,
                "applied_repairs": cycle_repairs,
                "primary_findings_after": primary,
                "secondary_findings_after": secondary,
                "findings_after": findings,
                "primary_meta": pmeta,
                "secondary_meta": smeta,
            }
        )

    final_en_words = count_words(story)
    if findings or not (min_words <= final_en_words <= max_words):
        rollup = rollup_model_calls(calls)
        evidence["status"] = "story_rejected_after_repairs"
        evidence["blocking_findings"] = findings
        evidence["english_word_count"] = final_en_words
        evidence["pipeline_usage_rollup"] = rollup
        evidence["total_cost_usd"] = rollup["totals"]["cost_usd"]
        _write_json(out_path, evidence)
        return evidence

    evidence["english_gate"] = {
        "pass": True,
        "word_count": final_en_words,
        "hard_range": [min_words, max_words],
        "primary_findings": primary,
        "secondary_findings": secondary,
    }

    translation_input = {
        "exact_age": int(spine["exact_age"]),
        "hard_constraints": _hard_constraints(spine),
        "accepted_english_master": story,
    }
    started = time.perf_counter()
    tr_story, tr_body, tr_request = call_openrouter(
        api_key=key,
        model=TRANSLATOR_MODEL,
        system_prompt=TRANSLATION_SYSTEM,
        user_prompt=json.dumps(translation_input, ensure_ascii=False),
        temperature=0.2,
        max_tokens=None,
        seed=seed + 20,
        request_class="translation",
        structured_output=False,
    )
    tr_latency = round(time.perf_counter() - started, 3)
    evidence["stage_latency_seconds"]["translation"] = tr_latency
    calls.append(
        normalize_model_call(
            stage="translation",
            model=TRANSLATOR_MODEL,
            provider=runtime_profile_identity(TRANSLATOR_MODEL).get("provider"),
            raw_usage=tr_body.get("usage") or {},
            cost=parse_cost(tr_body).model_dump(mode="json"),
            latency_seconds=tr_latency,
        )
    )

    started = time.perf_counter()
    fidelity, fidelity_meta = _structured_call(
        api_key=key,
        model=FIDELITY_MODEL,
        system=FIDELITY_SYSTEM,
        payload={
            "source_language": "en",
            "target_language": "tr",
            "exact_age": int(spine["exact_age"]),
            "hard_constraints": _hard_constraints(spine),
            "source_story": story,
            "translation": tr_story,
        },
        seed=seed + 21,
        request_class="editorial_audit",
        max_tokens=1800,
    )
    fidelity_latency = round(time.perf_counter() - started, 3)
    evidence["stage_latency_seconds"]["fidelity"] = fidelity_latency
    calls.extend(
        _call_from_meta(
            stage="fidelity",
            model=FIDELITY_MODEL,
            meta=fidelity_meta,
            latency_seconds=fidelity_latency,
        )
    )

    blocking_fidelity = [
        row
        for row in (fidelity.get("findings") or [])
        if str(row.get("severity") or "") in {"serious", "critical"}
    ]
    fidelity_pass = bool(fidelity.get("fidelity_clean")) and not blocking_fidelity

    rollup = rollup_model_calls(calls)
    evidence.update(
        {
            "status": "publication_ready" if fidelity_pass else "translation_rejected",
            "publication_ready": fidelity_pass,
            "accepted_english_master": story,
            "turkish_delivery_story": tr_story,
            "turkish_word_count": count_words(tr_story),
            "translation_request": {
                "temperature": tr_request.get("temperature"),
                "max_tokens": tr_request.get("max_tokens"),
                "reasoning": tr_request.get("reasoning"),
            },
            "fidelity_gate": {
                "pass": fidelity_pass,
                "result": fidelity,
                "meta": fidelity_meta,
            },
            "pipeline_usage_rollup": rollup,
            "total_cost_usd": rollup["totals"]["cost_usd"],
        }
    )
    _write_json(out_path, evidence)
    en_out_path.parent.mkdir(parents=True, exist_ok=True)
    en_out_path.write_text(story.rstrip() + "\n", encoding="utf-8")
    tr_out_path.parent.mkdir(parents=True, exist_ok=True)
    tr_out_path.write_text(tr_story.rstrip() + "\n", encoding="utf-8")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--approved-spine", type=Path, default=DEFAULT_SPINE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--en-out", type=Path, default=DEFAULT_EN_OUT)
    parser.add_argument("--tr-out", type=Path, default=DEFAULT_TR_OUT)
    args = parser.parse_args()

    result = run(
        source_path=args.source,
        approved_spine_path=args.approved_spine,
        out_path=args.out,
        en_out_path=args.en_out,
        tr_out_path=args.tr_out,
    )
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "publication_ready": result.get("publication_ready", False),
                "english_word_count": (result.get("english_gate") or {}).get("word_count"),
                "turkish_word_count": result.get("turkish_word_count"),
                "repairs": len(result.get("applied_repairs") or []),
                "fidelity_pass": (result.get("fidelity_gate") or {}).get("pass"),
                "usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if result.get("status") not in {"publication_ready"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
