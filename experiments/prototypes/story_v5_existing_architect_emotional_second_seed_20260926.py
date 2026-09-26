from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from experiments.prototypes import story_v5_existing_architect_narrative_load_targeted_v2_20260926 as base
from experiments.prototypes import story_v5_existing_architect_narrative_load_integration_20260926 as integ
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FAMILY = "emotional_development"
SEED_OFFSET = 17011


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
    started = time.perf_counter()

    frozen = base.frozen_cases()[FAMILY]
    fixture = base.fixture_by_family(FAMILY)
    spec = integ.make_spec(fixture)
    seed = int(frozen["seed"]) + SEED_OFFSET

    plan_obj, plan_meta = base.plan_targeted(key, spec, seed)
    candidate, writer_meta = base.write_targeted(key, spec, plan_obj, seed + 1)

    forward, c1 = base.compare(
        key,
        fixture,
        frozen["baseline_story"],
        candidate["story"],
        seed + 2,
    )
    reverse, reverse_meta = structured_call(
        api_key=key,
        model=integ.JUDGE_MODEL,
        system=integ.PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": FAMILY,
            "premise": fixture["premise"],
            "story_A": candidate["story"],
            "story_B": frozen["baseline_story"],
        },
        seed=seed + 3,
        max_tokens=base.JUDGE_MAX_TOKENS,
        request_class="editorial_audit",
    )
    c2 = float(((reverse_meta.get("cost") or {}).get("usd")) or 0.0)

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

    def candidate_defects(payload: dict, candidate_label: str) -> list:
        defects = payload.get("serious_defects") or {}
        return list(defects.get(candidate_label) or [])

    forward_candidate_defects = candidate_defects(forward, "B")
    reverse_candidate_defects = candidate_defects(reverse, "A")
    serious_defects = forward_candidate_defects + reverse_candidate_defects

    total_cost = (
        base.usd(plan_meta)
        + base.usd(writer_meta)
        + c1
        + c2
    )

    result = {
        "experiment": "story-v5-existing-architect-emotional-second-seed-v1",
        "family": FAMILY,
        "baseline_source_run": 36227676063,
        "first_targeted_run": 36228645350,
        "seed_offset": SEED_OFFSET,
        "effective_seed": seed,
        "provider_reservation_caps": {
            "architect": base.ARCHITECT_MAX_TOKENS,
            "writer": base.WRITER_MAX_TOKENS,
            "judge": base.JUDGE_MAX_TOKENS,
        },
        "frozen_baseline": {
            "word_count": frozen["baseline_words"],
            "story": frozen["baseline_story"],
        },
        "candidate": {
            "plan": plan_obj,
            "plan_meta": plan_meta,
            "story": candidate,
            "writer_meta": writer_meta,
        },
        "word_delta": candidate["word_count"] - int(frozen["baseline_words"]),
        "pairwise_forward": forward,
        "pairwise_reverse": reverse,
        "normalized_winners": {
            "forward": fw,
            "reverse": rv,
            "consensus": consensus,
        },
        "candidate_serious_defects": serious_defects,
        "candidate_serious_defect_count": len(serious_defects),
        "total_cost_usd": round(total_cost, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-existing-architect-emotional-second-seed")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "candidate.txt").write_text(candidate["story"] + "\n", encoding="utf-8")

    print(json.dumps({
        "family": FAMILY,
        "baseline_words": frozen["baseline_words"],
        "candidate_words": candidate["word_count"],
        "word_delta": result["word_delta"],
        "forward": fw,
        "reverse": rv,
        "consensus": consensus,
        "candidate_serious_defect_count": len(serious_defects),
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
