from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.capability_cube import (
    QualificationEvidence,
    build_evaluation_stack_identity,
    build_generation_protocol_identity,
    load_capability_config,
    load_evidence_manifests,
)
from src.english_story_pipeline import (
    EVALUATION_PROTOCOL_VERSION,
    GENERATION_PROTOCOL_VERSION,
)
from src.model_registry import runtime_profile_identity
from src.qualification_wave import WaveCase, load_wave, wave_cases

DEFAULT_EVIDENCE_ROOT = Path("evidence/model_qualification")
DEFAULT_PLAN_JSON = Path("reports/next_qualification_plan.json")
DEFAULT_PLAN_MD = Path("reports/next_qualification_plan.md")

STATUS_RANK = {
    "UNKNOWN": 3,
    "THIN": 2,
    "PROVISIONAL": 1,
    "ESTABLISHED": 0,
}
SENTINEL_MINIMUM_FINAL_CRITERION_LTE = 3
SENTINEL_SEMANTIC_REPAIRS_PER_RUN_GTE = 2
PERSISTENT_ANOMALY_RUN_COUNT_GTE = 2


@dataclass(frozen=True)
class CoverageIdentity:
    generator_model: str
    generator_profile_sha256: str
    production_policy_sha256: str
    generation_protocol_version: str
    generation_protocol_sha256: str
    continuity_evaluator_model: str
    semantic_judge_model: str
    evaluation_protocol_version: str
    evaluation_stack_sha256: str


@dataclass(frozen=True)
class CoverageCandidate:
    case_id: str
    age_tier: str
    exact_age: int
    reading_mode: str
    relative_length_class: str
    narrative_family: str
    target_words: int
    spec_path: str
    current_run_count: int
    current_accepted_count: int
    current_failure_count: int
    current_semantic_repairs: int
    current_scene_attempts: int
    current_semantic_repairs_per_run: float
    current_scene_attempts_per_run: float
    current_minimum_final_criterion: int | None
    current_distinct_spec_count: int
    current_anomalous_run_count: int
    current_anomalous_spec_count: int
    diagnostic_fixture_required: bool
    targeted_intervention_candidate: bool
    current_status: str
    family_observed_age_count: int
    historical_run_count: int
    historical_failure_count: int
    historical_semantic_repairs: int
    historical_scene_attempts: int
    historical_semantic_repairs_per_run: float
    historical_scene_attempts_per_run: float
    reasons: tuple[str, ...]


def coverage_status(run_count: int, capability: dict[str, Any]) -> str:
    if run_count <= 0:
        return "UNKNOWN"
    coverage = capability["coverage"]
    if run_count <= int(coverage["thin_max_runs"]):
        return "THIN"
    if run_count <= int(coverage["provisional_max_runs"]):
        return "PROVISIONAL"
    return "ESTABLISHED"


def current_coverage_identity(wave_path: Path) -> CoverageIdentity:
    wave = load_wave(wave_path)
    generator_model = str(wave["generator_model"])
    continuity_model = str(wave["continuity_evaluator_model"])
    judge_model = str(wave["semantic_judge_model"])

    generator_identity = runtime_profile_identity(generator_model)
    protocol_version, _, protocol_sha = build_generation_protocol_identity(
        {
            "generation_protocol_version": GENERATION_PROTOCOL_VERSION,
            "pipeline": "english_story_pipeline_v1",
        }
    )
    _, evaluation_sha = build_evaluation_stack_identity(
        continuity_evaluator_model=continuity_model,
        semantic_judge_model=judge_model,
        evaluation_protocol_version=EVALUATION_PROTOCOL_VERSION,
    )
    return CoverageIdentity(
        generator_model=generator_model,
        generator_profile_sha256=str(generator_identity["profile_sha256"]),
        production_policy_sha256=str(
            generator_identity["production_policy_sha256"]
        ),
        generation_protocol_version=protocol_version,
        generation_protocol_sha256=protocol_sha,
        continuity_evaluator_model=continuity_model,
        semantic_judge_model=judge_model,
        evaluation_protocol_version=EVALUATION_PROTOCOL_VERSION,
        evaluation_stack_sha256=evaluation_sha,
    )


def _same_case(row: QualificationEvidence, case: WaveCase) -> bool:
    axes = row.axes
    return (
        axes.age_min == case.exact_age
        and axes.age_max == case.exact_age
        and axes.narrative_age_tier == case.age_tier
        and axes.reading_mode == case.reading_mode
        and axes.relative_length_class == case.relative_length_class
        and axes.narrative_family == case.narrative_family
        and axes.target_words == case.target_words
    )


def _same_runtime_and_evaluation(
    row: QualificationEvidence,
    identity: CoverageIdentity,
) -> bool:
    runtime = row.runtime_profile_identity
    return (
        row.generator_model == identity.generator_model
        and str(runtime.get("profile_sha256") or "")
        == identity.generator_profile_sha256
        and str(runtime.get("production_policy_sha256") or "")
        == identity.production_policy_sha256
        and row.continuity_evaluator_model
        == identity.continuity_evaluator_model
        and row.semantic_judge_model == identity.semantic_judge_model
        and row.evaluation_protocol_version
        == identity.evaluation_protocol_version
        and row.evaluation_stack_sha256 == identity.evaluation_stack_sha256
    )


def _scene_attempts(row: QualificationEvidence) -> int:
    return sum(scene.attempt_count for scene in row.scenes)


def _semantic_repairs(row: QualificationEvidence) -> int:
    return sum(scene.semantic_repair_count for scene in row.scenes)


def _is_current_anomaly(row: QualificationEvidence) -> bool:
    return (
        not row.accepted
        or (
            row.final_judge_minimum is not None
            and row.final_judge_minimum <= SENTINEL_MINIMUM_FINAL_CRITERION_LTE
        )
        or _semantic_repairs(row) >= SENTINEL_SEMANTIC_REPAIRS_PER_RUN_GTE
    )


def _candidate_priority(candidate: CoverageCandidate) -> tuple[Any, ...]:
    return (
        STATUS_RANK[candidate.current_status],
        -candidate.family_observed_age_count,
        1 if candidate.historical_failure_count else 0,
        candidate.historical_semantic_repairs_per_run,
        candidate.historical_scene_attempts_per_run,
        -candidate.current_run_count,
        candidate.narrative_family,
        candidate.case_id,
    )


def _sentinel_repeat_candidate(
    candidates: list[CoverageCandidate],
) -> CoverageCandidate | None:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.current_status in {"THIN", "PROVISIONAL"}
        and not candidate.diagnostic_fixture_required
        and not candidate.targeted_intervention_candidate
        and (
            candidate.current_failure_count > 0
            or (
                candidate.current_minimum_final_criterion is not None
                and candidate.current_minimum_final_criterion
                <= SENTINEL_MINIMUM_FINAL_CRITERION_LTE
            )
            or candidate.current_semantic_repairs_per_run
            >= SENTINEL_SEMANTIC_REPAIRS_PER_RUN_GTE
        )
    ]
    if not eligible:
        return None

    def priority(candidate: CoverageCandidate) -> tuple[Any, ...]:
        low_minimum = (
            candidate.current_minimum_final_criterion is not None
            and candidate.current_minimum_final_criterion
            <= SENTINEL_MINIMUM_FINAL_CRITERION_LTE
        )
        return (
            1 if candidate.current_failure_count > 0 else 0,
            1 if low_minimum else 0,
            candidate.current_semantic_repairs_per_run,
            candidate.current_scene_attempts_per_run,
            -candidate.current_run_count,
        )

    return max(eligible, key=priority)


def build_coverage_candidates(
    wave_path: Path,
    *,
    evidence: list[QualificationEvidence] | None = None,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
) -> tuple[CoverageIdentity, list[CoverageCandidate], dict[str, Any]]:
    wave = load_wave(wave_path)
    capability = load_capability_config()
    identity = current_coverage_identity(wave_path)
    cases = wave_cases(wave_path)
    rows = evidence if evidence is not None else load_evidence_manifests(evidence_root)

    comparable = [
        row
        for row in rows
        if _same_runtime_and_evaluation(row, identity)
    ]
    current_rows = [
        row
        for row in comparable
        if row.generation_protocol_sha256
        == identity.generation_protocol_sha256
    ]

    family_observed_ages: dict[str, set[str]] = {
        family: set() for family in wave["families"]
    }
    for case in cases:
        if any(_same_case(row, case) for row in current_rows):
            family_observed_ages[case.narrative_family].add(case.age_tier)

    candidates: list[CoverageCandidate] = []
    for case in cases:
        current = [row for row in current_rows if _same_case(row, case)]
        historical = [
            row
            for row in comparable
            if row.generation_protocol_sha256
            != identity.generation_protocol_sha256
            and _same_case(row, case)
        ]
        run_count = len(current)
        accepted_count = sum(1 for row in current if row.accepted)
        current_failures = run_count - accepted_count
        current_repairs = sum(_semantic_repairs(row) for row in current)
        current_attempts = sum(_scene_attempts(row) for row in current)
        current_repair_rate = (
            round(current_repairs / run_count, 4)
            if run_count
            else 0.0
        )
        current_attempt_rate = (
            round(current_attempts / run_count, 4)
            if run_count
            else 0.0
        )
        current_minimums = [
            row.final_judge_minimum
            for row in current
            if row.final_judge_minimum is not None
        ]
        current_minimum = min(current_minimums) if current_minimums else None
        current_distinct_specs = len({row.spec_sha256 for row in current})
        anomalous_rows = [row for row in current if _is_current_anomaly(row)]
        current_anomalous_run_count = len(anomalous_rows)
        current_anomalous_spec_count = len(
            {row.spec_sha256 for row in anomalous_rows}
        )
        diagnostic_fixture_required = (
            current_anomalous_run_count >= PERSISTENT_ANOMALY_RUN_COUNT_GTE
            and current_distinct_specs < 2
        )
        targeted_intervention_candidate = current_anomalous_spec_count >= 2
        history_runs = len(historical)
        history_failures = sum(1 for row in historical if not row.accepted)
        history_repairs = sum(_semantic_repairs(row) for row in historical)
        history_attempts = sum(_scene_attempts(row) for row in historical)
        repair_rate = (
            round(history_repairs / history_runs, 4)
            if history_runs
            else 0.0
        )
        attempt_rate = (
            round(history_attempts / history_runs, 4)
            if history_runs
            else 0.0
        )
        status = coverage_status(run_count, capability)
        observed_age_count = len(
            family_observed_ages.get(case.narrative_family, set())
        )
        reasons = [
            f"CURRENT_STATUS:{status}",
            (
                "FAMILY_ACTIVE_PROTOCOL_COVERAGE:"
                f"{observed_age_count}/{len(wave['age_cases'])}"
            ),
        ]
        if run_count:
            reasons.append(f"CURRENT_FAILURES:{current_failures}")
            reasons.append(
                f"CURRENT_SEMANTIC_REPAIRS_PER_RUN:{current_repair_rate:.4f}"
            )
            reasons.append(
                f"CURRENT_SCENE_ATTEMPTS_PER_RUN:{current_attempt_rate:.4f}"
            )
            reasons.append(
                f"CURRENT_DISTINCT_SPEC_COUNT:{current_distinct_specs}"
            )
            reasons.append(
                f"CURRENT_ANOMALOUS_RUN_COUNT:{current_anomalous_run_count}"
            )
            reasons.append(
                f"CURRENT_ANOMALOUS_SPEC_COUNT:{current_anomalous_spec_count}"
            )
            if current_minimum is not None:
                reasons.append(
                    f"CURRENT_MINIMUM_FINAL_CRITERION:{current_minimum}"
                )
            if diagnostic_fixture_required:
                reasons.append("DIAGNOSTIC_FIXTURE_REQUIRED")
            if targeted_intervention_candidate:
                reasons.append("TARGETED_INTERVENTION_CANDIDATE")
        if history_runs:
            reasons.append(f"HISTORICAL_RUNS:{history_runs}")
            reasons.append(
                f"HISTORICAL_SEMANTIC_REPAIRS_PER_RUN:{repair_rate:.4f}"
            )
            reasons.append(
                f"HISTORICAL_SCENE_ATTEMPTS_PER_RUN:{attempt_rate:.4f}"
            )
        if history_failures:
            reasons.append(f"HISTORICAL_FAILURES:{history_failures}")

        candidates.append(
            CoverageCandidate(
                case_id=case.case_id,
                age_tier=case.age_tier,
                exact_age=case.exact_age,
                reading_mode=case.reading_mode,
                relative_length_class=case.relative_length_class,
                narrative_family=case.narrative_family,
                target_words=case.target_words,
                spec_path=str(case.spec_path),
                current_run_count=run_count,
                current_accepted_count=accepted_count,
                current_failure_count=current_failures,
                current_semantic_repairs=current_repairs,
                current_scene_attempts=current_attempts,
                current_semantic_repairs_per_run=current_repair_rate,
                current_scene_attempts_per_run=current_attempt_rate,
                current_minimum_final_criterion=current_minimum,
                current_distinct_spec_count=current_distinct_specs,
                current_anomalous_run_count=current_anomalous_run_count,
                current_anomalous_spec_count=current_anomalous_spec_count,
                diagnostic_fixture_required=diagnostic_fixture_required,
                targeted_intervention_candidate=targeted_intervention_candidate,
                current_status=status,
                family_observed_age_count=observed_age_count,
                historical_run_count=history_runs,
                historical_failure_count=history_failures,
                historical_semantic_repairs=history_repairs,
                historical_scene_attempts=history_attempts,
                historical_semantic_repairs_per_run=repair_rate,
                historical_scene_attempts_per_run=attempt_rate,
                reasons=tuple(reasons),
            )
        )

    canonical_case_count = (
        len(capability["narrative_age_tiers"])
        * len(capability["narrative_families"])
        * len(capability["relative_length_classes"])
    )
    summary = {
        "executable_scope_case_count": len(cases),
        "executable_age_tier_count": len(wave["age_cases"]),
        "canonical_standard_case_count": canonical_case_count,
        "canonical_out_of_scope_case_count": max(
            canonical_case_count - len(cases), 0
        ),
        "current_protocol_observed_case_count": sum(
            1 for candidate in candidates if candidate.current_run_count > 0
        ),
        "current_protocol_unknown_case_count": sum(
            1 for candidate in candidates if candidate.current_status == "UNKNOWN"
        ),
        "current_protocol_thin_case_count": sum(
            1 for candidate in candidates if candidate.current_status == "THIN"
        ),
        "current_protocol_provisional_case_count": sum(
            1
            for candidate in candidates
            if candidate.current_status == "PROVISIONAL"
        ),
        "current_protocol_established_case_count": sum(
            1
            for candidate in candidates
            if candidate.current_status == "ESTABLISHED"
        ),
        "diagnostic_fixture_required_count": sum(
            1 for candidate in candidates if candidate.diagnostic_fixture_required
        ),
        "targeted_intervention_candidate_count": sum(
            1
            for candidate in candidates
            if candidate.targeted_intervention_candidate
        ),
    }
    return identity, candidates, summary


def select_coverage_batch(
    candidates: list[CoverageCandidate],
    *,
    age_tier_order: list[str],
    batch_size: int,
) -> tuple[list[CoverageCandidate], str | None]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    eligible = [
        candidate
        for candidate in candidates
        if candidate.current_status != "ESTABLISHED"
        and not candidate.diagnostic_fixture_required
        and not candidate.targeted_intervention_candidate
    ]
    selected: list[CoverageCandidate] = []
    selected_ids: set[str] = set()
    selected_age_tiers: set[str] = set()

    sentinel = _sentinel_repeat_candidate(eligible)
    sentinel_case_id: str | None = None
    if sentinel is not None:
        selected.append(sentinel)
        selected_ids.add(sentinel.case_id)
        selected_age_tiers.add(sentinel.age_tier)
        sentinel_case_id = sentinel.case_id

    # First pass: protect age coverage. The sentinel occupies its age-tier slot.
    for age_tier in age_tier_order:
        if len(selected) >= batch_size:
            break
        if age_tier in selected_age_tiers:
            continue
        age_candidates = [
            candidate
            for candidate in eligible
            if candidate.age_tier == age_tier
            and candidate.case_id not in selected_ids
        ]
        if not age_candidates:
            continue
        choice = max(age_candidates, key=_candidate_priority)
        selected.append(choice)
        selected_ids.add(choice.case_id)
        selected_age_tiers.add(choice.age_tier)

    # Second pass: if the batch is larger than the age count, fill by priority.
    if len(selected) < batch_size:
        remaining = [
            candidate
            for candidate in eligible
            if candidate.case_id not in selected_ids
        ]
        for candidate in sorted(
            remaining,
            key=_candidate_priority,
            reverse=True,
        ):
            if len(selected) >= batch_size:
                break
            selected.append(candidate)
            selected_ids.add(candidate.case_id)

    return selected, sentinel_case_id


def build_coverage_plan(
    wave_path: Path,
    *,
    batch_size: int = 8,
    evidence: list[QualificationEvidence] | None = None,
    evidence_root: Path = DEFAULT_EVIDENCE_ROOT,
) -> dict[str, Any]:
    wave = load_wave(wave_path)
    capability = load_capability_config()
    identity, candidates, summary = build_coverage_candidates(
        wave_path,
        evidence=evidence,
        evidence_root=evidence_root,
    )
    selected, sentinel_case_id = select_coverage_batch(
        candidates,
        age_tier_order=list(capability["narrative_age_tiers"].keys()),
        batch_size=batch_size,
    )
    candidate_payload = [asdict(candidate) for candidate in candidates]
    diagnostic_fixture_required_case_ids = [
        candidate.case_id
        for candidate in candidates
        if candidate.diagnostic_fixture_required
    ]
    targeted_intervention_candidate_case_ids = [
        candidate.case_id
        for candidate in candidates
        if candidate.targeted_intervention_candidate
    ]
    selected_payload = []
    for candidate in selected:
        payload = asdict(candidate)
        payload["selection_lane"] = (
            "SENTINEL_REPEAT"
            if candidate.case_id == sentinel_case_id
            else "COVERAGE_EXPANSION"
        )
        selected_payload.append(payload)
    return {
        "schema_version": "capability-coverage-plan.v1",
        "scope_wave": str(wave_path),
        "selection_policy": {
            "age_balanced_first_pass": True,
            "coverage_status_order": [
                "UNKNOWN",
                "THIN",
                "PROVISIONAL",
                "ESTABLISHED",
            ],
            "family_gap_before_historical_burden": True,
            "sentinel_repeat": {
                "max_slots_per_batch": 1,
                "eligible_statuses": ["THIN", "PROVISIONAL"],
                "terminal_failure_triggers": True,
                "minimum_final_criterion_lte": 3,
                "semantic_repairs_per_run_gte": (
                    SENTINEL_SEMANTIC_REPAIRS_PER_RUN_GTE
                ),
            },
            "fixture_diversity_guard": {
                "persistent_anomaly_run_count_gte": (
                    PERSISTENT_ANOMALY_RUN_COUNT_GTE
                ),
                "same_fixture_action": "DIAGNOSTIC_FIXTURE_REQUIRED",
                "multi_fixture_action": "TARGETED_INTERVENTION_CANDIDATE",
                "automatic_repeat_when_escalated": False,
            },
            "production_frequency_weighting": "DISABLED_NO_TELEMETRY",
            "batch_size": batch_size,
        },
        "identity": asdict(identity),
        "summary": {
            **summary,
            "sentinel_repeat_case_id": sentinel_case_id,
            "diagnostic_fixture_required_case_ids": (
                diagnostic_fixture_required_case_ids
            ),
            "targeted_intervention_candidate_case_ids": (
                targeted_intervention_candidate_case_ids
            ),
        },
        "selected": selected_payload,
        "candidates": candidate_payload,
        "max_parallel": int(wave["max_parallel"]),
    }


def matrix_payload(plan: dict[str, Any]) -> dict[str, Any]:
    identity = plan["identity"]
    return {
        "include": [
            {
                "case_id": item["case_id"],
                "age_tier": item["age_tier"],
                "exact_age": item["exact_age"],
                "reading_mode": item["reading_mode"],
                "relative_length_class": item["relative_length_class"],
                "narrative_family": item["narrative_family"],
                "target_words": item["target_words"],
                "spec_path": item["spec_path"],
                "generator_model": identity["generator_model"],
                "continuity_evaluator_model": identity[
                    "continuity_evaluator_model"
                ],
                "semantic_judge_model": identity["semantic_judge_model"],
            }
            for item in plan["selected"]
        ]
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    summary = plan["summary"]
    lines = [
        "# Next Adaptive Qualification Plan",
        "",
        f"Scope wave: `{plan['scope_wave']}`",
        f"Active generation protocol: `{plan['identity']['generation_protocol_version']}`",
        "",
        (
            "Executable scope: "
            f"**{summary['executable_scope_case_count']}** cases; "
            f"canonical STANDARD scope: **{summary['canonical_standard_case_count']}**; "
            f"fixture-backed out-of-scope: **{summary['canonical_out_of_scope_case_count']}**."
        ),
        (
            "Current protocol inside executable scope: "
            f"observed **{summary['current_protocol_observed_case_count']}**, "
            f"unknown **{summary['current_protocol_unknown_case_count']}**, "
            f"thin **{summary['current_protocol_thin_case_count']}**, "
            f"provisional **{summary['current_protocol_provisional_case_count']}**, "
            f"established **{summary['current_protocol_established_case_count']}**."
        ),
        "",
    ]
    if summary["diagnostic_fixture_required_case_ids"]:
        lines.extend(
            [
                "Diagnostic fixture required: "
                + ", ".join(summary["diagnostic_fixture_required_case_ids"]),
                "",
            ]
        )
    if summary["targeted_intervention_candidate_case_ids"]:
        lines.extend(
            [
                "Targeted intervention candidates: "
                + ", ".join(
                    summary["targeted_intervention_candidate_case_ids"]
                ),
                "",
            ]
        )
    lines.extend(
        [
            "| Lane | Case | Age tier | Family | Target | Current | Current repairs/run | Current attempts/run | Family age coverage | Historical repairs/run |",
            "|---|---|---|---|---:|---|---:|---:|---:|---:|",
        ]
    )
    for item in plan["selected"]:
        lines.append(
            f"| {item['selection_lane']} | {item['case_id']} | "
            f"{item['age_tier']} | {item['narrative_family']} | "
            f"{item['target_words']} | "
            f"{item['current_status']} ({item['current_run_count']}) | "
            f"{item['current_semantic_repairs_per_run']:.2f} | "
            f"{item['current_scene_attempts_per_run']:.2f} | "
            f"{item['family_observed_age_count']}/{summary['executable_age_tier_count']} | "
            f"{item['historical_semantic_repairs_per_run']:.2f} |"
        )
    lines.extend(
        [
            "",
            "> Production-frequency weighting is intentionally disabled until real LUMI telemetry exists. The planner does not invent popularity.",
            "",
        ]
    )
    return "\n".join(lines)


def write_plan_reports(
    plan: dict[str, Any],
    *,
    json_out: Path = DEFAULT_PLAN_JSON,
    md_out: Path = DEFAULT_PLAN_MD,
) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_plan_markdown(plan), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan age-balanced adaptive Model Lab qualification coverage."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("plan", "matrix"):
        cmd = sub.add_parser(name)
        cmd.add_argument(
            "--wave",
            default="configs/qualification_waves/age-relative-standard-v2.yaml",
        )
        cmd.add_argument("--evidence-root", default=str(DEFAULT_EVIDENCE_ROOT))
        cmd.add_argument("--batch-size", type=int, default=8)

    plan_cmd = sub.choices["plan"]
    plan_cmd.add_argument("--json-out", default=str(DEFAULT_PLAN_JSON))
    plan_cmd.add_argument("--md-out", default=str(DEFAULT_PLAN_MD))

    args = parser.parse_args()
    plan = build_coverage_plan(
        Path(args.wave),
        batch_size=args.batch_size,
        evidence_root=Path(args.evidence_root),
    )

    if args.command == "matrix":
        if not plan["selected"]:
            raise SystemExit("NO_ELIGIBLE_ADAPTIVE_COVERAGE_CASES")
        print(
            json.dumps(
                matrix_payload(plan),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        return

    write_plan_reports(
        plan,
        json_out=Path(args.json_out),
        md_out=Path(args.md_out),
    )
    print(
        json.dumps(
            {
                "selected_count": len(plan["selected"]),
                **plan["summary"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
