from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.capability_cube import (
    default_reading_mode_for_age_tier,
    load_capability_config,
    narrative_age_tier_for_range,
    resolve_relative_length_class,
    standard_target_words_for_age_tier,
)
from src.schemas import StorySpec

WAVE_SCHEMA_VERSION = "qualification-wave.v2"
DEFAULT_OUTPUT_ROOT = Path("data/specifications/waves")


@dataclass(frozen=True)
class WaveCase:
    case_id: str
    age_tier: str
    exact_age: int
    reading_mode: str
    relative_length_class: str
    narrative_family: str
    target_words: int
    spec_path: Path


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not value:
        raise ValueError("empty slug")
    return value


def load_wave(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != WAVE_SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported qualification wave schema: {payload.get('schema_version')!r}"
        )
    if payload.get("status") != "ACTIVE":
        raise RuntimeError(
            f"Qualification wave is not ACTIVE: {payload.get('status')!r}"
        )

    capability = load_capability_config()
    expected_tiers = list(capability["narrative_age_tiers"].keys())
    age_cases = payload.get("age_cases") or {}
    if list(age_cases.keys()) != expected_tiers:
        raise ValueError(
            "age_cases must list every canonical NarrativeAgeTier in canonical order"
        )

    families = payload.get("families") or {}
    if not families:
        raise ValueError("wave requires at least one narrative family")
    unknown = sorted(set(families) - set(capability["narrative_families"]))
    if unknown:
        raise ValueError(f"unknown narrative families: {unknown}")

    for tier, case in age_cases.items():
        exact_age = int(case["exact_age"])
        actual_tier = narrative_age_tier_for_range(exact_age, exact_age)
        if actual_tier != tier:
            raise ValueError(
                f"representative age {exact_age} maps to {actual_tier}, not {tier}"
            )

        reading_mode = str(case["reading_mode"])
        canonical_mode = default_reading_mode_for_age_tier(tier)
        if reading_mode != canonical_mode:
            raise ValueError(
                f"{tier} reading_mode must be {canonical_mode}, got {reading_mode}"
            )

        relative_class = str(case["relative_length_class"])
        if relative_class != "STANDARD":
            raise ValueError(
                "qualification-wave.v2 currently supports STANDARD only; "
                "other relative length classes are not canonical yet"
            )

        target_words = int(case["target_words"])
        canonical_target = standard_target_words_for_age_tier(tier)
        if target_words != canonical_target:
            raise ValueError(
                f"{tier} STANDARD target_words must be {canonical_target}, "
                f"got {target_words}"
            )

        resolved_mode, resolved_class = resolve_relative_length_class(
            age_min=exact_age,
            age_max=exact_age,
            target_words=target_words,
            reading_mode=reading_mode,
        )
        if resolved_mode != reading_mode or resolved_class != relative_class:
            raise ValueError(
                f"{tier} policy resolution mismatch: "
                f"{resolved_mode}/{resolved_class}"
            )

    max_parallel = int(payload.get("max_parallel") or 0)
    if max_parallel < 1 or max_parallel > 8:
        raise ValueError("max_parallel must be between 1 and 8")

    for role in (
        "generator_model",
        "continuity_evaluator_model",
        "semantic_judge_model",
    ):
        if not str(payload.get(role) or "").strip():
            raise ValueError(f"{role} is required")

    return payload


def wave_cases(
    wave_path: Path,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> list[WaveCase]:
    wave = load_wave(wave_path)
    wave_id = _slug(str(wave["wave_id"]))
    rows: list[WaveCase] = []
    for tier, age_case in wave["age_cases"].items():
        exact_age = int(age_case["exact_age"])
        reading_mode = str(age_case["reading_mode"])
        relative_class = str(age_case["relative_length_class"])
        target_words = int(age_case["target_words"])
        for family in wave["families"]:
            case_id = f"{_slug(tier)}--{_slug(family)}"
            spec_path = output_root / wave_id / f"{case_id}.yaml"
            rows.append(
                WaveCase(
                    case_id=case_id,
                    age_tier=tier,
                    exact_age=exact_age,
                    reading_mode=reading_mode,
                    relative_length_class=relative_class,
                    narrative_family=family,
                    target_words=target_words,
                    spec_path=spec_path,
                )
            )
    return rows


def _protagonist(age: int) -> str:
    return (
        f"Deniz, age {age}, whose judgment, independence, vocabulary, "
        "social context, and responsibilities must be plausible for that exact age"
    )


def materialize_wave(
    wave_path: Path,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> list[WaveCase]:
    wave = load_wave(wave_path)
    global_constraints = [str(x) for x in wave.get("global_constraints") or []]
    cases = wave_cases(wave_path, output_root=output_root)
    for case in cases:
        family = wave["families"][case.narrative_family]
        constraints = [
            *global_constraints,
            *[str(x) for x in family.get("constraints") or []],
            (
                f"The intended reader is exactly age {case.exact_age}; "
                f"reading mode is {case.reading_mode}; do not write for a "
                "younger or older audience."
            ),
        ]
        spec = StorySpec(
            title_hint=str(family.get("title_hint") or "").strip() or None,
            age_min=case.exact_age,
            age_max=case.exact_age,
            language=str(wave.get("language") or "en"),
            target_words=case.target_words,
            narrative_family=case.narrative_family,
            reading_mode=case.reading_mode,
            relative_length_class=case.relative_length_class,
            protagonist=_protagonist(case.exact_age),
            setting=str(family["setting"]),
            theme=str(family["theme"]),
            premise=str(family["premise"]),
            constraints=constraints,
        )
        case.spec_path.parent.mkdir(parents=True, exist_ok=True)
        case.spec_path.write_text(
            yaml.safe_dump(
                spec.model_dump(mode="json"),
                sort_keys=False,
                allow_unicode=True,
                width=1000,
            ),
            encoding="utf-8",
        )
    return cases


def matrix_payload(
    wave_path: Path,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    wave = load_wave(wave_path)
    cases = wave_cases(wave_path, output_root=output_root)
    return {
        "include": [
            {
                "case_id": case.case_id,
                "age_tier": case.age_tier,
                "exact_age": case.exact_age,
                "reading_mode": case.reading_mode,
                "relative_length_class": case.relative_length_class,
                "narrative_family": case.narrative_family,
                "target_words": case.target_words,
                "spec_path": str(case.spec_path),
                "generator_model": wave["generator_model"],
                "continuity_evaluator_model": wave[
                    "continuity_evaluator_model"
                ],
                "semantic_judge_model": wave["semantic_judge_model"],
            }
            for case in cases
        ]
    }


def validate_materialized_wave(
    wave_path: Path,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> list[str]:
    wave = load_wave(wave_path)
    cases = wave_cases(wave_path, output_root=output_root)
    errors: list[str] = []
    seen: set[str] = set()

    for case in cases:
        if case.case_id in seen:
            errors.append(f"duplicate_case_id:{case.case_id}")
        seen.add(case.case_id)

        if not case.spec_path.exists():
            errors.append(f"missing_spec:{case.spec_path}")
            continue

        try:
            spec = StorySpec.model_validate(
                yaml.safe_load(case.spec_path.read_text(encoding="utf-8"))
            )
        except Exception as exc:
            errors.append(f"invalid_spec:{case.spec_path}:{exc}")
            continue

        if spec.age_min != case.exact_age or spec.age_max != case.exact_age:
            errors.append(f"age_mismatch:{case.case_id}")
        if narrative_age_tier_for_range(spec.age_min, spec.age_max) != case.age_tier:
            errors.append(f"tier_mismatch:{case.case_id}")
        if spec.narrative_family != case.narrative_family:
            errors.append(f"family_mismatch:{case.case_id}")
        if spec.target_words != case.target_words:
            errors.append(f"target_words_mismatch:{case.case_id}")
        if spec.reading_mode != case.reading_mode:
            errors.append(f"reading_mode_mismatch:{case.case_id}")
        if spec.relative_length_class != case.relative_length_class:
            errors.append(f"relative_length_class_mismatch:{case.case_id}")

        try:
            mode, relative_class = resolve_relative_length_class(
                age_min=spec.age_min,
                age_max=spec.age_max,
                target_words=spec.target_words,
                reading_mode=spec.reading_mode,
            )
        except ValueError as exc:
            errors.append(f"length_policy_mismatch:{case.case_id}:{exc}")
            continue
        if mode != case.reading_mode or relative_class != case.relative_length_class:
            errors.append(f"resolved_policy_mismatch:{case.case_id}")

    expected = len(wave["age_cases"]) * len(wave["families"])
    if len(cases) != expected:
        errors.append(f"case_count:{len(cases)}:{expected}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile LUMI qualification waves.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("materialize", "validate", "matrix", "max-parallel"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--wave", required=True)
        cmd.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))

    args = parser.parse_args()
    wave_path = Path(args.wave)
    output_root = Path(args.output_root)

    if args.command == "materialize":
        cases = materialize_wave(wave_path, output_root=output_root)
        print(json.dumps({"case_count": len(cases)}, ensure_ascii=False))
        return

    if args.command == "validate":
        errors = validate_materialized_wave(wave_path, output_root=output_root)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, indent=2))
            raise SystemExit(2)
        print(
            json.dumps(
                {
                    "valid": True,
                    "case_count": len(
                        wave_cases(wave_path, output_root=output_root)
                    ),
                },
                indent=2,
            )
        )
        return

    if args.command == "max-parallel":
        print(int(load_wave(wave_path)["max_parallel"]))
        return

    print(
        json.dumps(
            matrix_payload(wave_path, output_root=output_root),
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
