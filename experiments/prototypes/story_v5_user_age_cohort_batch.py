from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

CASES = (
    ("age-04-nature", 4, "experiments/specs/story-v5-user-cohort-20260925/age-04-nature.yaml"),
    ("age-10-mystery", 10, "experiments/specs/story-v5-user-cohort-20260925/age-10-mystery.yaml"),
    ("age-25-science", 25, "experiments/specs/story-v5-user-cohort-20260925/age-25-science.yaml"),
    ("age-40-world-lore", 40, "experiments/specs/story-v5-user-cohort-20260925/age-40-world-lore.yaml"),
    ("age-40-emotional", 40, "experiments/specs/story-v5-user-cohort-20260925/age-40-emotional.yaml"),
)

CONTEXT_ROOT = Path("experiments/context_packs/v5-user-cohort-20260925")
AUTHORITY_ROOT = Path("experiments/state_authority/v5-user-cohort-20260925")


def run_cmd(args: list[str]) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    completed = subprocess.run(args, env=env, check=False)
    return completed.returncode


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def case_prod_ready(result: dict[str, Any] | None, translation: dict[str, Any] | None) -> bool:
    if not result or not translation:
        return False
    judge = result.get("final_judge") or {}
    outcome_meta = result.get("story_outcome_meta") or {}
    jev_below = (result.get("whole_story_jev") or {}).get("below_threshold")
    return bool(
        result.get("accepted")
        and outcome_meta.get("commit_ready")
        and float(judge.get("average") or 0) >= 4.0
        and int(judge.get("minimum") or 0) >= 3
        and not jev_below
        and translation.get("accepted")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()

    marker_path = Path("experiments/triggers/story-v5-user-age-cohort-20260925.json")
    selected_cases = CASES
    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        only_cases = marker.get("only_cases")
        if isinstance(only_cases, list) and only_cases:
            wanted = {str(item) for item in only_cases}
            selected_cases = tuple(row for row in CASES if row[0] in wanted)
            if len(selected_cases) != len(wanted):
                raise RuntimeError("UNKNOWN_SELECTED_CASE")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cases_root = output.parent / "cases"
    cases_root.mkdir(parents=True, exist_ok=True)

    combined_cases: list[dict[str, Any]] = []
    tr_sections: list[str] = []
    outcome_rows: list[dict[str, Any]] = []

    for name, age, spec in selected_cases:
        print(f"===== V5 USER COHORT: {name} / exact age {age} =====", flush=True)
        case_dir = cases_root / name
        case_dir.mkdir(parents=True, exist_ok=True)
        case_result_path = case_dir / "result.json"

        story_rc = run_cmd(
            [
                sys.executable,
                "experiments/prototypes/story_v5_whole_draft_prototype.py",
                "--spec",
                spec,
                "--context-pack",
                str(CONTEXT_ROOT / f"{name}.json"),
                "--state-authority",
                str(AUTHORITY_ROOT / f"{name}.json"),
                "--output",
                str(case_result_path),
            ]
        )

        result = read_json(case_result_path)
        source_story_path = case_result_path.with_suffix(".story.txt")
        tr_path = case_dir / "result.story.tr.txt"
        tr_meta_path = case_dir / "result.translation.json"

        translation_rc = 99
        if story_rc == 0 and source_story_path.exists():
            translation_rc = run_cmd(
                [
                    sys.executable,
                    "experiments/prototypes/translate_story_to_tr.py",
                    "--source",
                    str(source_story_path),
                    "--age",
                    str(age),
                    "--output",
                    str(tr_path),
                    "--meta",
                    str(tr_meta_path),
                ]
            )

        translation = read_json(tr_meta_path)
        turkish_story = tr_path.read_text(encoding="utf-8").strip() if tr_path.exists() else ""
        prod_ready = case_prod_ready(result, translation)

        row: dict[str, Any] = {
            "case": name,
            "exact_age": age,
            "spec": spec,
            "story_process_exit_code": story_rc,
            "translation_process_exit_code": translation_rc,
            "prod_ready": prod_ready,
            "result": result,
            "translation": translation,
            "turkish_story": turkish_story,
        }
        combined_cases.append(row)

        if turkish_story:
            tr_sections.append(
                f"===== {name} | AGE {age} =====\n\n{turkish_story}"
            )

        outcome_rows.append(
            {
                "case": name,
                "exact_age": age,
                "prod_ready": prod_ready,
                "story_outcome": (result or {}).get("story_outcome"),
                "story_outcome_meta": (result or {}).get("story_outcome_meta"),
            }
        )

    all_prod_ready = len(combined_cases) == len(selected_cases) and all(row["prod_ready"] for row in combined_cases)
    combined = {
        "protocol": "english-story-production.v5-whole-draft-prototype.user-age-cohort.v1",
        "finalization": "story-v5-final-tr-translation.v1",
        "requested_ages": [row[1] for row in selected_cases],
        "case_count": len(combined_cases),
        "all_prod_ready": all_prod_ready,
        "cases": combined_cases,
    }

    output.write_text(
        json.dumps(combined, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output.with_suffix(".story.txt").write_text(
        "\n\n\n".join(tr_sections) + ("\n" if tr_sections else ""),
        encoding="utf-8",
    )
    output.with_suffix(".outcome.json").write_text(
        json.dumps(
            {
                "protocol": combined["protocol"],
                "all_prod_ready": all_prod_ready,
                "cases": outcome_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = []
    for row in combined_cases:
        result = row.get("result") or {}
        translation = row.get("translation") or {}
        judge = result.get("final_judge") or {}
        metrics = result.get("metrics") or {}
        summary.append(
            {
                "case": row["case"],
                "exact_age": row["exact_age"],
                "prod_ready": row["prod_ready"],
                "accepted": bool(result.get("accepted")),
                "word_count": metrics.get("word_count"),
                "target_words": metrics.get("target_words"),
                "scene_count": metrics.get("scene_count"),
                "judge_average": judge.get("average"),
                "judge_minimum": judge.get("minimum"),
                "jev_below_threshold": (result.get("whole_story_jev") or {}).get("below_threshold"),
                "commit_ready": bool((result.get("story_outcome_meta") or {}).get("commit_ready")),
                "translation_accepted": bool(translation.get("accepted")),
                "translation_average": (translation.get("final_verification") or {}).get("average"),
                "translation_minimum": (translation.get("final_verification") or {}).get("minimum"),
            }
        )

    print(
        json.dumps(
            {
                "all_prod_ready": all_prod_ready,
                "cases": summary,
                "result_path": str(output),
                "story_path": str(output.with_suffix(".story.txt")),
                "outcome_path": str(output.with_suffix(".outcome.json")),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )

    if not all_prod_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
