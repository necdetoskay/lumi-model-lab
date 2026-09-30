from pathlib import Path


def test_v15_prompt_is_narrow_and_authority_safe():
    prompt = Path("prompts/spineforge_convergence_repair_v15.md").read_text(encoding="utf-8")
    required = [
        "You are not an Architect.",
        "Do not restart the plot.",
        "A map that does not show a road cannot be used as evidence for the exact geometry of that road.",
        "Maren cannot suddenly appear where the scene needs pressure.",
        "define SUCCESS, PARTIAL, and FAILURE states",
        "keep `outcome_uncommitted=true`",
        "The two branches must not converge on the same final image",
        "no erased-road geometry is asserted",
    ]
    for phrase in required:
        assert phrase in prompt
