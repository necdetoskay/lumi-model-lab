from __future__ import annotations

from pathlib import Path

from src.deterministic_translation_semantic_guards import run_translation_semantic_guards

EN=Path("data/specifications/story_lab/age18_cross_age_c41_deterministic_recovered_story.txt")
RAW_TR=Path("data/specifications/story_lab/age18_cross_age_c5_story_tr.txt")
FINAL_TR=Path("data/specifications/story_lab/age18_cross_age_c61_final_story_tr.txt")


def test_raw_c5_translation_catches_both_confirmed_semantic_shifts() -> None:
    findings=run_translation_semantic_guards(EN.read_text(),RAW_TR.read_text())
    ids={x["guard_id"] for x in findings}
    assert ids=={
        "title_modality_preservation",
        "recurrence_repeatability_distinction",
    }


def test_final_c61_translation_is_guard_clean() -> None:
    assert run_translation_semantic_guards(EN.read_text(),FINAL_TR.read_text())==[]


def test_title_without_source_modality_does_not_require_turkish_modality() -> None:
    source="# The Closed Route\n\nRoute advisory NOT recommended."
    tr="# Kapalı Rota\n\nRota uyarısı TAVSİYE EDİLMEZ."
    assert run_translation_semantic_guards(source,tr)==[]


def test_distinct_recurrence_and_repeatability_terms_are_allowed() -> None:
    source=(
        "# The Route That Might Close\n\n"
        "Independent repeatable support is required. Recurrence unknown. "
        "Route advisory NOT recommended."
    )
    tr=(
        "# Kapanması Gerekebilecek Rota\n\n"
        "Bağımsız ve tekrarlanabilir destek gerekir. "
        "Sapmanın yeniden ortaya çıkıp çıkmayacağı bilinmiyor. "
        "Rota uyarısı TAVSİYE EDİLMEZ."
    )
    assert run_translation_semantic_guards(source,tr)==[]


def test_missing_no_advisory_negation_is_blocked() -> None:
    source="# A Route\n\nRoute advisory NOT recommended."
    tr="# Bir Rota\n\nRota uyarısı değerlendirildi."
    findings=run_translation_semantic_guards(source,tr)
    assert {x["guard_id"] for x in findings}=={"no_advisory_negation"}
