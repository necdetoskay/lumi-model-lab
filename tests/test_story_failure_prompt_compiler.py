from src.story_failure_prompt_compiler import compile_negative_constraints, render_writer_negative_prompt


def test_age4_turkish_compiles_high_value_rules_without_whole_registry():
    rules = compile_negative_constraints(
        language="tr",
        exact_age=4,
        story_type="nature",
        target_words=500,
        max_rules=12,
    )
    ids = {row["id"] for row in rules}
    assert "FP-TR-001" in ids
    assert "FP-DIDACTIC-001" in ids
    assert "FP-CANON-001" in ids
    assert "FP-LENGTH-001" in ids
    assert "FP-STRUCT-001" not in ids
    assert len(rules) <= 12


def test_long_form_adds_long_form_constraints():
    rules = compile_negative_constraints(
        language="tr",
        exact_age=10,
        story_type="mystery",
        target_words=2000,
        max_rules=20,
    )
    ids = {row["id"] for row in rules}
    assert "FP-STRUCT-001" in ids
    assert "FP-STRUCT-002" in ids


def test_render_is_compact_and_failure_aware():
    prompt = render_writer_negative_prompt(
        language="tr",
        exact_age=4,
        story_type="nature",
        target_words=500,
        max_rules=8,
    )
    assert "FAILURE-AWARE CONSTRAINTS" in prompt
    assert prompt.count("\n- [") <= 8
