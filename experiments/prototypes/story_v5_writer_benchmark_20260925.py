from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SPEC = "experiments/specs/story-v5-user-cohort-20260925/age-04-nature.yaml"
CONTEXT = "experiments/context_packs/v5-user-cohort-20260925/age-04-nature.json"
AUTHORITY = "experiments/state_authority/v5-user-cohort-20260925/age-04-nature.json"
TRANSLATOR = "experiments/prototypes/translate_story_to_tr.py"

CANDIDATES = (
    ("aion-3.5", "aion-labs/aion-3.5"),
    ("gpt-5.6-sol", "openai/gpt-5.6-sol"),
    ("aion-3.5-mini", "aion-labs/aion-3.5-mini"),
    ("skyfall-36b-v2", "thedrummer/skyfall-36b-v2"),
)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_process(args: list[str]) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    return subprocess.run(args, env=env, check=False).returncode


def translation_cost_usd(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    total = 0.0
    for attempt in meta.get("attempts") or []:
        total += float(((attempt.get("translation_cost") or {}).get("usd")) or 0.0)
        total += float((((attempt.get("verification") or {}).get("cost") or {}).get("usd")) or 0.0)
    return total


def story_cost_usd(result: dict[str, Any] | None) -> float:
    if not result:
        return 0.0
    costs = result.get("costs") or {}
    total = float(costs.get("known_usd_total_excluding_jev_if_unreported") or 0.0)
    total += float((((result.get("whole_story_jev") or {}).get("usage") or {}).get("cost")) or 0.0)
    return total


def run_candidate(root: Path, slug: str, writer: str) -> dict[str, Any]:
    case_dir = root / slug
    case_dir.mkdir(parents=True, exist_ok=True)
    result_path = case_dir / "result.json"

    story_rc = run_process([
        sys.executable,
        "experiments/prototypes/story_v5_whole_draft_prototype.py",
        "--spec", SPEC,
        "--context-pack", CONTEXT,
        "--state-authority", AUTHORITY,
        "--writer", writer,
        "--output", str(result_path),
    ])

    result = read_json(result_path)
    story_path = result_path.with_suffix(".story.txt")
    tr_path = case_dir / "result.story.tr.txt"
    tr_meta_path = case_dir / "result.translation.json"
    tr_rc = 99

    if story_rc == 0 and result and result.get("accepted") and story_path.exists():
        tr_rc = run_process([
            sys.executable,
            TRANSLATOR,
            "--source", str(story_path),
            "--age", "4",
            "--output", str(tr_path),
            "--meta", str(tr_meta_path),
        ])

    tr_meta = read_json(tr_meta_path)
    total_usd = story_cost_usd(result) + translation_cost_usd(tr_meta)

    return {
        "slug": slug,
        "writer_model": writer,
        "story_exit_code": story_rc,
        "translation_exit_code": tr_rc,
        "accepted": bool((result or {}).get("accepted")),
        "commit_ready": bool(((result or {}).get("story_outcome_meta") or {}).get("commit_ready")),
        "jev_below_threshold": ((result or {}).get("whole_story_jev") or {}).get("below_threshold"),
        "judge_average": ((result or {}).get("final_judge") or {}).get("average"),
        "judge_minimum": ((result or {}).get("final_judge") or {}).get("minimum"),
        "word_count": ((result or {}).get("metrics") or {}).get("word_count"),
        "target_words": ((result or {}).get("metrics") or {}).get("target_words"),
        "translation_accepted": bool((tr_meta or {}).get("accepted")),
        "translation_average": ((tr_meta or {}).get("final_verification") or {}).get("average"),
        "translation_minimum": ((tr_meta or {}).get("final_verification") or {}).get("minimum"),
        "story_cost_usd": round(story_cost_usd(result), 9),
        "translation_cost_usd": round(translation_cost_usd(tr_meta), 9),
        "total_cost_usd": round(total_usd, 9),
        "elapsed_seconds": (result or {}).get("elapsed_seconds"),
        "english_story": (result or {}).get("story"),
        "turkish_story": tr_path.read_text(encoding="utf-8").strip() if tr_path.exists() else None,
        "result": result,
        "translation": tr_meta,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    root = output.parent / "writer-benchmark"
    root.mkdir(parents=True, exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(CANDIDATES)) as pool:
        futures = [
            pool.submit(run_candidate, root, slug, writer)
            for slug, writer in CANDIDATES
        ]
        rows = [future.result() for future in futures]

    rows.sort(key=lambda row: [x[0] for x in CANDIDATES].index(row["slug"]))

    payload = {
        "protocol": "story-v5-writer-benchmark.v1",
        "exact_age": 4,
        "target_words": 500,
        "controlled_variables": {
            "architect": "openai/gpt-5.6-luna",
            "judge": "anthropic/claude-haiku-4.5",
            "jev": "typesafe/jev-1.13",
            "outcome_extractor": "openai/gpt-5.6-luna",
            "translator": "openai/gpt-5.6-luna",
            "translation_verifier": "anthropic/claude-haiku-4.5",
            "spec": SPEC,
            "context_pack": CONTEXT,
            "state_authority": AUTHORITY,
        },
        "candidates": rows,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    story_sections = []
    for row in rows:
        story_sections.append(
            f"===== {row['slug']} | {row['writer_model']} | USD {row['total_cost_usd']:.6f} =====\n\n"
            + (row.get("turkish_story") or "[NO TURKISH OUTPUT]")
        )
    output.with_suffix(".story.txt").write_text(
        "\n\n\n".join(story_sections) + "\n",
        encoding="utf-8",
    )
    output.with_suffix(".outcome.json").write_text(
        json.dumps(
            {
                "protocol": payload["protocol"],
                "candidates": [
                    {
                        k: row[k]
                        for k in (
                            "slug", "writer_model", "accepted", "commit_ready",
                            "jev_below_threshold", "judge_average", "judge_minimum",
                            "word_count", "translation_accepted",
                            "story_cost_usd", "translation_cost_usd", "total_cost_usd",
                            "elapsed_seconds",
                        )
                    }
                    for row in rows
                ],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps([
        {
            "slug": row["slug"],
            "writer": row["writer_model"],
            "accepted": row["accepted"],
            "commit_ready": row["commit_ready"],
            "jev_below": row["jev_below_threshold"],
            "judge_average": row["judge_average"],
            "translation_accepted": row["translation_accepted"],
            "word_count": row["word_count"],
            "story_cost_usd": row["story_cost_usd"],
            "translation_cost_usd": row["translation_cost_usd"],
            "total_cost_usd": row["total_cost_usd"],
            "elapsed_seconds": row["elapsed_seconds"],
        }
        for row in rows
    ], ensure_ascii=False, indent=2), flush=True)

    # Benchmark itself succeeds even when an individual candidate is rejected;
    # rejection is evidence, not infrastructure failure.


if __name__ == "__main__":
    main()
