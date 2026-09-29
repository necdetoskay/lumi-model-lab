from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.generate import count_words

DEFAULT_SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_postprocess_source_36552606045.json"
)
DEFAULT_REPAIR = Path(
    "data/specifications/story_lab/sonnet55_final_repair_run_36564554796.json"
)
DEFAULT_OUT = Path("runs/sonnet55-final-repair-recover/result.json")
DEFAULT_STORY_OUT = Path("runs/sonnet55-final-repair-recover/repaired_story.txt")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_recovered_repairs(story: str, repairs: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in repairs:
        grouped[str(row["old"])].append(row)

    value = story
    applied: list[dict[str, Any]] = []

    for old, rows in grouped.items():
        news = {str(row["new"]) for row in rows}
        if len(news) != 1:
            raise RuntimeError(f"Ambiguous repair variants for target: {old!r}")
        new = next(iter(news))
        count = value.count(old)
        if count == 0:
            continue
        if count == 1:
            value = value.replace(old, new, 1)
            applied.append({
                "old": old,
                "new": new,
                "occurrences": 1,
                "mode": "unique_exact",
            })
        else:
            # Safe only because every repair row for this exact old text agrees
            # on the same replacement.
            value = value.replace(old, new)
            applied.append({
                "old": old,
                "new": new,
                "occurrences": count,
                "mode": "identical_multi_exact",
            })

    # The model covered almost every named reference but missed one short
    # dialogue attribution. At this point any surviving exact proper-name token
    # is unauthorized by the typed authority packet, so replace that token only.
    residual_serel = value.count("Serel")
    if residual_serel:
        value = value.replace("Serel", "the mentor")
        applied.append({
            "old": "Serel",
            "new": "the mentor",
            "occurrences": residual_serel,
            "mode": "typed_authority_residual_token_cleanup",
        })

    neutral_repairs = [
        ("She nodded at the tide,", "The mentor nodded at the tide,"),
        ('"Write it," she said.', '"Write it," the mentor said.'),
        ("Then her initials.", "Then the mentor's initials."),
    ]
    for old, new in neutral_repairs:
        count = value.count(old)
        if count:
            value = value.replace(old, new)
            applied.append({
                "old": old,
                "new": new,
                "occurrences": count,
                "mode": "typed_authority_gender_cleanup",
            })

    return value, applied


def run(
    *,
    source_path: Path,
    repair_path: Path,
    out_path: Path,
    story_out_path: Path,
) -> dict[str, Any]:
    source = _read(source_path)
    repair = _read(repair_path)
    story = str(source["english_story"]).strip()
    payload = repair["repair_payload"]
    repaired, applied = apply_recovered_repairs(story, list(payload.get("repairs") or []))

    result = {
        "schema_version": "sonnet55-final-repair-recovery.v1",
        "status": "repaired",
        "source_writer_run_id": source["source_writer_run_id"],
        "repair_run_id": 36564554796,
        "inherited_repair_usage_rollup": repair["repair_usage_rollup"],
        "inherited_incremental_cost_usd": repair["incremental_cost_usd"],
        "inherited_incremental_latency_seconds": repair["incremental_latency_seconds"],
        "original_word_count": count_words(story),
        "repaired_word_count": count_words(repaired),
        "applied_repairs": applied,
        "remaining_serel_tokens": repaired.count("Serel"),
        "repaired_story": repaired,
        "next_stage": "post_repair_reaudit",
    }
    _write(out_path, result)
    story_out_path.parent.mkdir(parents=True, exist_ok=True)
    story_out_path.write_text(repaired.rstrip() + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "applied_groups": len(applied),
        "remaining_serel_tokens": result["remaining_serel_tokens"],
        "original_word_count": result["original_word_count"],
        "repaired_word_count": result["repaired_word_count"],
    }, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--repair", type=Path, default=DEFAULT_REPAIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--story-out", type=Path, default=DEFAULT_STORY_OUT)
    args = parser.parse_args()
    run(
        source_path=args.source,
        repair_path=args.repair,
        out_path=args.out,
        story_out_path=args.story_out,
    )


if __name__ == "__main__":
    main()
