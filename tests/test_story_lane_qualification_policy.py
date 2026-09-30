from pathlib import Path


POLICY=Path("docs/canonical/STORY_LANE_QUALIFICATION_POLICY.md")


def test_policy_forbids_cross_age_auto_promotion() -> None:
    text=POLICY.read_text()
    assert "does not require one universal story-production pipeline" in text
    assert "MUST NOT be automatically promoted to neighboring ages" in text
    assert "SINGLE_CASE_QUALIFIED" in text
    assert "PRODUCTION_STABLE" in text
    assert "the age12 lane must be replaced by the age18 lane" in text


def test_policy_moves_hard_invariants_to_code() -> None:
    text=POLICY.read_text()
    assert "code owns it instead of an LLM judge" in text
    assert "formal reviewed-record ordering" in text
    assert "recurrence versus repeatability" in text
