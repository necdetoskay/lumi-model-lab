from __future__ import annotations

import re
from typing import Any

from src.openrouter_jev import noul_probability, noul_question


DEFECT_FAMILIES: dict[str, dict[str, str]] = {
    "physical_feasibility": {
        "label": "physical feasibility",
        "true": "At least one material action, object interaction, bodily action, reach, force, motion, or physical affordance is impossible or unsupported by the established story conditions.",
        "false": "The story's physical actions and affordances are possible under the conditions it establishes.",
    },
    "causal_logic": {
        "label": "causal logic",
        "true": "At least one important effect, inference, solution, or outcome does not follow from the causes, rules, or evidence established by the story.",
        "false": "Important effects, inferences, solutions, and outcomes follow from established causes, rules, and evidence.",
    },
    "state_continuity": {
        "label": "state continuity",
        "true": "An object, completed action, relationship state, or other committed state later resets, moves, reappears, disappears, or contradicts itself without an explained transition.",
        "false": "Committed object and action states remain consistent or change only through explained transitions.",
    },
    "epistemic_order": {
        "label": "epistemic order",
        "true": "A character uses, states, or acts on information before that character could have observed, learned, inferred, or been told it.",
        "false": "Characters only use information available to them at that point in the story.",
    },
    "spatial_consistency": {
        "label": "spatial consistency",
        "true": "A character or object occupies incompatible locations or traverses space in a way not supported by the story.",
        "false": "Locations and movements are spatially consistent.",
    },
    "temporal_consistency": {
        "label": "temporal consistency",
        "true": "The ordering, duration, or timing of events is contradictory or impossible under the story's stated timeline.",
        "false": "Event order and duration are temporally consistent.",
    },
    "response_causality": {
        "label": "response causality",
        "true": "The story incorrectly turns inability or delay in responding into inability to perceive, such as claiming busy hands caused failure to hear.",
        "false": "Perception and response limitations are causally distinguished.",
    },
    "closure_integrity": {
        "label": "closure integrity",
        "true": "After the story reaches its terminal closure, it reopens the main action, adds a second payoff, or appends a new prop/action that weakens the ending.",
        "false": "The terminal closure remains terminal and no new story action is appended after it.",
    },
    "canon_integrity": {
        "label": "canon integrity",
        "true": "The prose invents, contradicts, or silently changes an authoritative durable character, relationship, world, item, or knowledge fact.",
        "false": "Authoritative durable facts are preserved.",
    },
}

SEVERITIES = {"minor", "moderate", "serious", "critical"}
REPAIR_SCOPES = {"NO_REPAIR", "LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}


def segment_story(text: str) -> list[dict[str, Any]]:
    """Create deterministic sentence IDs plus paragraph/source offsets.

    Offsets are measured against the CRLF-normalized, outer-trimmed story text.
    Existing `id` and `text` fields remain stable for current consumers.
    """
    normalized = re.sub(r"\r\n?", "\n", text or "").strip()
    if not normalized:
        return []

    segments: list[dict[str, Any]] = []
    sentence_index = 1
    paragraph_index = 1

    for paragraph_match in re.finditer(r"[^\n]+", normalized):
        raw_paragraph = paragraph_match.group(0)
        if not raw_paragraph.strip():
            continue

        leading = len(raw_paragraph) - len(raw_paragraph.lstrip())
        trailing = len(raw_paragraph) - len(raw_paragraph.rstrip())
        paragraph = raw_paragraph.strip()
        paragraph_start = paragraph_match.start() + leading
        paragraph_end = paragraph_match.end() - trailing
        paragraph_id = f"P{paragraph_index:03d}"

        sentence_start = 0
        for boundary in re.finditer(r"(?<=[.!?…])\s+", paragraph):
            raw_sentence = paragraph[sentence_start:boundary.start()]
            if raw_sentence.strip():
                left = len(raw_sentence) - len(raw_sentence.lstrip())
                right = len(raw_sentence) - len(raw_sentence.rstrip())
                text_value = raw_sentence.strip()
                char_start = paragraph_start + sentence_start + left
                char_end = paragraph_start + boundary.start() - right
                segments.append({
                    "id": f"S{sentence_index:03d}",
                    "paragraph_id": paragraph_id,
                    "paragraph_index": paragraph_index,
                    "text": text_value,
                    "char_start": char_start,
                    "char_end": char_end,
                })
                sentence_index += 1
            sentence_start = boundary.end()

        raw_sentence = paragraph[sentence_start:]
        if raw_sentence.strip():
            left = len(raw_sentence) - len(raw_sentence.lstrip())
            right = len(raw_sentence) - len(raw_sentence.rstrip())
            text_value = raw_sentence.strip()
            char_start = paragraph_start + sentence_start + left
            char_end = paragraph_end - right
            segments.append({
                "id": f"S{sentence_index:03d}",
                "paragraph_id": paragraph_id,
                "paragraph_index": paragraph_index,
                "text": text_value,
                "char_start": char_start,
                "char_end": char_end,
            })
            sentence_index += 1

        paragraph_index += 1

    return segments


def build_jev_state(
    *,
    story_id: str,
    story_text: str,
    authoritative_constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    segments = segment_story(story_text)
    return {
        "story_id": story_id,
        "segments": segments,
        "authoritative_constraints": authoritative_constraints or {},
        "instruction": (
            "Evaluate only the supplied current story. Sentence IDs are evidence locators, "
            "not narrative content. Do not reward style, length, or creativity. Focus on "
            "whether a material defect of each requested family exists."
        ),
    }


def build_jev_defect_questions(
    families: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    selected = families or list(DEFECT_FAMILIES)
    unknown = sorted(set(selected) - set(DEFECT_FAMILIES))
    if unknown:
        raise ValueError("Unknown defect families: " + ", ".join(unknown))

    questions: dict[str, dict[str, Any]] = {}
    for family in selected:
        spec = DEFECT_FAMILIES[family]
        questions[family] = noul_question(
            (
                f"Decide whether the story contains a material {spec['label']} defect. "
                "Judge defect presence only. This is a high-recall sentinel question; "
                "do not convert general writing preferences into defects."
            ),
            true_criteria=spec["true"],
            false_criteria=spec["false"],
        )
    return questions


def jev_scores_from_response(
    response: dict[str, Any],
    families: list[str] | None = None,
) -> dict[str, float]:
    answers = response.get("answers")
    if not isinstance(answers, dict):
        raise RuntimeError("JEV response missing answers.")

    selected = families or list(DEFECT_FAMILIES)
    scores: dict[str, float] = {}
    for family in selected:
        answer = answers.get(family)
        if not isinstance(answer, dict):
            raise RuntimeError(f"JEV response missing defect answer: {family}")
        scores[family] = noul_probability(answer)
    return scores


def suspected_families(
    scores: dict[str, float],
    *,
    threshold: float,
) -> list[tuple[str, float]]:
    """Threshold is explicit because v1 has no qualified production threshold yet."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be within [0,1]")
    unknown = sorted(set(scores) - set(DEFECT_FAMILIES))
    if unknown:
        raise ValueError("Unknown defect families: " + ", ".join(unknown))
    return sorted(
        [(family, float(score)) for family, score in scores.items() if float(score) >= threshold],
        key=lambda row: (-row[1], row[0]),
    )


def validate_defect_finding(finding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    family = finding.get("family")
    severity = finding.get("severity")
    repair_scope = finding.get("repair_scope")
    span_ids = finding.get("span_ids")
    reason = finding.get("reason")

    if family not in DEFECT_FAMILIES:
        errors.append("family_invalid")
    if severity not in SEVERITIES:
        errors.append("severity_invalid")
    if repair_scope not in REPAIR_SCOPES:
        errors.append("repair_scope_invalid")
    if not isinstance(span_ids, list) or not span_ids:
        errors.append("span_ids_missing")
    elif any(not isinstance(span, str) or not re.fullmatch(r"S\d{3}", span) for span in span_ids):
        errors.append("span_ids_invalid")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("reason_missing")
    return errors


def build_repair_context(
    segments: list[dict[str, Any]],
    span_ids: list[str],
    *,
    window: int = 1,
) -> list[dict[str, Any]]:
    if window < 0:
        raise ValueError("window must be >= 0")
    index_by_id = {row["id"]: index for index, row in enumerate(segments)}
    missing = [span for span in span_ids if span not in index_by_id]
    if missing:
        raise ValueError("Unknown span IDs: " + ", ".join(missing))

    selected: set[int] = set()
    for span in span_ids:
        center = index_by_id[span]
        start = max(0, center - window)
        end = min(len(segments), center + window + 1)
        selected.update(range(start, end))
    return [segments[index] for index in sorted(selected)]
