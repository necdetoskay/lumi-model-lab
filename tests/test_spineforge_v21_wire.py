import json
from copy import deepcopy
from pathlib import Path
import pytest

from src.spineforge_v21_simulation import simulate_case
from src.spineforge_v21_wire import project_payload


def test_real_harness_preserves_every_current_span_and_constraint(tmp_path):
    simulate_case("repair_succeeds", tmp_path)
    result = json.loads((tmp_path / "repair_succeeds/v21-bounded-quality-result.json").read_text())
    for call in result["quality_calls"]:
        original = call["input"]
        before = deepcopy(original)
        wire = call["response"]["request"]["wire_payload"]
        assert original == before
        assert wire["approved_constraints"] == original["approved_constraints"]
        assert set(original["canon_invariants"]) <= (
            set(wire["canon_invariants"]) | {r["text"] for r in wire["approved_constraints"]["constraints"]})
        for text_key, rows_key in (("full_story", "story_segments"),
                                   ("source_scene", "source_scene_segments"),
                                   ("replacement_scene", "replacement_scene_segments")):
            if text_key not in original:
                continue
            assert text_key not in wire
            table = wire[rows_key]
            assert "".join(gap + text for _, gap, text in table["spans"]) + table["trailing_whitespace"] == original[text_key]
            assert len(wire[rows_key]["spans"]) == len(original[rows_key])
            for row, (sid, gap, text) in zip(original[rows_key], wire[rows_key]["spans"]):
                assert sid == row["span_id"]
                assert text == row.get("repaired_text", row.get("text"))
        for key in ("entry_boundary", "exit_boundary", "blocking_findings", "original_blocking_findings"):
            if key in original:
                assert wire[key] == original[key]
        if call["stage"] == "INITIAL_AUDIT":
            assert len(json.dumps(wire)) < len(json.dumps(original)) * .5
        if call["stage"] == "FINAL_AUDIT":
            assert "full_story" not in wire


def test_projection_is_pure_and_preserves_unicode_repeated_text_and_extra_constraints():
    p = {"full_story": "İp.\n\nİp. 🪢", "story_segments": [
        {"span_id": "S1", "repaired_text": "İp.", "source_text": "OLD"},
        {"span_id": "S2", "repaired_text": "İp. 🪢"}],
        "approved_constraints": {"constraints": [{"text": "same"}]},
        "canon_invariants": ["same", "extra"]}
    before = deepcopy(p)
    w = project_payload(p)
    assert p == before
    assert w["canon_invariants"] == ["extra"]
    assert w["story_segments"]["spans"] == [["S1", "", "İp."], ["S2", "\n\n", "İp. 🪢"]]
    assert "OLD" not in json.dumps(w)


@pytest.mark.parametrize("text", ["missing prefix. present.", "present. missing suffix."])
def test_projection_rejects_incomplete_mapping(text):
    with pytest.raises(RuntimeError, match="prose"):
        project_payload({"full_story": text, "story_segments": [{"span_id": "S1", "text": "present."}]})
