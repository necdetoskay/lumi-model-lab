from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes import story_v5_narrative_load_planner_20260926 as p
from experiments.prototypes import story_v5_length_pressure_family_pairwise_20260926 as fam
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED_BASE = 2026092660


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def plan_for_fixture(key: str, fixture: dict, seed: int) -> tuple[dict, float]:
    plan, meta = structured_call(
        api_key=key,
        model=p.PLANNER_MODEL,
        system=p.PLANNER_SYSTEM,
        payload={
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "nominal_target_words": 500,
            "story_family": fixture["family"],
            "premise": fixture["premise"],
            "constraints": {
                "no_new_named_character": True,
                "no_new_relationship_canon": True,
                "supporting_thread_optional": True,
                "quality_over_word_count": True,
                "spine_must_be_self_sufficient_before_writing": True,
            },
        },
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
    )
    spine = plan.get("spine") or []
    if not (8 <= len(spine) <= 12):
        raise RuntimeError(f"{fixture['family']}:planner_spine_size_invalid:{len(spine)}")
    return plan, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()
    cases = []
    total_cost = 0.0

    for i, fixture in enumerate(fam.FIXTURES):
        seed = SEED_BASE + i * 100
        plan, planner_cost = plan_for_fixture(key, fixture, seed)
        planned_spine = plan["spine"]

        baseline = p.generate_story(key, fixture["spine"], seed + 1)

        # p.generate_story binds the original premise, so use a local equivalent
        # for non-exploration families.
        from src.generate import call_openrouter, count_words, parse_cost, parse_usage
        from experiments.prototypes import story_spine_refined_recipe_20260926 as base
        def generate_with_fixture(spine: list[dict]) -> dict:
            t0 = time.perf_counter()
            story, body, payload = call_openrouter(
                api_key=key,
                model=p.WRITER_MODEL,
                system_prompt=p.WRITER_SYSTEM,
                user_prompt=(
                    f"KONU:\n{fixture['premise']}\n\n"
                    f"HİKÂYE OMURGASI:\n{p.render_spine(spine)}\n\n"
                    "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
                ),
                temperature=0.72,
                max_tokens=None,
                seed=seed + 1,
                request_class="teacher_story_medium_reasoning",
                structured_output=False,
            )
            return {
                "story": story,
                "word_count": count_words(story),
                "scan": base.scan(story),
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost_usd": float(parse_cost(body).usd or 0.0),
                "elapsed_seconds": round(time.perf_counter() - t0, 3),
                "request_payload": payload,
            }

        baseline = generate_with_fixture(fixture["spine"])
        planned = generate_with_fixture(planned_spine)

        forward, c1 = structured_call(
            api_key=key,
            model=p.JUDGE_MODEL,
            system=p.PAIRWISE_SYSTEM,
            payload={
                "exact_age": 4,
                "story_family": fixture["family"],
                "premise": fixture["premise"],
                "story_A": baseline["story"],
                "story_B": planned["story"],
            },
            seed=seed + 2,
            max_tokens=None,
            request_class="editorial_audit",
        )
        reverse, c2 = structured_call(
            api_key=key,
            model=p.JUDGE_MODEL,
            system=p.PAIRWISE_SYSTEM,
            payload={
                "exact_age": 4,
                "story_family": fixture["family"],
                "premise": fixture["premise"],
                "story_A": planned["story"],
                "story_B": baseline["story"],
            },
            seed=seed + 3,
            max_tokens=None,
            request_class="editorial_audit",
        )
        judge_cost_1 = float(((c1.get("cost") or {}).get("usd")) or 0.0)
        judge_cost_2 = float(((c2.get("cost") or {}).get("usd")) or 0.0)

        fw = normalize(forward.get("winner"), "baseline", "planned")
        rv = normalize(reverse.get("winner"), "planned", "baseline")
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        case_cost = (
            planner_cost
            + baseline["cost_usd"]
            + planned["cost_usd"]
            + judge_cost_1
            + judge_cost_2
        )
        total_cost += case_cost

        cases.append({
            "family": fixture["family"],
            "premise": fixture["premise"],
            "planner_output": plan,
            "baseline": {"spine": fixture["spine"], **baseline},
            "planned": {"spine": planned_spine, **planned},
            "word_delta": planned["word_count"] - baseline["word_count"],
            "normalized_winners": {
                "forward": fw,
                "reverse": rv,
                "consensus": consensus,
            },
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "cost_usd": {
                "planner": planner_cost,
                "baseline_writer": baseline["cost_usd"],
                "planned_writer": planned["cost_usd"],
                "judges": judge_cost_1 + judge_cost_2,
                "total": case_cost,
            },
        })

    wins = {"baseline": 0, "planned": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        c = case["normalized_winners"]["consensus"]
        wins[c] = wins.get(c, 0) + 1
        support = case["planner_output"].get("supporting_thread") or {}
        summary.append({
            "family": case["family"],
            "planner_beats": len(case["planned"]["spine"]),
            "supporting_thread_used": bool(support.get("used")),
            "baseline_words": case["baseline"]["word_count"],
            "planned_words": case["planned"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": c,
            "forward_confidence": case["pairwise_forward"].get("confidence"),
            "reverse_confidence": case["pairwise_reverse"].get("confidence"),
        })

    deltas = [c["word_delta"] for c in cases]
    result = {
        "experiment": "story-v5-narrative-load-planner-multifamily-v1",
        "exact_age": 4,
        "nominal_target_words": 500,
        "families": len(cases),
        "planner_model": p.PLANNER_MODEL,
        "writer_model": p.WRITER_MODEL,
        "judge_model": p.JUDGE_MODEL,
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(deltas) / len(deltas), 2),
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-narrative-load-planner-multifamily")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in cases:
        family = case["family"]
        (out / f"{family}-baseline.txt").write_text(case["baseline"]["story"] + "\n", encoding="utf-8")
        (out / f"{family}-planned.txt").write_text(case["planned"]["story"] + "\n", encoding="utf-8")
        (out / f"{family}-spine.json").write_text(
            json.dumps(case["planner_output"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": result["mean_word_delta"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
