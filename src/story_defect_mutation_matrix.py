from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

from src.story_defect_corpus import build_mutation_source_rows


DEFAULT_MATRIX = Path(
    "experiments/fixtures/story_defect_mutation_matrix.tr-age4.v1.json"
)


def load_mutation_matrix(path: str | Path = DEFAULT_MATRIX) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def mutation_recipes(matrix: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = matrix or load_mutation_matrix()
    return [
        recipe
        for pack in payload.get("corrupt_packs") or []
        for recipe in pack.get("recipes") or []
    ]


def expected_case_count(
    *,
    source_count: int | None = None,
    matrix: dict[str, Any] | None = None,
) -> int:
    payload = matrix or load_mutation_matrix()
    if source_count is None:
        source_count = len(build_mutation_source_rows())
    per_source = payload["cases_per_source"]
    return source_count * int(per_source["total"])


def matrix_summary(matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = matrix or load_mutation_matrix()
    recipes = mutation_recipes(payload)
    benign = payload.get("benign_hard_negative_recipes") or []
    return {
        "corrupt_recipe_count": len(recipes),
        "benign_recipe_count": len(benign),
        "family_recipe_counts": dict(Counter(r["family"] for r in recipes)),
        "severity_recipe_counts": dict(Counter(r["severity"] for r in recipes)),
        "difficulty_recipe_counts": dict(Counter(r["difficulty"] for r in recipes)),
        "expected_total_cases": expected_case_count(matrix=payload),
    }


def validate_mutation_matrix(matrix: dict[str, Any] | None = None) -> list[str]:
    payload = matrix or load_mutation_matrix()
    errors: list[str] = []
    recipes = mutation_recipes(payload)
    ids = [str(r.get("id") or "") for r in recipes]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_corrupt_recipe_id")
    if len(recipes) != int(payload["cases_per_source"]["corrupt_variants"]):
        errors.append("corrupt_recipe_count_mismatch")

    benign = payload.get("benign_hard_negative_recipes") or []
    if len(benign) != int(payload["cases_per_source"]["benign_hard_negatives"]):
        errors.append("benign_recipe_count_mismatch")

    per_source_total = (
        int(payload["cases_per_source"]["original_clean"])
        + len(benign)
        + len(recipes)
    )
    if per_source_total != int(payload["cases_per_source"]["total"]):
        errors.append("per_source_total_mismatch")

    critical_focus = {"physical_feasibility", "causal_logic", "state_continuity"}
    counts = Counter(r["family"] for r in recipes)
    for family in critical_focus:
        if counts[family] < 3:
            errors.append(f"critical_focus_underrepresented:{family}")

    if not any(r["severity"] == "critical" for r in recipes):
        errors.append("critical_severity_missing")
    if expected_case_count(matrix=payload) < 200:
        errors.append("qualification_case_floor_not_met")

    return errors
