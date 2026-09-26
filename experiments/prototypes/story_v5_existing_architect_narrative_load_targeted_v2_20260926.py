from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.english_scene_plan_smoke import build_labeled_brief
from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import count_words, parse_cost, parse_usage
from experiments.prototypes import story_v5_whole_draft_prototype as whole
from experiments.prototypes import story_v5_existing_architect_narrative_load_integration_20260926 as integ
from experiments.prototypes import story_v5_narrative_load_planner_cohort_b_20260926 as cohort
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FROZEN_PATH = Path("experiments/fixtures/story_v5_existing_architect_baseline_cohort_b_v1.json")
TARGET_FAMILIES = ["emotional_development", "everyday_fantastical_discovery"]
ARCHITECT_MAX_TOKENS = 8192
WRITER_MAX_TOKENS = 16384
JUDGE_MAX_TOKENS = 8192


def frozen_cases() -> dict[str, dict]:
    payload = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    return {x["family"]: x for x in payload["cases"]}


def fixture_by_family(family: str) -> dict:
    return next(x for x in cohort.FIXTURES if x["family"] == family)


def usd(meta: dict) -> float:
    return float(((meta.get("cost") or {}).get("usd")) or 0.0)


def plan_targeted(key: str, spec, seed: int) -> tuple[dict, dict]:
    brief = build_labeled_brief(spec)
    total_cost = 0.0
    parse_failures_total: list[str] = []
    last_errors: list[str] = []

    for semantic_attempt in range(2):
        correction = ""
        if semantic_attempt:
            correction = (
                "\n\nBOUNDED REPLAN: Previous architecture failed deterministic validation: "
                + ", ".join(last_errors)
                + ". Correct structural errors only; preserve premise, causal rules, epistemic order, and terminal closure."
            )

        parsed, body, _, failures = call_structured_json_with_retry(
            api_key=key,
            model=integ.ARCHITECT_MODEL,
            system_prompt=integ.ARCHITECT_WITH_NARRATIVE_LOAD,
            user_prompt="Create the story architecture.\n\nSTORY BRIEF\n" + brief + correction,
            temperature=0.2,
            max_tokens=ARCHITECT_MAX_TOKENS,
            seed=seed + semantic_attempt * 1009,
            request_class="story_plan",
        )
        parse_failures_total.extend(failures)
        total_cost += float(parse_cost(body).usd or 0.0)
        errors = whole.validate_plan(parsed, spec)
        if not errors:
            return parsed, {
                "parse_failures": parse_failures_total,
                "semantic_retries": semantic_attempt,
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": {"usd": total_cost},
            }
        last_errors = errors

    raise RuntimeError("PLAN_INVALID_AFTER_BOUNDED_REPLAN:" + ",".join(last_errors))


def write_targeted(key: str, spec, plan_obj: dict, seed: int) -> tuple[dict, dict]:
    brief = build_labeled_brief(spec)
    meta = plan_obj.get("narrative_load") or {}
    user = (
        "STORY BRIEF\n"
        + brief
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan_obj["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nDYNAMIC SCENE GRAPH\n"
        + json.dumps(plan_obj["scenes"], ensure_ascii=False, indent=2)
        + "\n\nNARRATIVE LOAD METADATA\n"
        + json.dumps(meta, ensure_ascii=False, indent=2)
        + "\n\nTARGET TOTAL WORDS: 500 (SOFT)."
        + "\nQuality, causality, age fit and natural completion are more important than hitting the number."
        + "\nDo not invent new events merely to reach length."
        + "\nTreat NARRATIVE LOAD METADATA as immutable execution constraints."
        + "\nDo not delay an established causal effect once its stated conditions are satisfied."
        + "\nDo not undo a committed item/action state."
        + "\nKeep epistemic order: do not reveal decisive evidence early and do not repeat a resolved misunderstanding."
        + "\nDistinguish perceiving from responding: busy hands do not by themselves prevent hearing or seeing."
        + "\nDo not invent an unstated physical inability such as being too short, too weak, or unable to reach."
        + "\nOnce the final closure action is realized, STOP. Do not append a second payoff, prop convergence, joke, or symbolic action."
        + "\nAfter resolution, move to concrete payoff instead of re-explaining the same fact."
    )

    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=key,
        model=integ.WRITER_MODEL,
        system_prompt=whole.WHOLE_DRAFT_PROMPT,
        user_prompt=user,
        temperature=0.6,
        max_tokens=WRITER_MAX_TOKENS,
        seed=seed,
        request_class="scene_story",
    )
    errors = whole.validate_draft(parsed, plan_obj)
    if errors:
        raise RuntimeError("DRAFT_INVALID:" + ",".join(errors))
    story = whole.assemble_story(parsed)
    return {
        "draft": parsed,
        "story": story,
        "word_count": count_words(story),
    }, {
        "parse_failures": failures,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
    }


def compare(key: str, fixture: dict, baseline: str, candidate: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=key,
        model=integ.JUDGE_MODEL,
        system=integ.PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": fixture["family"],
            "premise": fixture["premise"],
            "story_A": baseline,
            "story_B": candidate,
        },
        seed=seed,
        max_tokens=JUDGE_MAX_TOKENS,
        request_class="editorial_audit",
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    frozen = frozen_cases()
    started = time.perf_counter()
    cases = []
    total_cost = 0.0

    for family in TARGET_FAMILIES:
        fixture = fixture_by_family(family)
        base = frozen[family]
        seed = int(base["seed"])

        spec = integ.make_spec(fixture)
        plan_obj, plan_meta = plan_targeted(key, spec, seed)
        candidate, writer_meta = write_targeted(key, spec, plan_obj, seed + 1)

        forward, c1 = compare(key, fixture, base["baseline_story"], candidate["story"], seed + 2)
        reverse, c2 = structured_call(
            api_key=key,
            model=integ.JUDGE_MODEL,
            system=integ.PAIRWISE_SYSTEM,
            payload={
                "exact_age": 4,
                "story_family": fixture["family"],
                "premise": fixture["premise"],
                "story_A": candidate["story"],
                "story_B": base["baseline_story"],
            },
            seed=seed + 3,
            max_tokens=JUDGE_MAX_TOKENS,
            request_class="editorial_audit",
        )
        c2_cost = float(((c2.get("cost") or {}).get("usd")) or 0.0)

        fw = normalize(forward.get("winner"), "frozen_baseline", "narrative_load_architect_v2")
        rv = normalize(reverse.get("winner"), "narrative_load_architect_v2", "frozen_baseline")
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        case_cost = usd(plan_meta) + usd(writer_meta) + c1 + c2_cost
        total_cost += case_cost
        cases.append({
            "family": family,
            "premise": fixture["premise"],
            "frozen_baseline": {
                "source_run": base["source_run"] if "source_run" in base else 36227676063,
                "word_count": base["baseline_words"],
                "story": base["baseline_story"],
            },
            "candidate": {
                "plan": plan_obj,
                "plan_meta": plan_meta,
                "story": candidate,
                "writer_meta": writer_meta,
            },
            "word_delta": candidate["word_count"] - int(base["baseline_words"]),
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "normalized_winners": {
                "forward": fw,
                "reverse": rv,
                "consensus": consensus,
            },
            "cost_usd": case_cost,
        })

    wins = {"frozen_baseline": 0, "narrative_load_architect_v2": 0, "TIE": 0, "INCONCLUSIVE": 0}
    summary = []
    for case in cases:
        consensus = case["normalized_winners"]["consensus"]
        wins[consensus] = wins.get(consensus, 0) + 1
        plan_meta = case["candidate"]["plan_meta"]
        summary.append({
            "family": case["family"],
            "semantic_retries": plan_meta.get("semantic_retries"),
            "baseline_words": case["frozen_baseline"]["word_count"],
            "candidate_words": case["candidate"]["story"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": consensus,
        })

    result = {
        "experiment": "story-v5-existing-architect-narrative-load-targeted-v2",
        "baseline_source_run": 36227676063,
        "target_families": TARGET_FAMILIES,
        "extra_planner_model_hop": False,
        "provider_reservation_caps": {
            "architect": ARCHITECT_MAX_TOKENS,
            "writer": WRITER_MAX_TOKENS,
            "judge": JUDGE_MAX_TOKENS,
        },
        "summary": summary,
        "consensus_wins": wins,
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-existing-architect-narrative-load-targeted")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for case in cases:
        family = case["family"]
        (out / f"{family}-candidate.txt").write_text(case["candidate"]["story"]["story"] + "\n", encoding="utf-8")

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
