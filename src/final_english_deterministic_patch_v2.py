from __future__ import annotations

import json
from pathlib import Path

from src.generate import count_words

SOURCE = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_repaired_postprocess_source.json"
)
OUT = Path(
    "data/specifications/story_lab/age12_episode1_sonnet55_final_english_source.json"
)

REPLACEMENTS = [
    (
        "Above, at the ridge tip, the old magnetic-stone beacon stood in its bronze housing, marked by years of weather.",
        "Above, at the ridge tip, the magnetic-stone beacon stood in its bronze housing, dark with blown spray.",
        "remove unsupported beacon age/history",
    ),
    (
        "Deniz unfolded the frame, set it on the marked stone platform, and sighted along the index line to the beacon.",
        "Deniz unfolded the frame, set it on the flat stone platform, and sighted along the index line to the beacon.",
        "remove unsupported durable platform mark",
    ),
    (
        "Deniz read the angle against the founder's line, jotted the number, then checked the tide table for the current height of water.",
        "Deniz read the angle against the reference line, jotted the number, then checked the tide table for the current height of water.",
        "remove unsupported founder history",
    ),
    (
        "The table allowed the beacon's pull to wander two degrees either side of the founder's line at this tide.",
        "The table allowed the beacon's pull to wander two degrees either side of the reference line at this tide.",
        "use neutral measurement reference",
    ),
    (
        "The beacon's stone housing came next: no cracks in the bronze, no shingle wedged underneath, the stone seated exactly as the ledger sketch showed.",
        "The beacon's stone housing came next: no cracks in the bronze, no shingle wedged underneath, and the stone sat squarely in its housing.",
        "remove unsupported prior ledger configuration",
    ),
    (
        "Offset past the founder's line: two and three-quarters degrees.",
        "Offset past the reference line: two and three-quarters degrees.",
        "use neutral measurement reference",
    ),
    (
        "Offset: two and a quarter.",
        "Offset: two and a half degrees.",
        "repair monotonic five-reading series",
    ),
    (
        "Offset: one and a half.",
        "Offset: two and a quarter degrees.",
        "repair monotonic five-reading series",
    ),
    (
        "Offset: three-quarters.",
        "Offset: two and a tenth degrees.",
        "repair monotonic five-reading series",
    ),
    (
        "Offset: dead on the table's edge.",
        "Offset: two degrees, exactly the table's edge.",
        "make final reading numerically explicit",
    ),
    (
        "Then Deniz laid the ledger's calibration page beside it — the record from the last annual check, with the founder's alignment mark drawn in faded brown ink, the baseline every reading was measured against.",
        "Then Deniz laid the official calibration table beside it, with its reference line — the baseline every reading was measured against.",
        "remove unsupported annual history and founder mark",
    ),
    (
        "Stone fixed in its bronze housing beside the founder's line cut into the rock.",
        "Stone fixed in its bronze housing above the platform.",
        "remove unsupported founder history",
    ),
    (
        "A record bought a date in a ledger that other surveyors could pick up next season and test properly, with two setups and a full tide.",
        "A record bought a date in a ledger that could be tested later with two setups and a full tide.",
        "keep reusability without guaranteeing future actors/timing",
    ),
    (
        "The offset started two and three-quarters degrees past the founder's line and fell in order to the table's edge as the tide dropped.",
        "The offset started two and three-quarters degrees past the reference line and fell in order to the table's edge as the tide dropped.",
        "use neutral measurement reference",
    ),
    (
        "Offset from founder's line observed beyond tabled allowance at high ebb, decreasing in ordered sequence across five timestamped, tide-paired readings under a single unchanged setup.",
        "Offset from reference line observed beyond tabled allowance during the ebb, decreasing in ordered sequence across five timestamped, tide-paired readings under a single unchanged setup.",
        "fix authority and tide-phase wording",
    ),
    (
        "They packed the instruments together, the tide just beginning to creep back up the bronze staff.",
        "They packed the instruments together, the water nearly slack at the bronze staff.",
        "keep stow action before the tide turn",
    ),
    (
        '"When I file the week\'s calibrations at the harbor office, I\'ll raise it with the pilots. Quietly. If it\'s nothing, it dies in a drawer. If it\'s not nothing, they\'ll have heard it from a calibration ledger, not from a rumor about a child with a compass."',
        '"When I file the week\'s calibrations at the harbor office, I\'ll keep this marked provisional. If it\'s nothing, it stays a bounded entry. If it matters later, the limits will already be written beside it."',
        "remove unearned pilot/social-spread outcome while preserving durable record payoff",
    ),
    (
        "Deniz looked at the old stone in its bronze housing, holding its small stubborn pull against the returning sea, and carried the question down the ridge like a third instrument: a fluke of this one beacon — or the first visible crack between the old markers and every chart the harbor had ever printed?",
        "Deniz looked at the stone in its bronze housing, holding its small stubborn pull against the returning sea, and carried the question down the ridge like a third instrument: a fluke of this one beacon — or something the official charts had not yet learned how to explain?",
        "preserve forward hook without asserting broader marker history",
    ),
    (
        "The tide turned. Perhaps the pilots would be talking soon.",
        "Behind them, the tide turned.",
        "remove unearned future social spread",
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

    out = {
        **source,
        "english_story": story,
        "deterministic_checks": {
            **source["deterministic_checks"],
            "word_count": count_words(story),
            "length_pass": 1600 <= count_words(story) <= 2500,
            "final_deterministic_patch_v2": True,
        },
        "final_patch_lineage": {
            "schema_version": "final-english-deterministic-patch-v2",
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
        "patch_count": result["final_patch_lineage"]["patch_count"],
    }, indent=2))
