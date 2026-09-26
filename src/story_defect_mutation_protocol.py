from __future__ import annotations

from typing import Any

from src.story_defect_detection import DEFECT_FAMILIES, segment_story


VALID_SEVERITIES = {"minor", "moderate", "serious", "critical"}
VALID_REPAIR_SCOPES = {"NO_REPAIR", "LOCAL_REPAIR", "STRUCTURAL_REPAIR", "REPLAN"}


def apply_single_patch(source_story: str, before: str, after: str) -> str:
    if not before or before == after:
        raise ValueError("patch_before_after_invalid")
    if source_story.count(before) != 1:
        raise ValueError("patch_before_must_match_exactly_once")
    return source_story.replace(before, after, 1)


def span_ids_for_exact_text(story: str, text: str) -> list[str]:
    if text not in story:
        return []
    rows = segment_story(story)
    return [
        row["id"]
        for row in rows
        if text in row["text"] or row["text"] in text
    ]


def validate_corrupt_variant(
    *,
    source_story: str,
    recipe: dict[str, Any],
    variant: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if variant.get("recipe_id") != recipe.get("id"):
        errors.append("recipe_id_mismatch")
    if variant.get("family") != recipe.get("family"):
        errors.append("family_mismatch")
    if variant.get("severity") != recipe.get("severity"):
        errors.append("severity_mismatch")
    if variant.get("repair_scope") != recipe.get("repair_scope"):
        errors.append("repair_scope_mismatch")

    before = str(variant.get("before_text") or "")
    after = str(variant.get("after_text") or "")
    story = str(variant.get("story") or "")
    reason = str(variant.get("defect_reason") or "").strip()

    try:
        expected = apply_single_patch(source_story, before, after)
    except ValueError as exc:
        errors.append(str(exc))
        expected = None

    if expected is not None and story != expected:
        errors.append("variant_story_is_not_exact_single_patch")
    if not reason:
        errors.append("defect_reason_missing")
    if after and story and not span_ids_for_exact_text(story, after):
        errors.append("gold_patch_span_not_addressable")
    return errors


def validate_benign_variant(
    *,
    source_story: str,
    recipe: dict[str, Any],
    variant: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if variant.get("recipe_id") != recipe.get("id"):
        errors.append("recipe_id_mismatch")
    if variant.get("expected_blocking_defect") is not False:
        errors.append("benign_variant_must_declare_no_blocking_defect")

    before = str(variant.get("before_text") or "")
    after = str(variant.get("after_text") or "")
    story = str(variant.get("story") or "")
    rationale = str(variant.get("why_still_valid") or "").strip()

    try:
        expected = apply_single_patch(source_story, before, after)
    except ValueError as exc:
        errors.append(str(exc))
        expected = None
    if expected is not None and story != expected:
        errors.append("variant_story_is_not_exact_single_patch")
    if not rationale:
        errors.append("benign_validity_rationale_missing")
    return errors


def validate_author_pack(
    *,
    source_story: str,
    recipes: list[dict[str, Any]],
    payload: dict[str, Any],
    benign: bool = False,
) -> list[str]:
    variants = payload.get("variants")
    if not isinstance(variants, list):
        return ["variants_missing"]
    expected_ids = [str(recipe["id"]) for recipe in recipes]
    actual_ids = [str(row.get("recipe_id") or "") for row in variants]
    errors: list[str] = []
    if actual_ids != expected_ids:
        errors.append("variant_recipe_order_or_set_mismatch")
        return errors

    recipe_by_id = {str(recipe["id"]): recipe for recipe in recipes}
    for index, variant in enumerate(variants):
        recipe = recipe_by_id[actual_ids[index]]
        variant_errors = (
            validate_benign_variant(
                source_story=source_story,
                recipe=recipe,
                variant=variant,
            )
            if benign
            else validate_corrupt_variant(
                source_story=source_story,
                recipe=recipe,
                variant=variant,
            )
        )
        errors.extend(f"variant_{index}:{error}" for error in variant_errors)
    return errors


def validate_validator_verdict(
    *,
    recipe: dict[str, Any],
    verdict: dict[str, Any],
    benign: bool = False,
) -> list[str]:
    errors: list[str] = []
    if verdict.get("recipe_id") != recipe.get("id"):
        errors.append("validator_recipe_id_mismatch")
    if verdict.get("accept_gold") is not True:
        errors.append("validator_did_not_accept_gold")

    if benign:
        if verdict.get("blocking_defect_present") is not False:
            errors.append("benign_validator_found_blocking_defect")
        return errors

    if verdict.get("blocking_defect_present") is not True:
        errors.append("corrupt_validator_missed_blocking_defect")
    if verdict.get("confirmed_family") != recipe.get("family"):
        errors.append("validator_family_mismatch")
    severity = verdict.get("confirmed_severity")
    if severity not in {"serious", "critical"}:
        errors.append("validator_severity_not_blocking")
    second = verdict.get("second_blocking_defects")
    if not isinstance(second, list):
        errors.append("validator_second_defects_invalid")
    elif second:
        errors.append("validator_found_second_blocking_defect")
    return errors
