from pathlib import Path

from src.narrative_spine_v1_contract import SpineProductGateV19
from src.spineforge_v19 import LUNA_MODEL, SONNET_MODEL


def test_v19_model_ownership_is_simple_and_writer_is_absent():
    source = Path("src/spineforge_v19.py").read_text(encoding="utf-8")
    assert SONNET_MODEL == "anthropic/claude-sonnet-5.5"
    assert LUNA_MODEL == "openai/gpt-5.6-luna"
    assert "aion-labs/" not in source
    assert "writer_authorized" in source
    assert '"writer_authorized": False' in source
    assert "automatic_retry_enabled" in source
    assert '"automatic_retry_enabled": False' in source


def test_architect_prompt_rejects_legacy_phase_forcing():
    prompt = Path("prompts/spineforge_v19_narrative_architect.md").read_text(encoding="utf-8")
    for phrase in [
        "single creative owner",
        "Internally consider multiple plausible concepts",
        "Do not force COMPLICATION, REVERSAL, DECISION, CLIMAX, PAYOFF labels",
        "difficult vocabulary as camouflage",
        "The ContextPack is reveal-safe",
    ]:
        assert phrase in prompt


def test_gate_prompt_is_compact_blocker_only():
    prompt = Path("prompts/spineforge_v19_product_gate.md").read_text(encoding="utf-8")
    for phrase in [
        "Do not score dimensions",
        "Report only concrete blocking findings",
        "ACCEPT",
        "REPAIR",
        "REPLAN",
    ]:
        assert phrase in prompt
    assert len(str(SpineProductGateV19.model_json_schema(by_alias=True)).encode("utf-8")) < 4096


def test_no_paid_trigger_exists_for_v19():
    assert not Path("experiments/triggers/spineforge-v19.json").exists()
