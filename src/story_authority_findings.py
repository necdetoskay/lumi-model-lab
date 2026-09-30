from __future__ import annotations

import re
from typing import Any

from src.story_defect_detection import segment_story


def normalize_authority_findings(
    payload: dict[str, Any],
    story: str,
) -> list[dict[str, Any]]:
    segments = segment_story(story)
    by_id = {str(seg["id"]): str(seg["text"]) for seg in segments}
    out: list[dict[str, Any]] = []

    for row in payload.get("findings") or []:
        severity = str(row.get("severity") or "").lower()
        if severity not in {"serious", "critical"}:
            continue

        family = str(row.get("family") or "canon_integrity")
        scope = str(row.get("repair_scope") or "local").lower()
        if scope not in {"local", "structural", "replan"}:
            scope = "local"

        span_ids = [str(x) for x in (row.get("span_ids") or []) if str(x) in by_id]
        quote = str(row.get("exact_quote") or "").strip()
        reason = str(row.get("reason") or "").strip()
        if not span_ids or not quote:
            continue

        direct = [sid for sid in span_ids if quote in by_id[sid]]
        if direct:
            out.append({
                "family": family,
                "severity": severity,
                "repair_scope": scope,
                "span_ids": direct,
                "exact_quote": quote,
                "reason": reason,
            })
            continue

        embedded = [
            (by_id[sid], sid)
            for sid in span_ids
            if by_id[sid] and by_id[sid] in quote
        ]
        if embedded:
            for fragment, sid in embedded:
                out.append({
                    "family": family,
                    "severity": severity,
                    "repair_scope": scope,
                    "span_ids": [sid],
                    "exact_quote": fragment,
                    "reason": reason,
                    "normalization_note": "Split from a model-supplied multi-span combined quote.",
                })
            continue

        fragments = [
            x.strip()
            for x in re.split(r"\s*(?:\.\.\.|…)\s*", quote)
            if x.strip()
        ]
        if len(fragments) < 2:
            raise RuntimeError(f"Finding exact_quote not found in cited spans: {quote}")

        matched: list[tuple[str, str]] = []
        for fragment in fragments:
            matches = [sid for sid in span_ids if fragment in by_id[sid]]
            if not matches:
                raise RuntimeError(
                    f"Finding quote fragment not found in cited spans: {fragment}"
                )
            matched.append((fragment, matches[0]))

        for fragment, sid in matched:
            out.append({
                "family": family,
                "severity": severity,
                "repair_scope": scope,
                "span_ids": [sid],
                "exact_quote": fragment,
                "reason": reason,
                "normalization_note": "Split from a model-supplied multi-span ellipsis quote.",
            })

    return out
