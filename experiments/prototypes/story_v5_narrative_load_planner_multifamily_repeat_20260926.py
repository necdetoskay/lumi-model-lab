from __future__ import annotations

import json
from pathlib import Path

from experiments.prototypes import story_v5_narrative_load_planner_multifamily_20260926 as probe

REPEAT_SEED_BASE = 2026092760


def main() -> None:
    probe.SEED_BASE = REPEAT_SEED_BASE
    probe.main()

    result_path = Path("runs/story-v5-narrative-load-planner-multifamily/result.json")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["experiment"] = "story-v5-narrative-load-planner-multifamily-repeat-v1"
    result["repeat_seed_base"] = REPEAT_SEED_BASE
    result["protocol_frozen_against_run"] = 36225932402
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "repeat_seed_base": REPEAT_SEED_BASE,
        "summary": result["summary"],
        "consensus_wins": result["consensus_wins"],
        "mean_word_delta": result["mean_word_delta"],
        "total_cost_usd": result["total_cost_usd"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
