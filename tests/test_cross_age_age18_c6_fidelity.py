from __future__ import annotations

import json
from pathlib import Path

C5=Path("data/specifications/story_lab/age18_cross_age_c5_run_36620129124.json")
PRE=Path("data/specifications/story_lab/age18_cross_age_c5_human_translation_preaudit.json")


def test_c6_source_is_translation_only_output() -> None:
    c5=json.loads(C5.read_text())
    assert c5["status"]=="translated_awaiting_fidelity"
    assert c5["translator_model"]=="google/gemini-3.8-flash"
    assert c5["english_word_count"]==2176
    assert c5["turkish_word_count"]==1814
    assert c5["next_stage"]=="AGE18_C6_LUNA_FIDELITY_ONLY"
    assert c5["next_stage_authorized"] is False


def test_human_preaudit_keeps_fidelity_boundary_explicit() -> None:
    pre=json.loads(PRE.read_text())
    ids={row["id"] for row in pre["confirmed_or_review_targets"]}
    assert "title_modality_shift" in ids
    assert "recurrence_vs_repeatability_shift" in ids
    assert pre["decision"]["publication_ready"] is False
    assert pre["decision"]["paid_next_stage_authorized"] is False


def test_c6_module_imports_and_uses_luna_only() -> None:
    import src.cross_age_age18_c6_fidelity as module
    assert module.FIDELITY_MODEL=="openai/gpt-5.6-luna"
