from __future__ import annotations

import json
from pathlib import Path

from src.generate import count_words

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source.json"
)
OUT = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source_v3.json"
)

REPLACEMENTS = [
    (
        "The first reading all afternoon that the official chart would have accepted.",
        "The first reading in the series that reached the table's accepted edge.",
        "scope acceptance claim to the five-reading series",
    ),
    (
        '"It moves with the tide.',
        '"It looks like it moves with the tide.',
        "frame Deniz's tide claim explicitly as a hypothesis",
    ),
    (
        "The iron in your frame cooled.",
        "The iron in your frame may have cooled.",
        "keep cooling as an unmeasured confound, not an established fact",
    ),
    (
        "The clamp you tightened at the start has been settling into the stone for two hours.",
        "The clamp you checked may have been settling into the stone.",
        "remove inaccurate duration and keep settlement as a possibility",
    ),
    (
        "Or enough time to break down the setup, re-level the frame from scratch, re-mount it, and take one fresh reading — the test that would show whether the original setup itself was the culprit.",
        "Or enough time to break down the setup, re-level the frame from scratch, re-mount it, and take one fresh reading — a test of whether a similar offset survived one fresh setup.",
        "align fresh-setup purpose with the validated evidence ceiling",
    ),
    (
        "Deniz thought, briefly, of the drowned causeway that showed itself only at rare low tides — perhaps the official tables had missed something about the tides. Maybe this stone kept its own tide-lore too.",
        "Deniz wondered, briefly, whether the pattern belonged to the beacon at all — or only to the setup and the passing afternoon.",
        "remove wider tide-lore speculation while preserving character uncertainty",
    ),
    (
        "If it matched the series, the setup would be partly cleared — and there would be no time to log anything, and the whole afternoon would exist only in memory and loose notes.",
        "If it matched the series, the original setup would look less likely as the sole explanation — and there would be no time to complete a reviewed entry.",
        "weaken fresh-setup inference and preserve record-state semantics",
    ),
    (
        "If it didn't match, the series would be suspect, and there would still be no time to write down why.",
        "If it didn't match, the series would be more doubtful, and there would still be no time to complete a reviewed entry.",
        "keep alternate fresh-setup result bounded",
    ),
    (
        "A retest bought a private answer.",
        "A retest bought one more piece of evidence.",
        "avoid overstating one fresh reading as an answer",
    ),
    (
        '"One fresh reading either proves or doubts my series, and either way it dies with me on this rock.',
        '"One fresh reading could strengthen or weaken my confidence in the series, and either way there would be no time for a reviewed entry.',
        "align Deniz's branch reasoning with the evidence ceiling",
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
            "final_deterministic_patch_v3": True,
        },
        "final_patch_v3_lineage": {
            "schema_version": "final-english-deterministic-patch-v3",
            "patch_count": len(applied),
            "repairs": applied,
            "model_cost_usd": 0,
        },
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out

if __name__ == "__main__":
    result = apply()
    print(json.dumps({
        "word_count": result["deterministic_checks"]["word_count"],
        "length_pass": result["deterministic_checks"]["length_pass"],
        "patch_count": result["final_patch_v3_lineage"]["patch_count"],
    }, indent=2))
