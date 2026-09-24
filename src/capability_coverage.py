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
    }
    return identity, candidates, summary


def select_coverage_batch(
    candidates: list[CoverageCandidate],
    *,
    age_tier_order: list[str],
    batch_size: int,
) -> list[CoverageCandidate]:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    eligible = [
        candidate
        for candidate in candidates
        if candidate.current_status != "ESTABLISHED"
    ]
    selected: list[CoverageCandidate] = []
    selected_ids: set[str] = set()

    # First pass: protect age coverage. At most one case per age tier.
    for age_tier in age_tier_order:
        if len(selected) >= batch_size:
            break
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

    return selected


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
    selected = select_coverage_batch(
        candidates,
        age_tier_order=list(capability["narrative_age_tiers"].keys()),
        batch_size=batch_size,
    )
    candidate_payload = [asdict(candidate) for candidate in candidates]
    selected_payload = [asdict(candidate) for candidate in selected]
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
            "production_frequency_weighting": "DISABLED_NO_TELEMETRY",
            "batch_size": batch_size,
        },
        "identity": asdict(identity),
        "summary": summary,
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
        "| Case | Age tier | Family | Target | Current | Family age coverage | Historical repairs/run | Historical attempts/run |",
        "|---|---|---|---:|---|---:|---:|---:|",
    ]
    for item in plan["selected"]:
        lines.append(
            f"| {item['case_id']} | {item['age_tier']} | "
            f"{item['narrative_family']} | {item['target_words']} | "
            f"{item['current_status']} ({item['current_run_count']}) | "
            f"{item['family_observed_age_count']}/{summary['executable_age_tier_count']} | "
            f"{item['historical_semantic_repairs_per_run']:.2f} | "
            f"{item['historical_scene_attempts_per_run']:.2f} |"
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
