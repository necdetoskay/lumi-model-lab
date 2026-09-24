from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from src.model_registry import runtime_profile_identity
from src.schemas import StorySpec

CAPABILITY_CONFIG_PATH = Path("configs/capability_cube.yaml")
EVIDENCE_SCHEMA_VERSION = "model-qualification-evidence.v2"
DEFAULT_EVIDENCE_ROOT = Path("evidence/model_qualification")
DEFAULT_REPORT_JSON = Path("reports/model_capability_cube.json")
DEFAULT_REPORT_MD = Path("reports/model_capability_cube.md")

GENERATION_PROTOCOL_ARTIFACTS = (
    Path("prompts/story_scene_plan_en_v2.md"),
    Path("prompts/story_scene_plan_repair_en_v2.md"),
    Path("prompts/story_scene_writer_en_v2.md"),
    Path("prompts/story_scene_repair_en_v1.md"),
    Path("prompts/story_scene_word_budget_repair_en_v1.md"),
    Path("prompts/story_final_targeted_repair_en_v1.md"),
)
EVALUATION_PROTOCOL_ARTIFACTS = (
    Path("prompts/story_scene_plan_judge_en_v2.md"),
    Path("prompts/story_final_judge_en_v2.md"),
)


class QualificationAxes(BaseModel):
    age_min: int
    age_max: int
    narrative_age_tier: str
    narrative_family: str
    target_words: int
    reading_mode: str = "LEGACY_UNSPECIFIED"
    relative_length_class: str = "LEGACY_UNSPECIFIED"
    length_band: str | None = None


class SceneEvidence(BaseModel):
    scene: int
    target_words: int | None = None
    word_count: int | None = None
    attempt_count: int = 0
    semantic_repair_count: int = 0
    continuity_signal: str | None = None
    continuity_positive_probabilities: dict[str, float] = Field(default_factory=dict)
    continuity_below_threshold: dict[str, Any] = Field(default_factory=dict)
    elapsed_seconds: float | None = None
    generation_attempt_elapsed_seconds: list[float] = Field(default_factory=list)
    continuity_evaluator_elapsed_seconds: list[float] = Field(default_factory=list)


class QualificationEvidence(BaseModel):
    schema_version: str = EVIDENCE_SCHEMA_VERSION
    run_id: str
    created_at: str
    source: str
    repository: str | None = None
    git_sha: str | None = None
    workflow_run_id: str | None = None
    workflow_job_id: str | None = None
    generator_model: str
    continuity_evaluator_model: str | None = None
    semantic_judge_model: str | None = None
    generation_protocol_version: str = "legacy-unversioned"
    generation_protocol_identity: dict[str, Any] = Field(default_factory=dict)
    generation_protocol_sha256: str = ""
    evaluation_protocol_version: str
    evaluation_stack_identity: dict[str, Any]
    evaluation_stack_sha256: str
    runtime_profile_identity: dict[str, Any]
    spec_path: str
    spec_sha256: str
    axes: QualificationAxes
    accepted: bool
    word_count: int
    deterministic_errors: list[str] = Field(default_factory=list)
    repeat_8gram_ratio: float | None = None
    final_judge_average: float | None = None
    final_judge_minimum: int | None = None
    final_judge_scores: dict[str, int] = Field(default_factory=dict)
    final_judge_critical_failures: list[Any] = Field(default_factory=list)
    final_judge_repair_targets: list[Any] = Field(default_factory=list)
    whole_story_continuity: dict[str, Any] = Field(default_factory=dict)
    terminal_error: dict[str, Any] | None = None
    scenes: list[SceneEvidence] = Field(default_factory=list)
    timings: dict[str, Any] = Field(default_factory=dict)
    costs: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    artifact_sha256: dict[str, str] = Field(default_factory=dict)
    evidence_limitations: list[str] = Field(default_factory=list)


def load_capability_config(path: Path = CAPABILITY_CONFIG_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "capability-cube.v2":
        raise RuntimeError("Unsupported capability cube schema")
    return payload


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def protocol_artifact_hashes(paths: tuple[Path, ...]) -> dict[str, str]:
    return {
        str(path): file_sha256(path)
        for path in paths
        if path.exists()
    }


def build_generation_protocol_identity(
    result: dict[str, Any],
    *,
    protocol_artifact_sha256: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any], str]:
    version = str(
        result.get("generation_protocol_version")
        or result.get("pipeline")
        or "legacy-unversioned"
    )
    identity = {
        "generation_protocol_version": version,
        "pipeline": result.get("pipeline"),
        "protocol_artifact_sha256": (
            dict(protocol_artifact_sha256)
            if protocol_artifact_sha256 is not None
            else protocol_artifact_hashes(GENERATION_PROTOCOL_ARTIFACTS)
        ),
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return version, identity, sha256_bytes(encoded)


def build_evaluation_stack_identity(
    *,
    continuity_evaluator_model: str | None,
    semantic_judge_model: str | None,
    evaluation_protocol_version: str,
    profile_registry_path: Path | None = None,
    protocol_artifact_sha256: dict[str, str] | None = None,
) -> tuple[dict[str, Any], str]:
    def identity_for(model_id: str | None) -> dict[str, Any] | None:
        if not model_id:
            return None
        if profile_registry_path is None:
            return runtime_profile_identity(model_id)
        return runtime_profile_identity(model_id, profile_registry_path)

    identity = {
        "evaluation_protocol_version": evaluation_protocol_version,
        "continuity_evaluator": identity_for(continuity_evaluator_model),
        "semantic_judge": identity_for(semantic_judge_model),
        "protocol_artifact_sha256": (
            dict(protocol_artifact_sha256)
            if protocol_artifact_sha256 is not None
            else protocol_artifact_hashes(EVALUATION_PROTOCOL_ARTIFACTS)
        ),
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return identity, sha256_bytes(encoded)


def narrative_age_tier_for_range(
    age_min: int,
    age_max: int,
    *,
    config: dict[str, Any] | None = None,
) -> str:
    if age_min > age_max:
        raise ValueError("age_min must be <= age_max")
    config = config or load_capability_config()
    matches = []
    for tier, bounds in config["narrative_age_tiers"].items():
        if age_min >= int(bounds["min_age"]) and age_max <= int(bounds["max_age"]):
            matches.append(tier)
    if len(matches) != 1:
        raise ValueError(
            f"Qualification age range {age_min}-{age_max} must fit exactly one NarrativeAgeTier"
        )
    return matches[0]


def default_reading_mode_for_age_tier(
    age_tier: str,
    *,
    config: dict[str, Any] | None = None,
) -> str:
    config = config or load_capability_config()
    try:
        mode = str(config["age_length_policy"][age_tier]["default_reading_mode"])
    except KeyError as exc:
        raise ValueError(f"No age-length policy for age tier {age_tier}") from exc
    if mode not in config["reading_modes"]:
        raise ValueError(f"Unknown reading mode in policy: {mode}")
    return mode


def standard_length_policy_for_age_tier(
    age_tier: str,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, int]:
    config = config or load_capability_config()
    try:
        policy = config["age_length_policy"][age_tier]["STANDARD"]
    except KeyError as exc:
        raise ValueError(f"No STANDARD length policy for age tier {age_tier}") from exc
    return {
        "target_words": int(policy["target_words"]),
        "min_words": int(policy["min_words"]),
        "max_words": int(policy["max_words"]),
    }


def resolve_relative_length_class(
    *,
    age_min: int,
    age_max: int,
    target_words: int,
    reading_mode: str | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[str, str]:
    config = config or load_capability_config()
    age_tier = narrative_age_tier_for_range(age_min, age_max, config=config)
    canonical_mode = default_reading_mode_for_age_tier(age_tier, config=config)
    resolved_mode = reading_mode or canonical_mode
    if resolved_mode not in config["reading_modes"]:
        raise ValueError(f"Unknown reading_mode: {resolved_mode}")
    if resolved_mode != canonical_mode:
        raise ValueError(
            "Alternative reading modes are not qualified in capability-cube.v2 yet: "
            f"{age_tier} expects {canonical_mode}, got {resolved_mode}"
        )

    for relative_class in config["relative_length_classes"]:
        bounds = config["age_length_policy"][age_tier][relative_class]
        if int(bounds["min_words"]) <= target_words <= int(bounds["max_words"]):
            return resolved_mode, str(relative_class)
    raise ValueError(
        "target_words is outside every qualified relative length class for "
        f"{age_tier}/{resolved_mode}: {target_words}"
    )


def standard_target_words_for_age_tier(
    age_tier: str,
    *,
    config: dict[str, Any] | None = None,
) -> int:
    return standard_length_policy_for_age_tier(
        age_tier, config=config
    )["target_words"]


def _scene_evidence(result: dict[str, Any]) -> list[SceneEvidence]:
    rows: list[SceneEvidence] = []
    if isinstance(result.get("scenes"), list):
        for scene in result["scenes"]:
            jev = scene.get("jev") or {}
            rows.append(
                SceneEvidence(
                    scene=int(scene["scene"]),
                    target_words=scene.get("target_words"),
                    word_count=scene.get("word_count"),
                    attempt_count=len(scene.get("attempts") or []),
                    semantic_repair_count=len(scene.get("semantic_repairs") or []),
                    continuity_signal=jev.get("shadow_signal"),
                    continuity_positive_probabilities={
                        str(key): float(value)
                        for key, value in (jev.get("positive_probabilities") or {}).items()
                        if isinstance(value, (int, float))
                    },
                    continuity_below_threshold=jev.get("below_threshold") or {},
                    elapsed_seconds=scene.get("elapsed_seconds"),
                    generation_attempt_elapsed_seconds=[
                        float(attempt["elapsed_seconds"])
                        for attempt in (scene.get("attempts") or [])
                        if isinstance(attempt.get("elapsed_seconds"), (int, float))
                    ],
                    continuity_evaluator_elapsed_seconds=[
                        float(value)
                        for value in (
                            scene.get("continuity_evaluator_elapsed_seconds") or []
                        )
                        if isinstance(value, (int, float))
                    ],
                )
            )
        return rows

    for scene in result.get("scene_words") or []:
        rows.append(
            SceneEvidence(
                scene=int(scene["scene"]),
                target_words=scene.get("target"),
                word_count=scene.get("actual"),
                attempt_count=int(scene.get("attempt_count") or 1),
                semantic_repair_count=int(scene.get("semantic_repairs") or 0),
                continuity_signal=scene.get("jev_signal"),
                continuity_below_threshold=scene.get("jev_below") or {},
                elapsed_seconds=scene.get("elapsed_seconds"),
            )
        )
    return rows


def assert_spec_is_qualifiable(spec_path: Path) -> None:
    marker = spec_path.parent / "INVALID_FOR_QUALIFICATION.md"
    if marker.exists():
        raise ValueError(
            "StorySpec is marked invalid for canonical qualification: "
            f"{spec_path}"
        )


def build_evidence(
    *,
    result: dict[str, Any],
    spec_path: Path,
    run_id: str,
    source: str,
    repository: str | None = None,
    git_sha: str | None = None,
    workflow_run_id: str | None = None,
    workflow_job_id: str | None = None,
    limitations: list[str] | None = None,
) -> QualificationEvidence:
    assert_spec_is_qualifiable(spec_path)
    spec = StorySpec.model_validate(yaml.safe_load(spec_path.read_text(encoding="utf-8")))
    if not spec.narrative_family:
        raise ValueError("Qualification StorySpec requires narrative_family")
    config = load_capability_config()
    if spec.narrative_family not in config["narrative_families"]:
        raise ValueError(f"Unknown narrative_family: {spec.narrative_family}")

    models = result.get("models") or {}
    generator_model = models.get("generator") or result.get("generator_model")
    if not generator_model:
        raise ValueError("Evidence requires generator model")

    judge = result.get("final_judge") or {}
    identity = runtime_profile_identity(generator_model)
    continuity_evaluator_model = (
        models.get("continuity_evaluator") or models.get("jev")
    )
    semantic_judge_model = models.get("semantic_judge") or models.get("judge")
    evaluation_protocol_version = str(
        result.get("evaluation_protocol_version") or "legacy-unversioned"
    )
    evaluation_stack_identity, evaluation_stack_sha256 = (
        build_evaluation_stack_identity(
            continuity_evaluator_model=continuity_evaluator_model,
            semantic_judge_model=semantic_judge_model,
            evaluation_protocol_version=evaluation_protocol_version,
        )
    )
    (
        generation_protocol_version,
        generation_protocol_identity,
        generation_protocol_sha256,
    ) = build_generation_protocol_identity(result)
    age_tier = narrative_age_tier_for_range(
        spec.age_min, spec.age_max, config=config
    )
    reading_mode, relative_length_class = resolve_relative_length_class(
        age_min=spec.age_min,
        age_max=spec.age_max,
        target_words=spec.target_words,
        reading_mode=spec.reading_mode,
        config=config,
    )
    if spec.relative_length_class and spec.relative_length_class != relative_length_class:
        raise ValueError(
            "StorySpec relative_length_class does not match age-aware policy: "
            f"{spec.relative_length_class} != {relative_length_class}"
        )

    return QualificationEvidence(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        repository=repository,
        git_sha=git_sha,
        workflow_run_id=workflow_run_id,
        workflow_job_id=workflow_job_id,
        generator_model=generator_model,
        continuity_evaluator_model=continuity_evaluator_model,
        semantic_judge_model=semantic_judge_model,
        generation_protocol_version=generation_protocol_version,
        generation_protocol_identity=generation_protocol_identity,
        generation_protocol_sha256=generation_protocol_sha256,
        evaluation_protocol_version=evaluation_protocol_version,
        evaluation_stack_identity=evaluation_stack_identity,
        evaluation_stack_sha256=evaluation_stack_sha256,
        runtime_profile_identity=identity,
        spec_path=str(spec_path),
        spec_sha256=file_sha256(spec_path),
        axes=QualificationAxes(
            age_min=spec.age_min,
            age_max=spec.age_max,
            narrative_age_tier=age_tier,
            narrative_family=spec.narrative_family,
            target_words=spec.target_words,
            reading_mode=reading_mode,
            relative_length_class=relative_length_class,
        ),
        accepted=bool(result.get("accepted")),
        word_count=int(result.get("word_count") or 0),
        deterministic_errors=list(result.get("deterministic_errors") or []),
        repeat_8gram_ratio=result.get("repeat_8gram_ratio"),
        final_judge_average=judge.get("average"),
        final_judge_minimum=judge.get("minimum"),
        final_judge_scores=dict(judge.get("scores") or {}),
        final_judge_critical_failures=list(judge.get("critical_failures") or []),
        final_judge_repair_targets=list(judge.get("repair_targets") or []),
        whole_story_continuity=dict(
            result.get("whole_story_continuity")
            or result.get("whole_story_jev")
            or {}
        ),
        terminal_error=(
            dict(result["terminal_error"])
            if isinstance(result.get("terminal_error"), dict)
            else None
        ),
        scenes=_scene_evidence(result),
        timings=dict(result.get("timings") or {}),
        costs=dict(result.get("costs") or {}),
        usage=dict(result.get("usage") or {}),
        evidence_limitations=list(limitations or []),
    )


def model_slug(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "_")


def materialize_evidence(
    *,
    evidence: QualificationEvidence,
    raw_result: dict[str, Any],
    spec_path: Path,
    story_text: str | None,
    output_root: Path = DEFAULT_EVIDENCE_ROOT,
) -> Path:
    destination = output_root / model_slug(evidence.generator_model) / evidence.run_id
    if destination.exists():
        raise FileExistsError(f"Immutable evidence already exists: {destination}")
    destination.mkdir(parents=True)

    result_path = destination / "result.json"
    story_path = destination / "story.txt"
    copied_spec_path = destination / "spec.yaml"

    result_path.write_text(
        json.dumps(raw_result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if story_text is not None:
        story_path.write_text(story_text.rstrip() + "\n", encoding="utf-8")
    shutil.copyfile(spec_path, copied_spec_path)

    evidence.artifact_sha256 = {
        "result.json": file_sha256(result_path),
        "spec.yaml": file_sha256(copied_spec_path),
    }
    if story_path.exists():
        evidence.artifact_sha256["story.txt"] = file_sha256(story_path)
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(
        json.dumps(evidence.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return destination


def _coverage_status(runs: int, config: dict[str, Any]) -> str:
    coverage = config["coverage"]
    if runs <= int(coverage["thin_max_runs"]):
        return "THIN"
    if runs <= int(coverage["provisional_max_runs"]):
        return "PROVISIONAL"
    return "ESTABLISHED"


def _average_metric_dict(rows: list[dict[str, int | float]]) -> dict[str, float]:
    keys = sorted({key for row in rows for key in row})
    return {
        key: round(
            statistics.mean(
                float(row[key])
                for row in rows
                if isinstance(row.get(key), (int, float))
            ),
            4,
        )
        for key in keys
    }


def _below_threshold_counts(
    rows: list[QualificationEvidence],
) -> tuple[dict[str, int], dict[str, int]]:
    scene_counts: dict[str, int] = {}
    whole_counts: dict[str, int] = {}
    for row in rows:
        for scene in row.scenes:
            for key in scene.continuity_below_threshold:
                scene_counts[key] = scene_counts.get(key, 0) + 1
        below = row.whole_story_continuity.get("below_threshold") or {}
        if isinstance(below, dict):
            for key in below:
                whole_counts[str(key)] = whole_counts.get(str(key), 0) + 1
    return dict(sorted(scene_counts.items())), dict(sorted(whole_counts.items()))


def load_evidence_manifests(root: Path = DEFAULT_EVIDENCE_ROOT) -> list[QualificationEvidence]:
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("**/manifest.json")):
        rows.append(
            QualificationEvidence.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        )
    return rows


def verify_evidence_integrity(
    root: Path = DEFAULT_EVIDENCE_ROOT,
) -> list[str]:
    errors: list[str] = []
    for manifest_path in sorted(root.glob("**/manifest.json")):
        try:
            evidence = QualificationEvidence.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            errors.append(f"{manifest_path}: invalid_manifest:{exc}")
            continue
        if not evidence.artifact_sha256:
            errors.append(f"{manifest_path}: artifact_hashes_missing")
            continue
        for name, expected in sorted(evidence.artifact_sha256.items()):
            artifact_path = manifest_path.parent / name
            if not artifact_path.exists():
                errors.append(f"{artifact_path}: missing")
                continue
            actual = file_sha256(artifact_path)
            if actual != expected:
                errors.append(
                    f"{artifact_path}: sha256_mismatch expected={expected} actual={actual}"
                )
    return errors


def build_capability_cube(
    rows: list[QualificationEvidence],
    *,
    config: dict[str, Any] | None = None,
    model_id: str | None = None,
) -> dict[str, Any]:
    config = config or load_capability_config()
    selected = [row for row in rows if model_id is None or row.generator_model == model_id]
    groups: dict[tuple[str, ...], list[QualificationEvidence]] = {}
    for row in selected:
        identity = row.runtime_profile_identity
        key = (
            row.generator_model,
            str(identity.get("profile_sha256") or ""),
            str(identity.get("production_policy_sha256") or ""),
            row.generation_protocol_sha256,
            row.evaluation_stack_sha256,
            row.axes.narrative_age_tier,
            row.axes.reading_mode,
            row.axes.narrative_family,
            row.axes.relative_length_class,
        )
        groups.setdefault(key, []).append(row)

    cells = []
    for key, items in sorted(groups.items()):
        (
            model,
            profile_sha,
            policy_sha,
            generation_protocol_sha,
            evaluation_stack_sha,
            age_tier,
            reading_mode,
            family,
            relative_length_class,
        ) = key
        judge = [x.final_judge_average for x in items if x.final_judge_average is not None]
        judge_min = [x.final_judge_minimum for x in items if x.final_judge_minimum is not None]
        durations = [
            float(x.timings["total_pipeline_seconds"])
            for x in items
            if isinstance(x.timings.get("total_pipeline_seconds"), (int, float))
        ]
        costs = [
            float(x.costs["total_pipeline_usd"])
            for x in items
            if isinstance(x.costs.get("total_pipeline_usd"), (int, float))
        ]
        total_attempts = sum(sum(s.attempt_count for s in x.scenes) for x in items)
        total_repairs = sum(
            sum(s.semantic_repair_count for s in x.scenes) for x in items
        )
        judge_criteria_average = _average_metric_dict(
            [x.final_judge_scores for x in items]
        )
        scene_below_counts, whole_below_counts = _below_threshold_counts(items)
        scene_continuity_probability_average = _average_metric_dict(
            [
                scene.continuity_positive_probabilities
                for item in items
                for scene in item.scenes
                if scene.continuity_positive_probabilities
            ]
        )
        whole_story_continuity_probability_average = _average_metric_dict(
            [
                dict(item.whole_story_continuity.get("positive_probabilities") or {})
                for item in items
                if isinstance(
                    item.whole_story_continuity.get("positive_probabilities"),
                    dict,
                )
            ]
        )
        repeat_ratios = [
            float(x.repeat_8gram_ratio)
            for x in items
            if isinstance(x.repeat_8gram_ratio, (int, float))
        ]
        successful_word_counts = [
            x.word_count for x in items if x.word_count > 0
        ]
        word_error_ratios = [
            abs(x.word_count - x.axes.target_words) / x.axes.target_words
            for x in items
            if x.word_count > 0 and x.axes.target_words > 0
        ]
        terminal_error_counts: dict[str, int] = {}
        for item in items:
            if not item.terminal_error:
                continue
            error_type = str(item.terminal_error.get("type") or "UNKNOWN")
            terminal_error_counts[error_type] = terminal_error_counts.get(error_type, 0) + 1
        total_final_repair_targets = sum(
            len(x.final_judge_repair_targets) for x in items
        )
        total_critical_failures = sum(
            len(x.final_judge_critical_failures) for x in items
        )

        target_word_breakdown: dict[str, dict[str, Any]] = {}
        for target_words in sorted({x.axes.target_words for x in items}):
            cohort = [x for x in items if x.axes.target_words == target_words]
            cohort_judge = [
                x.final_judge_average
                for x in cohort
                if x.final_judge_average is not None
            ]
            target_word_breakdown[str(target_words)] = {
                "run_count": len(cohort),
                "pass_rate": round(
                    sum(1 for x in cohort if x.accepted) / len(cohort), 6
                ),
                "average_final_judge": (
                    round(statistics.mean(cohort_judge), 4)
                    if cohort_judge
                    else None
                ),
            }

        age_range_breakdown: dict[str, dict[str, Any]] = {}
        for age_range in sorted(
            {(x.axes.age_min, x.axes.age_max) for x in items}
        ):
            cohort = [
                x
                for x in items
                if (x.axes.age_min, x.axes.age_max) == age_range
            ]
            cohort_judge = [
                x.final_judge_average
                for x in cohort
                if x.final_judge_average is not None
            ]
            age_range_breakdown[f"{age_range[0]}-{age_range[1]}"] = {
                "run_count": len(cohort),
                "pass_rate": round(
                    sum(1 for x in cohort if x.accepted) / len(cohort), 6
                ),
                "average_final_judge": (
                    round(statistics.mean(cohort_judge), 4)
                    if cohort_judge
                    else None
                ),
            }

        cells.append(
            {
                "model_id": model,
                "profile_sha256": profile_sha,
                "production_policy_sha256": policy_sha,
                "generation_protocol_sha256": generation_protocol_sha,
                "generation_protocol_version": items[0].generation_protocol_version,
                "evaluation_stack_sha256": evaluation_stack_sha,
                "continuity_evaluator_model": items[0].continuity_evaluator_model,
                "semantic_judge_model": items[0].semantic_judge_model,
                "evaluation_protocol_version": items[0].evaluation_protocol_version,
                "narrative_age_tier": age_tier,
                "reading_mode": reading_mode,
                "narrative_family": family,
                "relative_length_class": relative_length_class,
                "run_count": len(items),
                "accepted_count": sum(1 for x in items if x.accepted),
                "pass_rate": round(sum(1 for x in items if x.accepted) / len(items), 6),
                "coverage_status": _coverage_status(len(items), config),
                "target_words_observed": sorted({x.axes.target_words for x in items}),
                "target_word_breakdown": target_word_breakdown,
                "age_ranges_observed": sorted(
                    {f"{x.axes.age_min}-{x.axes.age_max}" for x in items}
                ),
                "age_range_breakdown": age_range_breakdown,
                "average_word_count": (
                    round(statistics.mean(successful_word_counts), 3)
                    if successful_word_counts
                    else None
                ),
                "average_final_judge": (
                    round(statistics.mean(judge), 4) if judge else None
                ),
                "minimum_final_criterion": min(judge_min) if judge_min else None,
                "total_scene_attempts": total_attempts,
                "semantic_repair_count": total_repairs,
                "semantic_repairs_per_run": round(total_repairs / len(items), 4),
                "average_scene_attempts_per_run": round(
                    total_attempts / len(items), 4
                ),
                "final_judge_repair_target_count": total_final_repair_targets,
                "critical_failure_count": total_critical_failures,
                "terminal_failure_count": len(items) - sum(1 for x in items if x.accepted),
                "terminal_error_counts": dict(sorted(terminal_error_counts.items())),
                "judge_criteria_average": judge_criteria_average,
                "scene_continuity_probability_average": (
                    scene_continuity_probability_average
                ),
                "whole_story_continuity_probability_average": (
                    whole_story_continuity_probability_average
                ),
                "scene_continuity_below_threshold_counts": scene_below_counts,
                "whole_story_continuity_below_threshold_counts": whole_below_counts,
                "average_repeat_8gram_ratio": (
                    round(statistics.mean(repeat_ratios), 6)
                    if repeat_ratios
                    else None
                ),
                "average_absolute_word_error_ratio": (
                    round(statistics.mean(word_error_ratios), 6)
                    if word_error_ratios
                    else None
                ),
                "average_pipeline_seconds": (
                    round(statistics.mean(durations), 3) if durations else None
                ),
                "average_pipeline_usd": (
                    round(statistics.mean(costs), 9) if costs else None
                ),
                "run_ids": [x.run_id for x in items],
            }
        )

    known_models = sorted({x.generator_model for x in selected})
    known_measurement_variants = {
        (
            x.generator_model,
            str(x.runtime_profile_identity.get("profile_sha256") or ""),
            str(x.runtime_profile_identity.get("production_policy_sha256") or ""),
            x.generation_protocol_sha256,
            x.evaluation_stack_sha256,
        )
        for x in selected
    }
    total_possible = (
        len(known_measurement_variants)
        * len(config["narrative_age_tiers"])
        * len(config["narrative_families"])
        * len(config["relative_length_classes"])
    )
    return {
        "schema_version": "model-capability-cube.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dimensions": {
            "models": known_models,
            "narrative_age_tiers": list(config["narrative_age_tiers"].keys()),
            "reading_modes": list(config["reading_modes"]),
            "narrative_families": list(config["narrative_families"]),
            "relative_length_classes": list(config["relative_length_classes"]),
        },
        "observed_cell_count": len(cells),
        "possible_cell_count_for_observed_models": total_possible,
        "unknown_cell_count": max(total_possible - len(cells), 0),
        "cells": cells,
    }


def render_cube_markdown(cube: dict[str, Any]) -> str:
    lines = [
        "# Model Capability Cube",
        "",
        f"Schema: `{cube['schema_version']}`",
        "",
        f"Observed cells: **{cube['observed_cell_count']}** / "
        f"**{cube['possible_cell_count_for_observed_models']}** "
        f"(unknown: **{cube['unknown_cell_count']}**)",
        "",
        "| Model | Protocol | Age tier | Reading mode | Narrative family | Relative length | Runs | Pass | Judge avg | Min | Repairs/run | Avg sec | Avg USD | Coverage |",
        "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for cell in cube["cells"]:
        sec = "—" if cell["average_pipeline_seconds"] is None else f"{cell['average_pipeline_seconds']:.1f}"
        usd = "—" if cell["average_pipeline_usd"] is None else f"{cell['average_pipeline_usd']:.5f}"
        judge = "—" if cell["average_final_judge"] is None else f"{cell['average_final_judge']:.3f}"
        minimum = "—" if cell["minimum_final_criterion"] is None else str(cell["minimum_final_criterion"])
        lines.append(
            f"| {cell['model_id']} | {cell['generation_protocol_version']} | "
            f"{cell['narrative_age_tier']} | {cell['reading_mode']} | "
            f"{cell['narrative_family']} | "
            f"{cell['relative_length_class']} | "
            f"{cell['run_count']} | {cell['pass_rate']:.0%} | {judge} | {minimum} | "
            f"{cell['semantic_repairs_per_run']:.2f} | {sec} | {usd} | "
            f"{cell['coverage_status']} |"
        )
    lines.extend(
        [
            "",
            "> Missing cells are **UNKNOWN**, not failures and not successes. "
            "They require qualification evidence before routing decisions.",
            "",
        ]
    )
    return "\n".join(lines)


def write_cube_reports(
    *,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
    json_out: Path = DEFAULT_REPORT_JSON,
    md_out: Path = DEFAULT_REPORT_MD,
    model_id: str | None = None,
) -> dict[str, Any]:
    cube = build_capability_cube(
        load_evidence_manifests(evidence_root),
        model_id=model_id,
    )
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(cube, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_cube_markdown(cube), encoding="utf-8")
    return cube


def _story_text_from_result(result: dict[str, Any]) -> str | None:
    title = str(result.get("story_title") or "").strip()
    story = str(result.get("story") or "").strip()
    if not story:
        return None
    return f"{title}\n\n{story}".strip() if title else story


def main() -> None:
    parser = argparse.ArgumentParser(description="LUMI model qualification evidence + capability cube")
    sub = parser.add_subparsers(dest="command", required=True)

    pack = sub.add_parser("pack")
    pack.add_argument("--result", required=True)
    pack.add_argument("--spec", required=True)
    pack.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID"))
    pack.add_argument("--source", default="github_actions" if os.getenv("GITHUB_ACTIONS") else "local")
    pack.add_argument("--output-root", default=str(DEFAULT_EVIDENCE_ROOT))
    pack.add_argument("--workflow-job-id", default=os.getenv("GITHUB_JOB"))

    build = sub.add_parser("build")
    build.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
    build.add_argument("--json-out", default=str(DEFAULT_REPORT_JSON))
    build.add_argument("--md-out", default=str(DEFAULT_REPORT_MD))
    build.add_argument("--model")

    verify = sub.add_parser("verify")
    verify.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))

    args = parser.parse_args()
    if args.command == "pack":
        if not args.run_id:
            raise SystemExit("--run-id is required outside GitHub Actions")
        result_path = Path(args.result)
        spec_path = Path(args.spec)
        result = json.loads(result_path.read_text(encoding="utf-8"))
        evidence = build_evidence(
            result=result,
            spec_path=spec_path,
            run_id=str(args.run_id),
            source=args.source,
            repository=os.getenv("GITHUB_REPOSITORY"),
            git_sha=os.getenv("GITHUB_SHA"),
            workflow_run_id=os.getenv("GITHUB_RUN_ID"),
            workflow_job_id=args.workflow_job_id,
        )
        destination = materialize_evidence(
            evidence=evidence,
            raw_result=result,
            spec_path=spec_path,
            story_text=_story_text_from_result(result),
            output_root=Path(args.output_root),
        )
        print(destination)
        return

    if args.command == "verify":
        errors = verify_evidence_integrity(Path(args.evidence_root))
        if errors:
            for error in errors:
                print(error)
            raise SystemExit(2)
        print("qualification evidence integrity: PASS")
        return

    write_cube_reports(
        evidence_root=Path(args.evidence_root),
        json_out=Path(args.json_out),
        md_out=Path(args.md_out),
        model_id=args.model,
    )


if __name__ == "__main__":
    main()
