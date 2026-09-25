from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("configs/story_failure_patterns.v1.json")

RULE_TEXT: dict[str, str] = {
    "FP-TR-001": "Do not narrate a young child's response with formal, bureaucratic, analytical, or adult cognitive vocabulary; show observable action, speech, or expression instead.",
    "FP-TR-002": "Avoid conspicuously literary or formal Turkish words that would sound unnatural when read aloud to the exact target age.",
    "FP-AGE-001": "Do not make a young child verbalize multi-step chronological or analytical reasoning with adult precision.",
    "FP-DIALOGUE-001": "Do not turn the caregiver into a teacher, answer-key, evaluator, or constant corrector; let the adult participate naturally in the relationship and play.",
    "FP-DIDACTIC-001": "Do not pause the story for textbook-like causal explanations, science lessons, or educational summaries; let information emerge through event, image, play, or brief age-natural dialogue.",
    "FP-PROSE-001": "Do not reuse the same sentence skeleton for multiple observations in the same story.",
    "FP-PROSE-002": "Do not add defensive clauses solely to prove safety, continuity, or non-contradiction.",
    "FP-PHYS-001": "Every concrete action must be physically visualizable and natural for a human body to perform.",
    "FP-NARRATOR-001": "Prefer visible action and image over philosophical or interpretive narrator commentary about what a scene means.",
    "FP-ENDING-001": "Do not close with generic smiling, lesson-learned, everything-is-fine, or 'we will come again' formulas; end on a story-specific beat.",
    "FP-CHAR-001": "Do not make the protagonist ask exactly the question needed only so another character can deliver exposition; questions and actions must arise from personality and the live scene.",
    "FP-CANON-001": "Never invent a named or relationship-bearing persistent character when the StoryContract/ContextPack does not supply or explicitly authorize that identity.",
    "FP-TR-003": "Do not preserve source syntax or imagery when it creates unnatural Turkish or a physically nonsensical action.",
    "FP-AGE-002": "For age 4, keep metaphor concrete, playful, immediately graspable, and one layer deep.",
    "FP-SAFETY-001": "Show safe behavior naturally in action; do not insert safety-policy lectures into the prose.",
    "FP-LENGTH-001": "Stay inside the supplied hard word interval; do not end early merely because the narrative can technically close.",
    "FP-STRUCT-001": "For long-form stories, do not resolve the central arc before the contracted progression has been earned.",
    "FP-STRUCT-002": "Do not pad length by restating observations, dialogue, or scene beats; each unit must change state, reveal, deepen character, or advance an active thread.",
    "FP-METAPHOR-001": "For very young children, do not give places or objects abstract adult qualities such as perseverance, resignation, or moral resilience; keep personification concrete and playful.",
    "FP-METAPHOR-002": "Do not reuse the same metaphor family repeatedly in one short story; one playful image is stronger than a chain of related explanatory metaphors.",
    "FP-ADULT-001": "Do not make the caregiver merely functional or endlessly approving; let the adult sometimes wonder, mishear, joke, notice, or join the child's play without supplying the answer.",
}

PRIORITY = {
    "BLOCKER": 0,
    "BLOCKER_IF_NONSENSE": 0,
    "SERIOUS": 1,
    "SERIOUS_IF_RECURRENT": 1,
    "SERIOUS_OR_BLOCKER": 1,
    "MODERATE_OR_SERIOUS": 2,
    "MODERATE": 2,
    "MINOR": 3,
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _applies(pattern: dict[str, Any], *, language: str, exact_age: int, story_type: str | None, long_form: bool) -> bool:
    scope = pattern.get("scope") or {}
    if scope.get("global") is True:
        return True
    if scope.get("g2") is True:
        return True
    if scope.get("multilingual") is True:
        return False
    languages = scope.get("language") or []
    if languages and language not in languages:
        return False
    ages = scope.get("age") or []
    if ages:
        if "exact-age-sensitive" in ages:
            return True
        band = "early-child" if exact_age <= 6 else "child" if exact_age <= 12 else "adult"
        if band not in ages:
            return False
    lengths = scope.get("length") or []
    if lengths and ("long-form" in lengths) != long_form:
        return False
    return True


def compile_negative_constraints(
    *,
    language: str,
    exact_age: int,
    story_type: str | None = None,
    target_words: int | None = None,
    max_rules: int = 12,
) -> list[dict[str, str]]:
    registry = load_registry()
    long_form = bool(target_words and target_words >= 1200)
    selected = [
        p for p in registry.get("initial_patterns") or []
        if _applies(
            p,
            language=language,
            exact_age=exact_age,
            story_type=story_type,
            long_form=long_form,
        ) and p.get("id") in RULE_TEXT
    ]
    selected.sort(key=lambda p: (PRIORITY.get(str(p.get("default_severity")), 9), str(p.get("id"))))
    return [
        {
            "id": str(p["id"]),
            "severity": str(p.get("default_severity")),
            "constraint": RULE_TEXT[str(p["id"])],
        }
        for p in selected[:max_rules]
    ]


def render_writer_negative_prompt(**kwargs: Any) -> str:
    rules = compile_negative_constraints(**kwargs)
    if not rules:
        return ""
    lines = [
        "FAILURE-AWARE CONSTRAINTS",
        "These are recurring defects found in prior story evaluations. Avoid the behavior, but do not write as if you are following a checklist:",
    ]
    lines.extend(f"- [{r['id']}] {r['constraint']}" for r in rules)
    return "\n".join(lines)
