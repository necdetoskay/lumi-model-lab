from __future__ import annotations

import json
from pathlib import Path

from src.generate import count_words

ENGLISH=Path("data/specifications/story_lab/age18_cross_age_c41_deterministic_recovered_story.txt")
APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
C4=Path("data/specifications/story_lab/age18_cross_age_c4_run_36618878723.json")
C41=Path("data/specifications/story_lab/age18_cross_age_c41_deterministic_recovery_evidence.json")


def test_c5_translation_inputs_are_green_and_scoped() -> None:
    approved=json.loads(APPROVED.read_text())
    c4=json.loads(C4.read_text())
    c41=json.loads(C41.read_text())
    english=ENGLISH.read_text()
    assert approved["episode_spine"]["exact_age"]==18
    assert c4["status"]=="repaired_guard_clean"
    assert c41["status"]=="GREEN"
    assert c41["post_recovery_findings"]==[]
    assert c41["incremental_cost_usd"]==0.0
    assert count_words(english)==2176
    assert c4["pipeline_usage_rollup"]["totals"]["cost_usd"]==0.15627555
