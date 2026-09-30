from __future__ import annotations
from pathlib import Path


def test_generic_adjudication_and_repair_sources_have_no_case_names() -> None:
    paths=[
        Path("prompts/story_authority_adjudicator_v1_generic.md"),
        Path("src/episode_authority_adjudication_v1.py"),
        Path("src/episode_bounded_repair_v1.py"),
    ]
    text="\n".join(p.read_text() for p in paths)
    for name in ["Deniz","Beacon Ridge","Meridian Harbor","Leyra","Ashen Gate","Greyfen"]:
        assert name not in text


def test_adjudicator_prompt_cannot_find_new_defects() -> None:
    text=Path("prompts/story_authority_adjudicator_v1_generic.md").read_text()
    assert "NOT to find new defects" in text
    assert "CONFIRM" in text and "REJECT" in text


def test_bounded_repair_is_single_local_scope_runtime() -> None:
    text=Path("src/episode_bounded_repair_v1.py").read_text()
    assert "refuses non-local findings" in text
    assert "minimal_exact_replacements_only" in text
    assert "do_not_rewrite_unaffected_prose" in text


def test_english_bounded_repair_is_limited_to_one_attempt() -> None:
    text=Path("src/episode_bounded_repair_v1.py").read_text()
    assert "MAX_REPAIR_ATTEMPTS=1" in text
    assert "English bounded repair attempt limit reached." in text
