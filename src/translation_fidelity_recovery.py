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

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_translation_recovery_36528435261.json"
)
DEFAULT_OUT = Path("runs/translation-fidelity-recovery-age12/result.json")
DEFAULT_TR_OUT = Path("runs/translation-fidelity-recovery-age12/final_tr.txt")

FIDELITY_MODEL = "openai/gpt-5.6-luna"
TRANSLATOR_MODEL = "google/gemini-3.8-flash"

ADJUDICATION_SYSTEM = r"""
You are the final adjudicator for previously flagged EN->TR semantic fidelity findings.

You receive:
- the complete English source story,
- the complete Turkish translation,
- findings from an earlier narrow fidelity pass.

Your task is NOT to search for new defects.
Re-evaluate ONLY the supplied findings in their surrounding context.

A finding remains blocking only when the Turkish passage materially changes, omits, or adds
story meaning at serious/critical severity. Judge meaning across the local passage, not one
sentence in isolation. If information is clearly preserved in an adjacent sentence, do not
call it an omission. If the supplied finding's own rationale describes the issue as minor,
it cannot remain a serious/critical blocker.

Ignore stylistic preference, literalness, terminology polish, and harmless phrasing.

Return JSON only:
{
  "evaluations":[
    {
      "finding_index":0,
      "blocking":false,
      "severity":null,
      "why":"brief context-aware reason"
    }
  ],
  "confirmed_findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"exact supplied source quote",
      "translation_quote":"exact supplied translation quote",
      "why":"brief"
    }
  ],
  "fidelity_clean":true
}

Rules:
- Include exactly one evaluation for every supplied finding index.
- confirmed_findings contains only findings whose evaluation has blocking=true.
- fidelity_clean must be true iff confirmed_findings is empty.
""".strip()

TRANSLATION_REPAIR_SYSTEM = r"""
You are the bounded EN->TR fidelity repair editor inside LUMI.

You receive an accepted English master, its Turkish translation, and confirmed
serious/critical fidelity defects.

Do NOT retranslate the whole story.
Return the smallest exact Turkish substring replacements needed to remove ONLY the
confirmed defects.

Rules:
- old must be an exact unique substring of the supplied Turkish translation.
- new must preserve natural Turkish and the 12-year-old reading level.
- do not add plot events, explanations, motivations, canon, morals, or stylistic rewrites.
- preserve names, objects, state, causality, knowledge boundaries, and ending.
- repairs must address only confirmed findings.

Return JSON only:
{
  "repairs":[
    {
      "old":"exact Turkish substring",
      "new":"minimal corrected Turkish substring",
      "why":"brief"
    }
  ]
}
""".strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _meta_calls(
    *,
    stage: str,
    model: str,
    meta: dict[str, Any],
    latency_seconds: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    failures = meta.get("parse_failures") or []
    for idx, row in enumerate(failures, start=1):
        out.append(
            normalize_model_call(
                stage=f"{stage}_format_attempt_{idx}",
                model=model,
                provider=runtime_profile_identity(model).get("provider"),
                raw_usage=row.get("raw_usage") or {},
                cost=row.get("cost") or {},
                status="parse_failed",
                attempt=idx,
            )
        )
    out.append(
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
    return out


def _apply_repairs(text: str, payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    current = text
    applied: list[dict[str, Any]] = []
    repairs = payload.get("repairs") or []
    if not repairs:
        raise RuntimeError("Translation repair returned no replacements.")
    for row in repairs:
        old = str(row.get("old") or "")
        new = str(row.get("new") or "")
        if not old or not new or old == new:
            raise RuntimeError("Invalid empty/no-op translation repair.")
        if current.count(old) != 1:
            raise RuntimeError("Translation repair target must exist exactly once.")
        current = current.replace(old, new, 1)
        applied.append({"old": old, "new": new, "why": str(row.get("why") or "")})
    return current, applied


def _blocking(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in findings
        if str(row.get("severity") or "") in {"serious", "critical"}
    ]


def run(
    *,
    source_path: Path,
    out_path: Path,
    tr_out_path: Path,
    api_key: str | None = None,
) -> dict[str, Any]:
    load_dotenv()
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    require_qualification_runtime_profile(FIDELITY_MODEL)
    require_qualification_runtime_profile(TRANSLATOR_MODEL)

    source = _read_json(source_path)
    if source.get("schema_version") != "translation-fidelity-recovery-source.v1":
        raise RuntimeError("Recovery source schema mismatch.")

    english = str(source.get("accepted_english_master") or "").strip()
    translation = str(source.get("turkish_delivery_story") or "").strip()
    original_gate = source.get("original_fidelity_gate") or {}
    original_result = original_gate.get("result") or {}
    original_findings = list(original_result.get("findings") or [])
    if not english or not translation or not original_findings:
        raise RuntimeError("Recovery source is missing stories or fidelity findings.")

    source_calls = list(source.get("source_pipeline_calls") or [])
    calls = list(source_calls)
    recovery_calls: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "schema_version": "translation-fidelity-recovery-evidence.v1",
        "source_postprocess_run_id": source["source_postprocess_run_id"],
        "source_writer_run_id": source["source_writer_run_id"],
        "source_spine_run_id": source["source_spine_run_id"],
        "original_fidelity_findings": original_findings,
        "applied_translation_repairs": [],
        "cycles": [],
    }

    started = time.perf_counter()
    adjudication, meta = _structured_call(
        api_key=key,
        model=FIDELITY_MODEL,
        system=ADJUDICATION_SYSTEM,
        payload={
            "source_story": english,
            "translation": translation,
            "flagged_findings": original_findings,
        },
        seed=2026092940,
        request_class="defect_locator",
        max_tokens=None,
    )
    latency = round(time.perf_counter() - started, 3)
    stage_calls = _meta_calls(
        stage="fidelity_adjudication",
        model=FIDELITY_MODEL,
        meta=meta,
        latency_seconds=latency,
    )
    calls.extend(stage_calls)
    recovery_calls.extend(stage_calls)

    evaluations = adjudication.get("evaluations") or []
    confirmed = list(adjudication.get("confirmed_findings") or [])
    if len(evaluations) != len(original_findings):
        raise RuntimeError("Fidelity adjudication did not evaluate every original finding.")
    adjudication_clean = bool(adjudication.get("fidelity_clean")) and not _blocking(confirmed)
    evidence["adjudication"] = {
        "result": adjudication,
        "meta": meta,
        "pass": adjudication_clean,
        "latency_seconds": latency,
    }

    if adjudication_clean:
        final_rollup = rollup_model_calls(calls)
        recovery_rollup = rollup_model_calls(recovery_calls)
        evidence.update(
            {
                "status": "publication_ready",
                "publication_ready": True,
                "accepted_english_master": english,
                "turkish_delivery_story": translation,
                "final_fidelity_gate": {
                    "pass": True,
                    "basis": "contextual_adjudication_of_original_findings",
                    "confirmed_findings": [],
                },
                "recovery_usage_rollup": recovery_rollup,
                "pipeline_usage_rollup": final_rollup,
                "total_cost_usd": final_rollup["totals"]["cost_usd"],
            }
        )
        _write_json(out_path, evidence)
        tr_out_path.parent.mkdir(parents=True, exist_ok=True)
        tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")
        return evidence

    confirmed = _blocking(confirmed)
    if not confirmed:
        raise RuntimeError("Adjudication is internally inconsistent.")

    for cycle in range(1, 3):
        repair_stage = f"translation_repair_{cycle}"
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
            seed=2026092940 + cycle,
            request_class="translation",
            max_tokens=1800,
        )
        repair_latency = round(time.perf_counter() - started, 3)
        stage_calls = _meta_calls(
            stage=repair_stage,
            model=TRANSLATOR_MODEL,
            meta=repair_meta,
            latency_seconds=repair_latency,
        )
        calls.extend(stage_calls)
        recovery_calls.extend(stage_calls)
        translation, applied = _apply_repairs(translation, repair_payload)
        evidence["applied_translation_repairs"].extend(
            [{**row, "repair_cycle": cycle} for row in applied]
        )

        fidelity_stage = f"fidelity_recheck_{cycle}"
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
            seed=2026092950 + cycle,
            request_class="defect_locator",
            max_tokens=None,
        )
        fidelity_latency = round(time.perf_counter() - started, 3)
        stage_calls = _meta_calls(
            stage=fidelity_stage,
            model=FIDELITY_MODEL,
            meta=fidelity_meta,
            latency_seconds=fidelity_latency,
        )
        calls.extend(stage_calls)
        recovery_calls.extend(stage_calls)
        confirmed = _blocking(list(fidelity.get("findings") or []))
        clean = bool(fidelity.get("fidelity_clean")) and not confirmed
        evidence["cycles"].append(
            {
                "cycle": cycle,
                "repairs": applied,
                "repair_meta": repair_meta,
                "repair_latency_seconds": repair_latency,
                "fidelity": fidelity,
                "fidelity_meta": fidelity_meta,
                "fidelity_latency_seconds": fidelity_latency,
                "pass": clean,
            }
        )
        if clean:
            final_rollup = rollup_model_calls(calls)
            recovery_rollup = rollup_model_calls(recovery_calls)
            evidence.update(
                {
                    "status": "publication_ready",
                    "publication_ready": True,
                    "accepted_english_master": english,
                    "turkish_delivery_story": translation,
                    "final_fidelity_gate": {"pass": True, "result": fidelity},
                    "recovery_usage_rollup": recovery_rollup,
                    "pipeline_usage_rollup": final_rollup,
                    "total_cost_usd": final_rollup["totals"]["cost_usd"],
                }
            )
            _write_json(out_path, evidence)
            tr_out_path.parent.mkdir(parents=True, exist_ok=True)
            tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")
            return evidence

    final_rollup = rollup_model_calls(calls)
    recovery_rollup = rollup_model_calls(recovery_calls)
    evidence.update(
        {
            "status": "translation_rejected",
            "publication_ready": False,
            "accepted_english_master": english,
            "turkish_delivery_story": translation,
            "final_fidelity_gate": {"pass": False, "confirmed_findings": confirmed},
            "recovery_usage_rollup": recovery_rollup,
            "pipeline_usage_rollup": final_rollup,
            "total_cost_usd": final_rollup["totals"]["cost_usd"],
        }
    )
    _write_json(out_path, evidence)
    tr_out_path.parent.mkdir(parents=True, exist_ok=True)
    tr_out_path.write_text(translation.rstrip() + "\n", encoding="utf-8")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--tr-out", type=Path, default=DEFAULT_TR_OUT)
    args = parser.parse_args()
    result = run(source_path=args.source, out_path=args.out, tr_out_path=args.tr_out)
    print(
        json.dumps(
            {
                "status": result["status"],
                "publication_ready": result["publication_ready"],
                "translation_repairs": len(result.get("applied_translation_repairs") or []),
                "recovery_usage": (result.get("recovery_usage_rollup") or {}).get("totals"),
                "pipeline_usage": (result.get("pipeline_usage_rollup") or {}).get("totals"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not result.get("publication_ready"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
