from pathlib import Path


def test_v18_prompt_relies_on_provider_enforced_shape():
    prompt = Path("prompts/spineforge_strict_complete_auditor_v18.md").read_text(encoding="utf-8")
    assert "provider enforces your output structure" in prompt
    assert "Do not rewrite or repair it." in prompt
    assert "Return only the provider-enforced JSON object." in prompt
