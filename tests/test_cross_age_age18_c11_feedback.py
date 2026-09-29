from __future__ import annotations

import json
from pathlib import Path


FEEDBACK = Path(
    "data/specifications/story_lab/"
    "sonnet55_cross_age_age18_c11_revision_feedback.json"
)
PROMPT = Path("prompts/episode_spine_architect_v2.md")


def test_age18_c11_feedback_preserves_branch_asymmetry() -> None:
    value = json.loads(FEEDBACK.read_text())
    text = json.dumps(value)
    assert value["verdict"] == "REVISE"
    assert "fresh setup branch produces stronger evidence but no reviewed formal log" in text
    assert "provisional record branch produces a reviewed bounded log with no advisory" in text
    assert "No route advisory or closure" in text or "no route advisory or closure" in text


def test_architect_prompt_forbids_global_branch_rule_conflicts() -> None:
    text = PROMPT.read_text()
    assert "Global rules must not contradict branch-specific rules" in text
    assert "no UNPLANNED new evidence in the climax" in text
    assert "never claim that a reviewed record exists globally" in text
