from __future__ import annotations

import json
import os
import time
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE = Path("experiments/fixtures/story_v5_emotional_absolute_tiebreak_v1.json")
JUDGES = [
    {
        "id": "sol",
        "model": "openai/gpt-5.6-sol",
        "request_class": "editorial_audit",
        "max_tokens": 3000,
        "seed_base": 2026095100,
    },
    {
        "id": "haiku",
        "model": "anthropic/claude-haiku-4.5",
        "request_class": "judge",
        "max_tokens": 2500,
        "seed_base": 2026095200,
    },
]
CRITERIA = [
    "coherence",
    "age_fit",
    "read_aloud",
    "agency",
    "pacing",
    "naturalness",
    "closure",
    "economy",
]
BASELINE_ID = "frozen_baseline"
CANDIDATE_IDS = ["candidate_seed_1", "candidate_seed_2"]

ABSOLUTE_JUDGE_SYSTEM = r"""
You are an independent children's-book production quality judge.

Judge exactly ONE finished Turkish story in isolation. You are not comparing A vs B,
you do not know whether this story is a baseline or candidate, and you must not infer
or reward experiment identity.

Reader contract:
- exact age: 4
- adult read-aloud
- nominal target: about 500 words, but LENGTH IS SOFT
- quality, causality, age fit, natural Turkish, and satisfying completion are more
  important than approaching the nominal word count
- do NOT reward a story merely for being longer or shorter
- economy means every sentence earns its place; it does not mean "shorter is better"

Score each criterion with an INTEGER 1-10:
- coherence: causal and factual consistency; information appears before it is used
- age_fit: understandable and emotionally suitable for an exact-age-4 listener
- read_aloud: rhythm, sentence flow, dialogue, and oral clarity
- agency: the child protagonist meaningfully observes/decides/acts
- pacing: progression without dragging, rushing, or redundant beats
- naturalness: idiomatic, fluent Turkish without awkward generated phrasing
- closure: the main emotional/causal question closes concretely without a tacked-on epilogue
- economy: no filler, recap, repeated explanation, or forced prop convergence
- overall: holistic production quality; not a mechanical average

Calibration:
- 9-10 exceptional / publication-ready
- 8 strong production quality
- 7 acceptable, with only minor weaknesses
- 6 noticeable weakness
- 5 or below materially weak

A serious defect is a material flaw that should block this story from production,
such as broken causality, contradictory state, age-inappropriate reasoning, unresolved
main problem, major unnatural-language failure, or an invented physical/epistemic
condition that materially changes the story. Minor wording preferences are NOT serious defects.

Return JSON only:
{
  "scores": {
    "coherence": 1,
    "age_fit": 1,
    "read_aloud": 1,
    "agency": 1,
    "pacing": 1,
    "naturalness": 1,
    "closure": 1,
    "economy": 1,
    "overall": 1
  },
  "serious_defects": [],
  "forced_or_filler_risk": "low|medium|high",
  "strengths": ["short item"],
  "weaknesses": ["short item"],
  "summary": "maximum three short sentences"
}
""".strip()


def validate_judgment(payload: dict) -> None:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("scores_missing")
    for key in [*CRITERIA, "overall"]:
        value = scores.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
            raise RuntimeError(f"invalid_score:{key}:{value!r}")
    defects = payload.get("serious_defects")
    if not isinstance(defects, list):
        raise RuntimeError("serious_defects_invalid")
    if payload.get("forced_or_filler_risk") not in {"low", "medium", "high"}:
        raise RuntimeError("forced_or_filler_risk_invalid")


def average_story(judgments: list[dict]) -> dict:
    return {
        "criterion_averages": {
            criterion: round(mean(j["scores"][criterion] for j in judgments), 3)
            for criterion in CRITERIA
        },
        "overall_average": round(mean(j["scores"]["overall"] for j in judgments), 3),
        "serious_defect_count": sum(len(j["serious_defects"]) for j in judgments),
        "forced_or_filler_risk": [j["forced_or_filler_risk"] for j in judgments],
    }


def noninferiority(candidate: dict, baseline: dict) -> dict:
    criterion_floor = 7.0
    overall_margin = 0.5
    max_criterion_trail = 1.0

    criterion_floor_failures = [
        key
        for key, value in candidate["criterion_averages"].items()
        if value < criterion_floor
    ]
    baseline_trail_failures = [
        key
        for key in CRITERIA
        if baseline["criterion_averages"][key] - candidate["criterion_averages"][key]
        > max_criterion_trail
    ]
    overall_noninferior = (
        candidate["overall_average"] >= baseline["overall_average"] - overall_margin
    )
    no_serious_defects = candidate["serious_defect_count"] == 0

    passed = (
        no_serious_defects
        and overall_noninferior
        and not criterion_floor_failures
        and not baseline_trail_failures
    )
    return {
        "passed": passed,
        "no_serious_defects": no_serious_defects,
        "overall_noninferior": overall_noninferior,
        "overall_margin_allowed": overall_margin,
        "criterion_floor": criterion_floor,
        "criterion_floor_failures": criterion_floor_failures,
        "max_criterion_trail_allowed": max_criterion_trail,
        "baseline_trail_failures": baseline_trail_failures,
    }


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.perf_counter()
    raw: dict[str, dict[str, dict]] = {}
    total_cost = 0.0

    for story_index, row in enumerate(fixture["stories"]):
        story_id = row["id"]
        raw[story_id] = {}
        for judge_index, judge in enumerate(JUDGES):
            parsed, meta = structured_call(
                api_key=key,
                model=judge["model"],
                system=ABSOLUTE_JUDGE_SYSTEM,
                payload={
                    "exact_age": fixture["exact_age"],
                    "reading_mode": fixture["reading_mode"],
                    "narrative_family": fixture["family"],
                    "nominal_target_words_soft": fixture["nominal_target_words"],
                    "premise": fixture["premise"],
                    "story": row["story"],
                },
                seed=judge["seed_base"] + story_index * 10 + judge_index,
                max_tokens=judge["max_tokens"],
                request_class=judge["request_class"],
            )
            validate_judgment(parsed)
            cost = float(((meta.get("cost") or {}).get("usd")) or 0.0)
            total_cost += cost
            raw[story_id][judge["id"]] = {
                "model": judge["model"],
                "judgment": parsed,
                "meta": meta,
            }

    aggregate = {}
    for row in fixture["stories"]:
        story_id = row["id"]
        judgments = [raw[story_id][j["id"]]["judgment"] for j in JUDGES]
        aggregate[story_id] = {
            "word_count": row["word_count"],
            **average_story(judgments),
        }

    baseline = aggregate[BASELINE_ID]
    candidate_checks = {
        candidate_id: noninferiority(aggregate[candidate_id], baseline)
        for candidate_id in CANDIDATE_IDS
    }
    strict_resolution_pass = all(x["passed"] for x in candidate_checks.values())

    result = {
        "experiment": "story-v5-emotional-absolute-tiebreak-v1",
        "fixture": str(FIXTURE),
        "family": fixture["family"],
        "exact_age": fixture["exact_age"],
        "reading_mode": fixture["reading_mode"],
        "nominal_target_words_soft": fixture["nominal_target_words"],
        "judge_models": [j["model"] for j in JUDGES],
        "position_independent": True,
        "generation_calls": 0,
        "decision_rule_frozen_before_run": {
            "candidate_serious_defects_across_judges_must_equal": 0,
            "candidate_overall_average_must_be_at_least_baseline_minus": 0.5,
            "every_candidate_criterion_average_must_be_at_least": 7.0,
            "no_candidate_criterion_may_trail_baseline_by_more_than": 1.0,
            "both_candidate_seeds_must_pass": True,
            "economy_does_not_reward_shortness": True,
        },
        "aggregate": aggregate,
        "candidate_noninferiority": candidate_checks,
        "strict_resolution_pass": strict_resolution_pass,
        "proposed_family_resolution": (
            "noninferior_from_position_independent_absolute_judging"
            if strict_resolution_pass
            else "remain_inconclusive"
        ),
        "raw_judgments": raw,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-emotional-absolute-tiebreak")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "aggregate": aggregate,
        "candidate_noninferiority": candidate_checks,
        "strict_resolution_pass": strict_resolution_pass,
        "proposed_family_resolution": result["proposed_family_resolution"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
