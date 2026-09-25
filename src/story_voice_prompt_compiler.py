from __future__ import annotations

import json
from pathlib import Path

PROFILE_PATHS = {
    ("tr", 4): Path("configs/story_voice_profiles/tr_age4.v1.json"),
}


def load_voice_profile(*, language: str, exact_age: int) -> dict:
    path = PROFILE_PATHS.get((language, exact_age))
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_positive_voice_prompt(*, language: str, exact_age: int, max_rules: int = 8) -> str:
    profile = load_voice_profile(language=language, exact_age=exact_age)
    rules = (profile.get("positive_constraints") or [])[:max_rules]
    if not rules:
        return ""
    lines = [
        f"POSITIVE EXACT-AGE VOICE — age {exact_age}",
        "Write toward these behaviors naturally; do not mention or mechanically demonstrate the rules:",
    ]
    lines.extend(f"- [{r['id']}] {r['text']}" for r in rules)
    return "\n".join(lines)


NATURAL_AUTHOR_PATHS = {
    "tr": Path("configs/story_voice_profiles/natural_author_tr.v1.json"),
}


def render_natural_author_prompt(*, language: str, max_rules: int = 8) -> str:
    path = NATURAL_AUTHOR_PATHS.get(language)
    if path is None:
        return ""
    profile = json.loads(path.read_text(encoding="utf-8"))
    rules = (profile.get("constraints") or [])[:max_rules]
    if not rules:
        return ""
    lines = [
        "NATURAL AUTHOR VOICE",
        "Apply these as editorial instincts, not as a visible checklist and never mention them:",
    ]
    lines.extend(f"- [{r['id']}] {r['text']}" for r in rules)
    return "\n".join(lines)
