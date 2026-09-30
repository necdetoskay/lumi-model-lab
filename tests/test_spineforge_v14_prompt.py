from pathlib import Path


def test_v14_prompt_is_targeted_not_regenerative():
    prompt = Path("prompts/spineforge_targeted_semantic_repair_v14.md").read_text(encoding="utf-8")
    required = [
        "You do not invent a new episode from scratch.",
        "Repair the diagnosed dramatic defects",
        "Do not perform a cosmetic rewrite.",
        "branches must create meaningfully different executable actions",
        "The writer must not need to invent the missing dramatic engine.",
        "Never invent hidden Saga truth.",
        "Check every audit repair target is addressed.",
        "Check every preserve item still exists.",
    ]
    for phrase in required:
        assert phrase in prompt
