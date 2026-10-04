"""Lossless model-facing projection; immutable runtime artifacts stay intact."""
from copy import deepcopy


def project_payload(payload: dict) -> dict:
    wire = deepcopy(payload)
    for text_key, rows_key in (("full_story", "story_segments"),
                               ("source_scene", "source_scene_segments"),
                               ("replacement_scene", "replacement_scene_segments")):
        if text_key not in wire or not wire.get(rows_key):
            continue
        text = wire[text_key]
        spans = []
        cursor = 0
        seen = set()
        for row in wire[rows_key]:
            current = row.get("repaired_text", row.get("text"))
            sid = row["span_id"]
            if not isinstance(current, str) or not current or sid in seen:
                raise RuntimeError("Invalid current segment for wire projection")
            start = text.find(current, cursor)
            if start < 0 or text[cursor:start].strip():
                raise RuntimeError("Wire segments do not cover current prose")
            end = start + len(current)
            spans.append([sid, text[cursor:start], current])
            seen.add(sid)
            cursor = end
        if text[cursor:].strip():
            raise RuntimeError("Wire segments omit trailing prose")
        wire.pop(text_key)
        wire[rows_key] = {"replaces_text_field": text_key,
                          "columns": ["span_id", "whitespace_before", "current_text"],
                          "trailing_whitespace": text[cursor:], "spans": spans}
    approved = wire.get("approved_constraints") or {}
    quoted = {row["text"] for row in approved.get("constraints", [])}
    if quoted and "canon_invariants" in wire:
        # Preserve extra invariants; only exact duplicate quotes can be removed.
        wire["canon_invariants"] = [s for s in wire["canon_invariants"] if s not in quoted]
    wire["wire_projection"] = "spineforge-v21-lossless-wire.v1"
    return wire
