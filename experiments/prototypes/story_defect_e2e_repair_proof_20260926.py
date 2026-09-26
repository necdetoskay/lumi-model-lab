from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE = Path("experiments/fixtures/story_defect_e2e_repair_proof.v1.json")
CORPUS = Path("experiments/fixtures/story_defect_corpus.tr-age4.synthetic.v1.json")
MANIFEST = Path("experiments/fixtures/story_defect_d1_validation_manifest.tr-age4.v1.json")
SOURCE_POOL = Path("experiments/fixtures/story_defect_source_pool.tr-age4.v1.json")
CLEAN_ADMISSION = Path("experiments/fixtures/story_defect_clean_source_admission.tr-age4.v1.json")
OUT = Path("runs/story-defect-e2e-repair-proof/result.json")

DETECTOR_MODEL = "anthropic/claude-sonnet-5"
REPAIR_MODEL = "anthropic/claude-sonnet-5"
POST_VERIFY_MODEL = "anthropic/claude-haiku-4.5"
POST_ADJUDICATOR_MODEL = "openai/gpt-5.6-luna"

FAMILY_ALIASES = {
    "physical_impossible_affordance": "physical_feasibility",
    "physical_solid_barrier_violation": "physical_feasibility",
    "physical_unsupported_motion": "physical_feasibility",
    "state_object_reset": "state_continuity",
    "state_completed_action_undone": "state_continuity",
    "state_unexplained_reappearance": "state_continuity",
    "response_perception_conflation": "response_causality",
    "closure_post_terminal_action": "closure_integrity",
}

DETECTOR_SYSTEM = r"""
You are a strict publication-defect auditor for one finished Turkish read-aloud story for an exact-age-4 child.

Audit the current story on its own. You are not told whether this is a benchmark, a clean story, or a corrupted story.

Report ONLY serious or critical semantic defects in these canonical families:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Important:
- Zero findings is allowed and preferred over inventing a defect.
- Do not report grammar, style, word count, repetition, optional polish, or taste.
- Do not call ordinary fantasy a defect when the story establishes the fantasy rule.
- Do not invent hidden height, strength, distance, knowledge, or world constraints.
- response_causality means the story incorrectly uses inability/delay to respond as inability to perceive, for example "hands are full, therefore cannot hear".
- closure_integrity means the story reaches a terminal ending and then unnecessarily reopens the completed central action.
- Cite the exact supplied sentence IDs that establish the defect.
- Do not rewrite the story.

Return JSON only:
{
  "findings": [
    {
      "family": "physical_feasibility|causal_logic|state_continuity|epistemic_order|spatial_consistency|temporal_consistency|response_causality|closure_integrity|canon_integrity",
      "severity": "serious|critical",
      "span_ids": ["S001"],
      "reason": "brief evidence-based reason"
    }
  ]
}
""".strip()

REPAIR_SYSTEM = r"""
You repair exactly ONE confirmed semantic defect in an otherwise accepted Turkish read-aloud story for an exact-age-4 child.

This is a bounded local repair, not a rewrite.

Hard rules:
- You may replace ONLY the exact target_block supplied by the caller.
- Everything outside target_block is read-only and must remain unchanged.
- Preserve character names, events, object state, causal rules, tone, age fit, and ending unless the confirmed defect itself requires the local block to stop reopening the ending.
- Add no new subplot, canon, object, character, explanation, moral, or extra payoff.
- Make the smallest natural correction.
- For response_causality defects, preserve perception explicitly. Busy/full hands or task load must NEVER be used as the cause of failure to hear, speak, turn the head, or look. If the faulty call/hearing event has no downstream role, prefer deleting it. If it must remain, the character should hear and may verbally acknowledge; only a genuinely hand-dependent physical action (for example putting something down) may be delayed.
- For physical_feasibility defects, remove only the impossible action; do not invent a new mechanism unless the surrounding story already establishes it.
- For state_continuity defects, restore the previously established state or remove the unsupported reset/reappearance.
- For closure_integrity defects, prefer deleting the reopening tail when the story already has a complete ending.
- If deletion is the cleanest fix (for example an unnecessary post-closure tail), replacement_text may be an empty string.
- Do not quote or rewrite any other story text.
- Return replacement text only through the JSON field.

Return JSON only:
{
  "replacement_text": "minimal replacement, or empty string if deletion is best",
  "repair_note": "one short sentence explaining why this fixes the confirmed defect"
}
""".strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def meta_cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    cost = meta.get("cost")
    if isinstance(cost, dict) and isinstance(cost.get("usd"), (int, float)):
        return float(cost["usd"])
    if isinstance(cost, (int, float)):
        return float(cost)
    return 0.0


def normalize_findings(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise RuntimeError("findings_missing")
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(findings):
        if not isinstance(raw, dict):
            raise RuntimeError(f"finding_{index}_not_object")
        family = FAMILY_ALIASES.get(str(raw.get("family")), raw.get("family"))
        if family not in DEFECT_FAMILIES:
            raise RuntimeError(f"finding_{index}_family_invalid:{family}")
        severity = raw.get("severity") or "serious"
        if severity not in {"serious", "critical"}:
            raise RuntimeError(f"finding_{index}_severity_invalid:{severity}")
        spans = raw.get("span_ids")
        if not isinstance(spans, list) or not spans:
            raise RuntimeError(f"finding_{index}_span_missing")
        if not set(spans).issubset(valid_ids):
            raise RuntimeError(f"finding_{index}_span_invalid:{spans}")
        reason = str(raw.get("reason") or "").strip() or "[reason omitted]"
        normalized.append({
            "family": family,
            "severity": severity,
            "span_ids": spans,
            "reason": reason,
        })
    return normalized


def call_detector(
    *,
    api_key: str,
    model: str,
    story_id: str,
    story_family: str,
    story_text: str,
    seed: int,
    request_class: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    segments = segment_story(story_text)
    payload, meta = structured_call(
        api_key=api_key,
        model=model,
        system=DETECTOR_SYSTEM,
        payload={
            "story_id": story_id,
            "story_family": story_family,
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "story_segments": segments,
        },
        seed=seed,
        max_tokens=2600,
        request_class=request_class,
    )
    return normalize_findings(payload, {row["id"] for row in segments}), meta


def find_gold(manifest: dict[str, Any], case_id: str) -> dict[str, Any]:
    rows = [row for row in manifest["validated_cases"] if row["case_id"] == case_id]
    if len(rows) != 1:
        raise RuntimeError(f"gold_case_not_unique:{case_id}:{len(rows)}")
    return rows[0]


def expected_match(findings: list[dict[str, Any]], gold: dict[str, Any]) -> dict[str, Any] | None:
    gold_spans = set(gold["span_ids"])
    for finding in findings:
        if finding["family"] == gold["family"] and gold_spans.intersection(finding["span_ids"]):
            return finding
    return None


def findings_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left["family"] == right["family"]
        and bool(set(left["span_ids"]).intersection(right["span_ids"]))
    )


def build_repaired_story(story: str, target_block: str, replacement: str) -> tuple[str, dict[str, Any]]:
    count = story.count(target_block)
    if count != 1:
        raise RuntimeError(f"target_block_occurrence_count:{count}")
    prefix, suffix = story.split(target_block, 1)
    repaired = prefix + replacement + suffix
    return repaired, {
        "target_occurrences_before": count,
        "outside_target_byte_for_byte_unchanged": (
            repaired.startswith(prefix) and repaired.endswith(suffix)
        ),
        "target_block_removed": target_block not in repaired,
        "changed_character_delta": len(replacement) - len(target_block),
    }


def main() -> None:
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]

    fixture = load_json(FIXTURE)
    corpus = load_json(CORPUS)
    manifest = load_json(MANIFEST)
    source_pool = load_json(SOURCE_POOL)
    admission = load_json(CLEAN_ADMISSION)

    corpus_by_id = {row["case_id"]: row for row in corpus["cases"]}
    source_by_id = {row["source_id"]: row for row in source_pool["sources"]}
    admitted_clean = {
        row["source_id"]
        for row in admission["entries"]
        if row["admitted_as_clean_source"] is True
    }

    results: list[dict[str, Any]] = []
    total_cost = 0.0
    started = time.perf_counter()

    for index, spec in enumerate(fixture["cases"]):
        proof_id = spec["proof_id"]
        row: dict[str, Any] = {
            "proof_id": proof_id,
            "kind": spec["kind"],
            "pass": False,
        }

        try:
            if spec["kind"] == "defect":
                case = corpus_by_id[spec["case_id"]]
                gold = find_gold(manifest, spec["case_id"])
                if gold["family"] != spec["expected_family"]:
                    raise RuntimeError(
                        f"fixture_family_mismatch:{gold['family']}:{spec['expected_family']}"
                    )
                if case["gold"]["repair_scope"] != "LOCAL_REPAIR":
                    raise RuntimeError(
                        f"proof_requires_local_repair:{case['gold']['repair_scope']}"
                    )

                original_story = case["text"]
                detector_findings, detector_meta = call_detector(
                    api_key=api_key,
                    model=DETECTOR_MODEL,
                    story_id=proof_id,
                    story_family=case["family"],
                    story_text=original_story,
                    seed=2026130000 + index,
                    request_class="editorial_audit",
                )
                total_cost += meta_cost(detector_meta)
                matched = expected_match(detector_findings, gold)

                row.update({
                    "case_id": case["case_id"],
                    "source_id": case["source_id"],
                    "story_family": case["family"],
                    "gold": {
                        "family": gold["family"],
                        "severity": gold["severity"],
                        "span_ids": gold["span_ids"],
                        "validation_basis": gold["validation_basis"],
                    },
                    "detector": {
                        "model": DETECTOR_MODEL,
                        "findings": detector_findings,
                        "expected_defect_confirmed": matched is not None,
                        "meta": detector_meta,
                    },
                })

                if matched is None:
                    row["failure_stage"] = "DETECTION"
                    results.append(row)
                    continue

                target_block = case["mutation"]["injected_text"]
                family_rule = (
                    "Perception must remain intact. Busy/full hands or task load may not explain failure to hear, speak, turn the head, or look. If this call/hearing event has no downstream role, delete it. Otherwise the character must hear and may verbally acknowledge; only a genuinely hand-dependent physical action may be delayed."
                    if matched["family"] == "response_causality"
                    else "Use the smallest local correction for the confirmed family."
                )

                repair_attempts: list[dict[str, Any]] = []
                repaired_story = original_story
                verifier_findings: list[dict[str, Any]] = []
                verifier_meta: dict[str, Any] | None = None
                current_target_for_prompt = target_block
                verifier_feedback: list[dict[str, Any]] = []
                mechanical: dict[str, Any] = {}

                for attempt in range(1, 3):
                    repair_payload, repair_meta = structured_call(
                        api_key=api_key,
                        model=REPAIR_MODEL,
                        system=REPAIR_SYSTEM,
                        payload={
                            "story_id": proof_id,
                            "story_family": case["family"],
                            "attempt": attempt,
                            "full_story_read_only": repaired_story,
                            "confirmed_defect": matched,
                            "family_specific_repair_rule": family_rule,
                            "verifier_feedback_from_previous_attempt": verifier_feedback,
                            "target_block": current_target_for_prompt,
                        },
                        seed=2026135000 + index * 10 + attempt,
                        max_tokens=1400,
                        request_class="editorial_audit",
                    )
                    total_cost += meta_cost(repair_meta)
                    if "replacement_text" not in repair_payload:
                        raise RuntimeError("replacement_text_missing")
                    replacement = str(repair_payload.get("replacement_text") or "")
                    repair_note = str(repair_payload.get("repair_note") or "").strip()

                    repaired_story, mechanical = build_repaired_story(
                        original_story, target_block, replacement
                    )

                    verifier_findings, verifier_meta = call_detector(
                        api_key=api_key,
                        model=POST_VERIFY_MODEL,
                        story_id=f"{proof_id}_repaired_attempt_{attempt}",
                        story_family=case["family"],
                        story_text=repaired_story,
                        seed=2026140000 + index * 10 + attempt,
                        request_class="judge",
                    )
                    total_cost += meta_cost(verifier_meta)

                    repair_attempts.append({
                        "attempt": attempt,
                        "input_target_block": current_target_for_prompt,
                        "replacement_text": replacement,
                        "repair_note": repair_note,
                        "mechanical_invariants": mechanical,
                        "repair_meta": repair_meta,
                        "post_verify_findings": verifier_findings,
                        "post_verify_meta": verifier_meta,
                    })

                    if not verifier_findings:
                        break
                    if replacement == "":
                        break

                    current_target_for_prompt = replacement
                    verifier_feedback = verifier_findings

                adjudicator_findings: list[dict[str, Any]] = []
                adjudicator_meta: dict[str, Any] | None = None
                clean_source_story = source_by_id[case["source_id"]]["story"]
                restores_admitted_clean_source = (
                    case["source_id"] in admitted_clean
                    and repaired_story.strip() == clean_source_story.strip()
                )

                if verifier_findings:
                    adjudicator_findings, adjudicator_meta = call_detector(
                        api_key=api_key,
                        model=POST_ADJUDICATOR_MODEL,
                        story_id=f"{proof_id}_post_verify_adjudication",
                        story_family=case["family"],
                        story_text=repaired_story,
                        seed=2026145000 + index,
                        request_class="defect_locator",
                    )
                    total_cost += meta_cost(adjudicator_meta)

                consensus_findings = [
                    finding
                    for finding in verifier_findings
                    if any(
                        findings_overlap(finding, adjudicated)
                        for adjudicated in adjudicator_findings
                    )
                ]

                post_verify_clear = len(verifier_findings) == 0
                post_verify_disagreement_resolved = (
                    bool(verifier_findings)
                    and not adjudicator_findings
                    and restores_admitted_clean_source
                )

                row["repair"] = {
                    "model": REPAIR_MODEL,
                    "max_attempts": 2,
                    "attempts": repair_attempts,
                    "final_replacement_text": repair_attempts[-1]["replacement_text"],
                    "mechanical_invariants": mechanical,
                    "restores_admitted_clean_source": restores_admitted_clean_source,
                }
                row["post_verify"] = {
                    "model": POST_VERIFY_MODEL,
                    "findings": verifier_findings,
                    "meta": verifier_meta,
                    "attempts_used": len(repair_attempts),
                    "adjudication": None if not verifier_findings else {
                        "model": POST_ADJUDICATOR_MODEL,
                        "findings": adjudicator_findings,
                        "meta": adjudicator_meta,
                        "consensus_findings": consensus_findings,
                        "resolved_as_single_verifier_false_positive": (
                            post_verify_disagreement_resolved
                        ),
                    },
                }
                row["repaired_story"] = repaired_story
                row["pass"] = (
                    mechanical["outside_target_byte_for_byte_unchanged"]
                    and mechanical["target_block_removed"]
                    and (
                        post_verify_clear
                        or post_verify_disagreement_resolved
                    )
                )
                if not row["pass"]:
                    row["failure_stage"] = "POST_REPAIR_VERIFY"

            else:
                source_id = spec["source_id"]
                if source_id not in admitted_clean:
                    raise RuntimeError(f"clean_source_not_admitted:{source_id}")
                source = source_by_id[source_id]
                story = source["story"]

                detector_findings, detector_meta = call_detector(
                    api_key=api_key,
                    model=DETECTOR_MODEL,
                    story_id=proof_id,
                    story_family=source["family"],
                    story_text=story,
                    seed=2026130000 + index,
                    request_class="editorial_audit",
                )
                total_cost += meta_cost(detector_meta)

                verifier_findings, verifier_meta = call_detector(
                    api_key=api_key,
                    model=POST_VERIFY_MODEL,
                    story_id=f"{proof_id}_independent",
                    story_family=source["family"],
                    story_text=story,
                    seed=2026140000 + index,
                    request_class="judge",
                )
                total_cost += meta_cost(verifier_meta)

                row.update({
                    "source_id": source_id,
                    "story_family": source["family"],
                    "detector": {
                        "model": DETECTOR_MODEL,
                        "findings": detector_findings,
                        "meta": detector_meta,
                    },
                    "repair": {"skipped": True},
                    "post_verify": {
                        "model": POST_VERIFY_MODEL,
                        "findings": verifier_findings,
                        "meta": verifier_meta,
                    },
                    "pass": len(detector_findings) == 0 and len(verifier_findings) == 0,
                })
                if not row["pass"]:
                    row["failure_stage"] = "CLEAN_FALSE_POSITIVE"

        except Exception as exc:
            row["failure_stage"] = "RUNTIME"
            row["error"] = f"{type(exc).__name__}: {exc}"

        results.append(row)

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(
            json.dumps({
                "schema_version": "story-defect-e2e-repair-proof-result.v1",
                "status": "IN_PROGRESS",
                "completed": len(results),
                "results": results,
                "total_cost_usd": round(total_cost, 6),
            }, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    passes = sum(bool(row.get("pass")) for row in results)
    output = {
        "schema_version": "story-defect-e2e-repair-proof-result.v1",
        "status": "PASS" if passes == len(results) == 5 else "FAIL",
        "models": {
            "detector": DETECTOR_MODEL,
            "repair": REPAIR_MODEL,
            "post_repair_verifier": POST_VERIFY_MODEL,
            "post_repair_adjudicator": POST_ADJUDICATOR_MODEL,
        },
        "summary": {
            "cases": len(results),
            "passes": passes,
            "failures": len(results) - passes,
            "all_five_pass": passes == 5,
        },
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    OUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": output["status"],
        "summary": output["summary"],
        "total_cost_usd": output["total_cost_usd"],
        "elapsed_seconds": output["elapsed_seconds"],
        "case_results": [
            {
                "proof_id": row["proof_id"],
                "pass": row.get("pass"),
                "failure_stage": row.get("failure_stage"),
            }
            for row in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
