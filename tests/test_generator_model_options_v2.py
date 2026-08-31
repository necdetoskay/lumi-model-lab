from src.generate import build_model_options


def test_glm_53_flash_uses_low_reasoning_instead_of_disabling_it() -> None:
    options = build_model_options("z-ai/glm-5.3-flash", 42)

    assert options["reasoning"] == {
        "enabled": True,
        "effort": "low",
        "exclude": True,
    }
    assert options["max_tokens"] == 10000
    assert options["seed"] == 42
