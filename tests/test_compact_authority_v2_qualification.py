from __future__ import annotations

import json
from pathlib import Path

from src.compact_authority_v2_qualification import normalize_findings_v2
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_canon_authority_qualification import _gold_segment_map

SOURCE=Path("data/specifications/story_lab/age18_cross_age_c2_postprocess_source_36612862926.json")
APPROVED=Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
GOLD=Path("data/specifications/story_lab/age18_cross_age_c2_confirmed_authority_gold.json")
RUN=Path("data/specifications/story_lab/age18_cross_age_c3_run_36614762650.json")


def test_v2_gold_is_scoreable_and_hidden_from_packet() -> None:
    source=json.loads(SOURCE.read_text())
    approved=json.loads(APPROVED.read_text())
    gold=json.loads(GOLD.read_text())
    mapping=_gold_segment_map(source["english_story"],gold["targets"])
    packet=build_story_authority_packet_v2(approved)
    assert len(mapping)==3
    text=json.dumps(packet,ensure_ascii=False)
    assert "PROVISIONAL RECORD FILED AT HARBOR." not in text
    assert "the next person sent to Beacon Ridge would start from a blank page" not in text


def test_v2_normalizer_salvages_previous_multispan_ellipsis_quote() -> None:
    source=json.loads(SOURCE.read_text())
    old=json.loads(RUN.read_text())
    payload={"findings":[old["raw_model_payload"]["findings"][4]]}
    findings=normalize_findings_v2(payload,source["english_story"])
    assert len(findings)>=2
    assert all("..." not in row["exact_quote"] for row in findings)
    assert all(len(row["span_ids"])==1 for row in findings)


def test_v2_prompt_requires_single_span_verbatim_quotes() -> None:
    text=Path("prompts/story_compact_authority_gate_v3.md").read_text()
    assert "exact_quote MUST be verbatim text from ONE cited span" in text
    assert "separate findings rather than joining quotations with ellipses" in text
