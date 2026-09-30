from __future__ import annotations

import json
from pathlib import Path

from src.episode_spine_safe_normalize_v2 import normalize_episode_spine_syntax
from src.episode_writer_v2_generate import build_writer_input

LEYRA_SOURCE=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f1_recovery_source_36656865491.json"
)
AGE18_APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")


def test_generic_normalizer_recovers_omitted_final_return_without_story_edits() -> None:
    source=json.loads(LEYRA_SOURCE.read_text())
    raw=source["architect_raw_payload"]
    normalized,repairs=normalize_episode_spine_syntax(raw)
    assert any(x["kind"]=="append_omitted_final_return" for x in repairs)
    assert normalized["logistics_plan"]["location_sequence"]==[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    clone=json.loads(json.dumps(raw))
    clone["logistics_plan"]["location_sequence"]=[
        "vellum_hall","greyfen","ashen_gate","greyfen"
    ]
    assert normalized==clone


def test_generic_writer_can_use_authority_packet_v2() -> None:
    approved=json.loads(AGE18_APPROVED.read_text())
    payload=build_writer_input(approved,authority_packet_version="v2")
    assert payload["authority_packet"]["schema_version"]=="story-authority-packet.v2"
    assert payload["authority_packet_version"]=="v2"


def test_generic_v3_prompts_have_no_qualified_case_names() -> None:
    paths=[
        Path("prompts/episode_spine_architect_v3_generic.md"),
        Path("prompts/episode_spine_gate_v3_generic.md"),
        Path("prompts/episode_writer_v3_generic.md"),
    ]
    forbidden=[
        "Deniz","Beacon Ridge","Meridian Harbor",
        "Leyra","Ashen Gate","Greyfen",
    ]
    text="\n".join(p.read_text() for p in paths)
    for name in forbidden:
        assert name not in text
    assert "Age 12" not in text
