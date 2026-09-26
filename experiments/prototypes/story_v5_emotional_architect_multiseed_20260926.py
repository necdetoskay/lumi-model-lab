from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes import story_v5_existing_architect_narrative_load_targeted_v2_20260926 as targeted

FAMILY = "emotional_development"
SEEDS = [2026093810, 2026094810]
PRIOR_TARGETED_RUN = 36228645350
PRIOR_RESULT = "INCONCLUSIVE"


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    frozen = targeted.frozen_cases()[FAMILY]
    fixture = targeted.fixture_by_family(FAMILY)
    spec = targeted.integ.make_spec(fixture)
    started = time.perf_counter()

    cases = []
    total_cost = 0.0

    for seed in SEEDS:
        plan_obj, plan_meta = targeted.plan_targeted(key, spec, seed)
        candidate, writer_meta = targeted.write_targeted(key, spec, plan_obj, seed + 1)

        forward, c1 = targeted.compare(
            key,
            fixture,
            frozen["baseline_story"],
            candidate["story"],
            seed + 2,
        )
        reverse, rmeta = targeted.structured_call(
            api_key=key,
            model=targeted.integ.JUDGE_MODEL,
            system=targeted.integ.PAIRWISE_SYSTEM,
            payload={
                "exact_age": 4,
                "story_family": FAMILY,
                "premise": fixture["premise"],
                "story_A": candidate["story"],
                "story_B": frozen["baseline_story"],
            },
            seed=seed + 3,
            max_tokens=targeted.JUDGE_MAX_TOKENS,
            request_class="editorial_audit",
        )
        c2 = float(((rmeta.get("cost") or {}).get("usd")) or 0.0)

        fw = targeted.normalize(
            forward.get("winner"),
            "frozen_baseline",
            "narrative_load_architect_v2",
        )
        rv = targeted.normalize(
            reverse.get("winner"),
            "narrative_load_architect_v2",
            "frozen_baseline",
        )
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        case_cost = targeted.usd(plan_meta) + targeted.usd(writer_meta) + c1 + c2
        total_cost += case_cost
        cases.append({
            "seed": seed,
            "semantic_retries": plan_meta.get("semantic_retries"),
            "baseline_words": frozen["baseline_words"],
            "candidate_words": candidate["word_count"],
            "word_delta": candidate["word_count"] - int(frozen["baseline_words"]),
            "candidate_plan": plan_obj,
            "candidate_story": candidate,
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "normalized_winners": {
                "forward": fw,
                "reverse": rv,
                "consensus": consensus,
            },
            "cost_usd": case_cost,
        })

    wins = {
        "frozen_baseline": 0,
        "narrative_load_architect_v2": 0,
        "TIE": 0,
        "INCONCLUSIVE": 0,
    }
    for case in cases:
        wins[case["normalized_winners"]["consensus"]] += 1

    strict_resolution_pass = (
        wins["narrative_load_architect_v2"] == len(SEEDS)
        and wins["frozen_baseline"] == 0
        and wins["INCONCLUSIVE"] == 0
        and wins["TIE"] == 0
    )

    result = {
        "experiment": "story-v5-emotional-architect-multiseed-v1",
        "family": FAMILY,
        "prior_targeted_run": PRIOR_TARGETED_RUN,
        "prior_result": PRIOR_RESULT,
        "frozen_baseline_source_run": frozen.get("source_run", 36227676063),
        "new_seeds": SEEDS,
        "strict_resolution_rule": (
            "both new seeds must be narrative_load_architect_v2 consensus wins; "
            "zero frozen-baseline wins; zero inconclusive/tie"
        ),
        "strict_resolution_pass": strict_resolution_pass,
        "proposed_family_resolution": (
            "narrative_load_architect_win_from_multi_seed"
            if strict_resolution_pass
            else "remain_inconclusive"
        ),
        "provider_reservation_caps": {
            "architect": targeted.ARCHITECT_MAX_TOKENS,
            "writer": targeted.WRITER_MAX_TOKENS,
            "judge": targeted.JUDGE_MAX_TOKENS,
            "note": "provider/output reservation caps, not story-length targets",
        },
        "summary": [
            {
                "seed": case["seed"],
                "semantic_retries": case["semantic_retries"],
                "baseline_words": case["baseline_words"],
                "candidate_words": case["candidate_words"],
                "word_delta": case["word_delta"],
                **case["normalized_winners"],
            }
            for case in cases
        ],
        "consensus_wins": wins,
        "cases": cases,
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-emotional-architect-multiseed")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in cases:
        (out / f"seed-{case['seed']}-candidate.txt").write_text(
            case["candidate_story"]["story"] + "\n",
            encoding="utf-8",
        )

    print(json.dumps({
        "summary": result["summary"],
        "consensus_wins": wins,
        "strict_resolution_pass": strict_resolution_pass,
        "proposed_family_resolution": result["proposed_family_resolution"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
