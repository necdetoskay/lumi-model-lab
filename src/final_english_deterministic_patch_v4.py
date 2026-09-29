from __future__ import annotations

import json
from pathlib import Path

from src.generate import count_words

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v3.json"
)
OUT = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v4.json"
)

REPLACEMENTS = [
    (
        "The mentor had said it an hour ago without saying it:",
        "The mentor had said it earlier that afternoon without saying it:",
        "remove inaccurate elapsed-time claim",
    ),
    (
        '"When I file the week\'s calibrations at the harbor office, I\'ll keep this marked provisional. If it\'s nothing, it stays a bounded entry. If it matters later, the limits will already be written beside it."',
        '"Keep it provisional," the mentor said. "The limits stay written beside it. If anyone tests it later, they start from what we actually observed — not from a larger claim."',
        "keep closure in present earned state without future filing commitment",
    ),
]

def apply() -> dict:
    source = json.loads(SOURCE.read_text())
    story = source["english_story"]
    applied = []
    for old, new, why in REPLACEMENTS:
        count = story.count(old)
        if count != 1:
            raise RuntimeError(f"Expected exactly one patch target ({count}): {old}")
        story = story.replace(old, new, 1)
        applied.append({"old": old, "new": new, "why": why})

    words = count_words(story)
    out = {
        **source,
        "english_story": story,
        "deterministic_checks": {
            **source["deterministic_checks"],
            "word_count": words,
            "length_pass": 1600 <= words <= 2500,
            "final_deterministic_patch_v4": True,
        },
        "final_patch_v4_lineage": {
            "schema_version": "final-english-deterministic-patch-v4",
            "patch_count": len(applied),
            "repairs": applied,
            "model_cost_usd": 0,
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out

if __name__ == "__main__":
    value=apply()
    print(json.dumps({
        "word_count": value["deterministic_checks"]["word_count"],
        "length_pass": value["deterministic_checks"]["length_pass"],
        "patch_count": value["final_patch_v4_lineage"]["patch_count"],
    }, indent=2))
