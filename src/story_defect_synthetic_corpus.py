from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.story_defect_corpus import build_mutation_source_rows
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.story_defect_mutation_matrix import load_mutation_matrix, mutation_recipes


DEFAULT_SYNTHETIC_CORPUS = Path(
    "experiments/fixtures/story_defect_corpus.tr-age4.synthetic.v1.json"
)


def load_synthetic_corpus(
    path: str | Path = DEFAULT_SYNTHETIC_CORPUS,
) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_synthetic_corpus(corpus: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if corpus.get("status") != "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION":
        errors.append("status_invalid")
    if corpus.get("qualification_evidence") is not False:
        errors.append("must_not_claim_qualification_evidence")

    cases = corpus.get("cases")
    if not isinstance(cases, list):
        return [*errors, "cases_missing"]

    sources = build_mutation_source_rows()
    matrix = load_mutation_matrix()
    recipes = mutation_recipes(matrix)
    expected_count = len(sources) * len(recipes)
    if len(cases) != expected_count:
        errors.append(f"case_count_mismatch:{len(cases)}:{expected_count}")

    expected_source_ids = {row["source_id"] for row in sources}
    expected_recipe_ids = {row["id"] for row in recipes}
    recipe_by_id = {row["id"]: row for row in recipes}
    split_by_source = {row["source_id"]: row["dataset_split"] for row in sources}

    case_ids: set[str] = set()
    recipe_counts: dict[str, Counter[str]] = defaultdict(Counter)
    source_counts: Counter[str] = Counter()

    for index, case in enumerate(cases):
        case_id = str(case.get("case_id") or "")
        if not case_id:
            errors.append(f"case_{index}_id_missing")
        elif case_id in case_ids:
            errors.append(f"case_id_duplicate:{case_id}")
        case_ids.add(case_id)

        source_id = str(case.get("source_id") or "")
        if source_id not in expected_source_ids:
            errors.append(f"case_{index}_source_not_admitted:{source_id}")
            continue

        if case.get("dataset_split") != split_by_source[source_id]:
            errors.append(f"case_{index}_split_mismatch")

        if case.get("variant") != "corrupt":
            errors.append(f"case_{index}_variant_not_corrupt")
        if case.get("synthetic_status") != "SYNTHETIC_PENDING_INDEPENDENT_VALIDATION":
            errors.append(f"case_{index}_synthetic_status_invalid")

        mutation = case.get("mutation") or {}
        recipe_id = str(mutation.get("recipe_id") or "")
        if recipe_id not in expected_recipe_ids:
            errors.append(f"case_{index}_recipe_invalid:{recipe_id}")
            continue

        recipe = recipe_by_id[recipe_id]
        gold = case.get("gold") or {}
        if gold.get("defect_present") is not True:
            errors.append(f"case_{index}_gold_not_positive")
        if gold.get("family") != recipe["family"]:
            errors.append(f"case_{index}_gold_family_mismatch")
        if gold.get("severity") != recipe["severity"]:
            errors.append(f"case_{index}_gold_severity_mismatch")
        if gold.get("repair_scope") != recipe["repair_scope"]:
            errors.append(f"case_{index}_gold_repair_scope_mismatch")
        if gold.get("validation_status") != "PENDING_INDEPENDENT_VALIDATION":
            errors.append(f"case_{index}_gold_validation_status_invalid")

        spans = gold.get("span_ids")
        story = str(case.get("text") or "")
        valid_span_ids = {row["id"] for row in segment_story(story)}
        if not isinstance(spans, list) or not spans:
            errors.append(f"case_{index}_gold_spans_missing")
        elif not set(spans).issubset(valid_span_ids):
            errors.append(f"case_{index}_gold_spans_invalid")

        injected = str(mutation.get("injected_text") or "")
        if not injected or injected not in story:
            errors.append(f"case_{index}_injected_text_missing")

        if mutation.get("intended_family") not in DEFECT_FAMILIES:
            errors.append(f"case_{index}_mutation_family_invalid")

        source_counts[source_id] += 1
        recipe_counts[source_id][recipe_id] += 1

    for source_id in sorted(expected_source_ids):
        if source_counts[source_id] != len(recipes):
            errors.append(
                f"source_recipe_count_mismatch:{source_id}:{source_counts[source_id]}"
            )
        missing = expected_recipe_ids - set(recipe_counts[source_id])
        duplicate = [
            recipe_id
            for recipe_id, count in recipe_counts[source_id].items()
            if count != 1
        ]
        for recipe_id in sorted(missing):
            errors.append(f"source_recipe_missing:{source_id}:{recipe_id}")
        for recipe_id in sorted(duplicate):
            errors.append(f"source_recipe_duplicate:{source_id}:{recipe_id}")

    return errors


def corpus_summary(corpus: dict[str, Any]) -> dict[str, Any]:
    cases = corpus.get("cases") or []
    return {
        "case_count": len(cases),
        "source_count": len({case["source_id"] for case in cases}),
        "by_defect_family": dict(
            sorted(Counter(case["gold"]["family"] for case in cases).items())
        ),
        "by_severity": dict(
            sorted(Counter(case["gold"]["severity"] for case in cases).items())
        ),
        "by_split": dict(
            sorted(Counter(case["dataset_split"] for case in cases).items())
        ),
        "pending_validation": sum(
            1
            for case in cases
            if case["gold"]["validation_status"]
            == "PENDING_INDEPENDENT_VALIDATION"
        ),
    }


def development_cases(
    corpus: dict[str, Any] | None = None,
    *,
    split: str | None = None,
) -> list[dict[str, Any]]:
    payload = corpus or load_synthetic_corpus()
    cases = list(payload.get("cases") or [])
    if split is not None:
        if split not in {"calibration", "held_out"}:
            raise ValueError("split must be calibration or held_out")
        cases = [case for case in cases if case["dataset_split"] == split]
    return cases


def qualification_cases(
    corpus: dict[str, Any] | None = None,
    *,
    split: str | None = None,
) -> list[dict[str, Any]]:
    payload = corpus or load_synthetic_corpus()
    cases = development_cases(payload, split=split)
    pending = [
        case["case_id"]
        for case in cases
        if case["gold"].get("validation_status")
        != "INDEPENDENTLY_VALIDATED"
    ]
    if pending:
        raise RuntimeError(
            "defect corpus is not qualification-ready; "
            f"{len(pending)} cases still require independent validation"
        )
    return cases


def corpus_qualification_state(
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = corpus or load_synthetic_corpus()
    cases = list(payload.get("cases") or [])
    validated = sum(
        1
        for case in cases
        if case["gold"].get("validation_status")
        == "INDEPENDENTLY_VALIDATED"
    )
    return {
        "case_count": len(cases),
        "independently_validated": validated,
        "pending_validation": len(cases) - validated,
        "qualification_ready": bool(cases) and validated == len(cases),
    }
