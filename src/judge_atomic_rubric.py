from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_VARIANTS = {
    "TR_NATIVE",
    "EN_REFERENCE",
    "CONTROLLED_EN_PROJECTION",
}
ALLOWED_OWNERS = {"decision_engine", "hybrid"}
REQUIRED_ANCHORS = {"bad", "borderline", "good"}
EXPECTED_CRITICAL_DIMENSIONS = {
    "contract_alignment",
    "world_state_consistency",
    "age_fit",
    "relationship_consistency",
    "knowledge_consistency",
}


def load_rubric(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_rubric(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    rubric_id = data.get("rubric_id")
    rubric_version = data.get("rubric_version")
    if not isinstance(rubric_id, str) or not rubric_id:
        errors.append("rubric_id must be a non-empty string")
    if not isinstance(rubric_version, str) or not rubric_version:
        errors.append("rubric_version must be a non-empty string")

    if data.get("score_range") != [0, 4]:
        errors.append("score_range must be exactly [0, 4] for v1")

    if data.get("aggregate_story_verdict") != "forbidden_in_p3":
        errors.append("aggregate story verdict must remain forbidden in P3")

    evidence_gate = data.get("evidence_gate")
    if not isinstance(evidence_gate, dict):
        errors.append("evidence_gate must be an object")
        evidence_gate = {}
    if evidence_gate.get("required_for_all_dimensions") is not True:
        errors.append("evidence gate must be required for all dimensions")
    if evidence_gate.get("question_id_pattern") != "{dimension_id}__evidence":
        errors.append("evidence gate question_id_pattern must remain {dimension_id}__evidence")
    if evidence_gate.get("type") != "choice":
        errors.append("evidence gate must use choice semantics")
    if evidence_gate.get("choices") != ["SUFFICIENT", "INSUFFICIENT_EVIDENCE"]:
        errors.append("evidence gate choices must be SUFFICIENT/INSUFFICIENT_EVIDENCE")
    if evidence_gate.get("insufficient_policy") != "ignore_score_and_abstain":
        errors.append("insufficient evidence must ignore score and abstain")
    for language in ("tr_instruction_template", "en_instruction_template"):
        text = evidence_gate.get(language)
        if not isinstance(text, str) or not text.strip():
            errors.append(f"evidence gate missing {language}")

    variants = data.get("language_variants")
    if not isinstance(variants, list):
        errors.append("language_variants must be a list")
        variants = []
    variant_ids = [item.get("id") for item in variants if isinstance(item, dict)]
    if len(variant_ids) != len(set(variant_ids)):
        errors.append("language variant IDs must be unique")
    if set(variant_ids) != REQUIRED_VARIANTS:
        errors.append(
            "language variants must be exactly TR_NATIVE, EN_REFERENCE, "
            "CONTROLLED_EN_PROJECTION"
        )

    dimensions = data.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append("dimensions must be a non-empty list")
        dimensions = []

    dimension_ids: list[str] = []
    critical_ids: set[str] = set()
    owner_counts = {"decision_engine": 0, "hybrid": 0}

    for dimension in dimensions:
        if not isinstance(dimension, dict):
            errors.append("each dimension must be an object")
            continue
        dimension_id = dimension.get("id")
        if not isinstance(dimension_id, str) or not dimension_id:
            errors.append("dimension missing id")
            continue
        dimension_ids.append(dimension_id)

        owner = dimension.get("owner_candidate")
        if owner not in ALLOWED_OWNERS:
            errors.append(f"{dimension_id}: invalid owner_candidate {owner!r}")
        else:
            owner_counts[owner] += 1

        if dimension.get("critical_capable") is True:
            critical_ids.add(dimension_id)

        question = dimension.get("question")
        if not isinstance(question, dict):
            errors.append(f"{dimension_id}: question must be an object")
        else:
            if question.get("type") != "score":
                errors.append(f"{dimension_id}: v1 atomic rubric question type must be score")
            for language in ("tr", "en"):
                text = question.get(language)
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"{dimension_id}: missing {language} question text")

        levels = dimension.get("levels")
        if not isinstance(levels, dict):
            errors.append(f"{dimension_id}: levels must be an object")
        else:
            for language in ("tr", "en"):
                values = levels.get(language)
                if not isinstance(values, list) or len(values) != 5:
                    errors.append(
                        f"{dimension_id}: {language} levels must contain exactly 5 entries"
                    )
                elif any(not isinstance(value, str) or not value.strip() for value in values):
                    errors.append(f"{dimension_id}: {language} levels must be non-empty strings")

        anchors = dimension.get("anchors")
        if not isinstance(anchors, dict):
            errors.append(f"{dimension_id}: anchors must be an object")
        else:
            if set(anchors) != REQUIRED_ANCHORS:
                errors.append(
                    f"{dimension_id}: anchors must be exactly bad/borderline/good"
                )
            for anchor_name in REQUIRED_ANCHORS:
                anchor = anchors.get(anchor_name)
                if not isinstance(anchor, str) or not anchor.strip():
                    errors.append(f"{dimension_id}: missing {anchor_name} anchor")

    if len(dimension_ids) != len(set(dimension_ids)):
        errors.append("dimension IDs must be unique")

    if critical_ids != EXPECTED_CRITICAL_DIMENSIONS:
        errors.append(
            "critical_capable dimensions drifted from the frozen v1 set"
        )

    retained = data.get("llm_retained_dimensions")
    if not isinstance(retained, list) or not retained:
        errors.append("llm_retained_dimensions must be a non-empty list")
    else:
        retained_ids = {
            item.get("id")
            for item in retained
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        required_retained = {
            "creativity",
            "literary_style_quality",
            "deep_holistic_coherence",
        }
        if not required_retained.issubset(retained_ids):
            errors.append("required strong-LLM retained dimensions are missing")

    calibration = data.get("calibration")
    if not isinstance(calibration, dict):
        errors.append("calibration must be an object")
        calibration = {}
    if calibration.get("anchor_source") != "dedicated_synthetic_descriptions":
        errors.append("anchors must come from dedicated synthetic descriptions")
    if calibration.get("final_holdout_examples_allowed_as_anchors") is not False:
        errors.append("final holdout examples must never be allowed as anchors")

    thresholds_frozen = calibration.get("thresholds_frozen") is True
    calibration_status = calibration.get("status")
    calibration_ready = (
        not errors
        and thresholds_frozen
        and calibration_status == "CALIBRATED"
    )

    return {
        "valid": not errors,
        "calibration_ready": calibration_ready,
        "rubric_id": rubric_id,
        "rubric_version": rubric_version,
        "evidence_gate_version": evidence_gate.get("version"),
        "dimension_count": len(dimensions),
        "decision_engine_dimension_count": owner_counts["decision_engine"],
        "hybrid_dimension_count": owner_counts["hybrid"],
        "critical_dimension_count": len(critical_ids),
        "language_variants": variant_ids,
        "thresholds_frozen": thresholds_frozen,
        "calibration_status": calibration_status,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Judge Atomic Rubric v1.")
    parser.add_argument(
        "--rubric",
        default="data/specifications/judge_atomic_rubric_v1.yaml",
    )
    parser.add_argument(
        "--require-calibrated",
        action="store_true",
        help="Exit non-zero unless empirical calibration is complete and thresholds are frozen.",
    )
    args = parser.parse_args()

    result = validate_rubric(load_rubric(Path(args.rubric)))
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["valid"]:
        raise SystemExit(1)
    if args.require_calibrated and not result["calibration_ready"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
