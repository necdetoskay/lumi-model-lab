from pathlib import Path


def test_v16_repair_prompt_forbids_invented_evidence_mechanics():
    prompt = Path("prompts/spineforge_evidence_logic_repair_v16.md").read_text(encoding="utf-8")
    for phrase in [
        "Do not invent legal-map bearings",
        "Do not claim that equal offsets reveal hidden geometry.",
        "Do not claim what magical residue would do.",
        "Remove arbitrary peg-order mechanics.",
        "SUCCESS means the relevant observed response recurs",
        "middle measurement beat must gain a concrete external complication",
    ]:
        assert phrase in prompt


def test_v16_reauditor_requires_all_18_dimensions():
    prompt = Path("prompts/spineforge_complete_reauditor_v16.md").read_text(encoding="utf-8")
    assert "exactly 18 objects" in prompt
    assert "Never omit FRESHNESS." in prompt
    assert "silently count the array" in prompt
