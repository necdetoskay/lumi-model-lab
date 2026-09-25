from src.story_voice_prompt_compiler import render_positive_voice_prompt


def test_age4_turkish_voice_profile_compiles():
    prompt = render_positive_voice_prompt(language="tr", exact_age=4)
    assert "POSITIVE EXACT-AGE VOICE" in prompt
    assert "A4-DIALOGUE" in prompt
    assert "A4-CAREGIVER" in prompt
    assert "A4-PEER" in prompt


def test_unknown_profile_is_empty():
    assert render_positive_voice_prompt(language="tr", exact_age=17) == ""
