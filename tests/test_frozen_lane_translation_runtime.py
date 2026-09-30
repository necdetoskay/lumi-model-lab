from __future__ import annotations
from pathlib import Path


def test_translation_runtime_has_no_case_names() -> None:
    paths=[
        Path("prompts/translation_en_tr_v2_generic.md"),
        Path("prompts/translation_fidelity_gate_v2_generic.md"),
        Path("prompts/translation_fidelity_adjudicator_v1_generic.md"),
        Path("prompts/translation_local_repair_v1_generic.md"),
        Path("src/episode_translation_v1.py"),
        Path("src/episode_translation_repair_v1.py"),
        Path("src/episode_fidelity_v1.py"),
        Path("src/episode_fidelity_adjudication_v1.py"),
        Path("src/episode_final_delivery_v1.py"),
    ]
    text="\n".join(p.read_text() for p in paths)
    for name in ["Deniz","Beacon Ridge","Meridian Harbor","Leyra","Ashen Gate","Greyfen"]:
        assert name not in text


def test_translation_repair_is_bounded_to_one_attempt() -> None:
    text=Path("src/episode_translation_repair_v1.py").read_text()
    assert "MAX_REPAIR_ATTEMPTS=1" in text
    assert "Translation repair attempt limit reached." in text


def test_fidelity_does_not_call_luna_when_deterministic_semantic_findings_exist() -> None:
    text=Path("src/episode_fidelity_v1.py").read_text()
    hard_index=text.index("if hard:")
    key_index=text.index('key=api_key or os.getenv("OPENROUTER_API_KEY")')
    assert hard_index < key_index


def test_finalizer_requires_publication_ready() -> None:
    text=Path("src/episode_final_delivery_v1.py").read_text()
    assert 'source.get("publication_ready") is not True' in text
