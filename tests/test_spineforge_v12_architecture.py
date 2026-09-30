from pathlib import Path

from src.spineforge_v12 import SONNET_MODEL


def test_v12_keeps_single_owner_architecture() -> None:
    assert SONNET_MODEL == "anthropic/claude-sonnet-5.5"
    source = Path("src/spineforge_v12.py").read_text(encoding="utf-8")
    assert "aion-labs/" not in source
    assert "openai/gpt-" not in source
    assert '"automatic_repair_enabled": False' in source
    assert '"writer_authorized": False' in source


def test_v12_changes_prompt_revision_not_pipeline_topology() -> None:
    source = Path("src/spineforge_v12.py").read_text(encoding="utf-8")
    assert "spineforge_roleplay_architect_v12.md" in source
    assert "spineforge_roleplay_auditor_v12.md" in source
    assert "SONNET_STORY_SPINE_ARCHITECT" in source
    assert "DETERMINISTIC_CONTRACT_AND_AUTHORITY_VALIDATION" in source
    assert "SONNET_AGGRESSIVE_RED_TEAM_AUDIT" in source
