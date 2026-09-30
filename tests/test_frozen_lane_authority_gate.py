from __future__ import annotations

import json
from pathlib import Path

from src.story_authority_findings import normalize_authority_findings
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.deterministic_story_authority_guards import run_deterministic_authority_guards

APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
FINAL=Path("data/specifications/story_lab/age18_cross_age_final_delivery_v1.json")


def test_generic_authority_gate_prompt_has_no_case_names() -> None:
    text=Path("prompts/story_compact_authority_gate_v4_generic.md").read_text()
    for name in ["Deniz","Beacon Ridge","Meridian Harbor","Leyra","Ashen Gate","Greyfen"]:
        assert name not in text


def test_clean_control_has_no_deterministic_hard_findings() -> None:
    approved=json.loads(APPROVED.read_text())
    final=json.loads(FINAL.read_text())
    packet=build_story_authority_packet_v2(approved)
    findings=run_deterministic_authority_guards(final["accepted_english_master"],packet)
    assert findings==[]


def test_authority_finding_normalizer_accepts_single_span_quote() -> None:
    story="# T\nA fact is asserted. Another sentence."
    payload={"findings":[{
        "family":"canon_integrity",
        "severity":"serious",
        "repair_scope":"local",
        "span_ids":["S002"],
        "exact_quote":"A fact is asserted.",
        "reason":"unsupported"
    }]}
    rows=normalize_authority_findings(payload,story)
    assert len(rows)==1
    assert rows[0]["exact_quote"]=="A fact is asserted."
