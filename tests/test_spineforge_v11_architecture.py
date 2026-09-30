from pathlib import Path

from src.spineforge_v11 import SONNET_MODEL


def test_v11_has_one_model_owner():
    assert SONNET_MODEL == "anthropic/claude-sonnet-5.5"
    source = Path("src/spineforge_v11.py").read_text(encoding="utf-8")
    assert "aion-labs/" not in source
    assert "openai/gpt-" not in source


def test_v11_does_not_auto_repair_or_authorize_writer():
    source = Path("src/spineforge_v11.py").read_text(encoding="utf-8")
    assert '"automatic_repair_enabled": False' in source
    assert '"writer_authorized": False' in source
    assert '"automatic_execution": False' in source


def test_architect_prompt_is_roleplay_first():
    prompt = Path("prompts/spineforge_single_owner_architect_v11.md").read_text(encoding="utf-8")
    required = [
        "interactive-fiction / roleplay story architect",
        "active protagonist agency",
        "roleplay density",
        "sceneability",
        "at least three distinct forms of protagonist engagement",
        "action -> consequence -> new pressure -> new choice",
        "The protagonist must not be a passenger",
        "Final self-test before returning JSON",
    ]
    for phrase in required:
        assert phrase in prompt


def test_auditor_explicitly_attacks_roleplay_and_story_quality():
    prompt = Path("prompts/spineforge_single_owner_auditor_v11.md").read_text(encoding="utf-8")
    for phrase in [
        "try to prove the spine is not ready",
        "ROLEPLAY_POTENTIAL",
        "CHARACTER_DRIVENNESS",
        "WORLD_SPECIFICITY",
        "A structurally valid spine can still be a weak story",
    ]:
        assert phrase in prompt
