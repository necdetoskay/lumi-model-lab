from pathlib import Path


def test_v17_prompt_is_complete_and_compact():
    prompt = Path("prompts/spineforge_compact_complete_auditor_v17.md").read_text(encoding="utf-8")
    assert "exactly 18 dimension objects" in prompt
    assert "Never omit FRESHNESS." in prompt
    assert "exactly 1 short evidence string per dimension" in prompt
    assert "no essays" in prompt
    assert "Judge the actual supplied Spine, not previous versions." in prompt
