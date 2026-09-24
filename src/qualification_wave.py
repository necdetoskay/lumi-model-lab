from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.capability_cube import (
    length_band_for_target_words,
    load_capability_config,
    narrative_age_tier_for_range,
)
from src.schemas import StorySpec

WAVE_SCHEMA_VERSION = "qualification-wave.v1"
DEFAULT_OUTPUT_ROOT = Path("data/specifications/waves")


@dataclass(frozen=True)
class WaveCase:
    case_id: str
    age_tier: str
    exact_age: int
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

    capability = load_capability_config()
    expected_tiers = list(capability["narrative_age_tiers"].keys())
    representative = payload.get("representative_ages") or {}
    if list(representative.keys()) != expected_tiers:
        raise ValueError(
            "representative_ages must list every canonical NarrativeAgeTier "
            "in canonical order"
        )

    families = payload.get("families") or {}
    if not families:
        raise ValueError("wave requires at least one narrative family")
    unknown = sorted(set(families) - set(capability["narrative_families"]))
    if unknown:
        raise ValueError(f"unknown narrative families: {unknown}")

    target_words = int(payload.get("target_words") or 0)
    if length_band_for_target_words(target_words) != "STANDARD":
        raise ValueError(
            "age-standard-v1 requires a STANDARD target length; "
            f"got {target_words}"
        )

    for tier, exact_age in representative.items():
        exact_age = int(exact_age)
        actual_tier = narrative_age_tier_for_range(exact_age, exact_age)
        if actual_tier != tier:
            raise ValueError(
                f"representative age {exact_age} maps to {actual_tier}, not {tier}"
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
    target_words = int(wave["target_words"])
    rows: list[WaveCase] = []
    for tier, exact_age_raw in wave["representative_ages"].items():
        exact_age = int(exact_age_raw)
        for family in wave["families"]:
            case_id = f"{_slug(tier)}--{_slug(family)}"
            spec_path = output_root / wave_id / f"{case_id}.yaml"
            rows.append(
                WaveCase(
                    case_id=case_id,
                    age_tier=tier,
                    exact_age=exact_age,
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
                f"The intended reader is exactly age {case.exact_age}; do not write "
                "for a younger or older audience."
            ),
        ]
        spec = StorySpec(
            title_hint=str(family.get("title_hint") or "").strip() or None,
            age_min=case.exact_age,
            age_max=case.exact_age,
            language=str(wave.get("language") or "en"),
            target_words=case.target_words,
            narrative_family=case.narrative_family,
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
        if spec.target_words != int(wave["target_words"]):
            errors.append(f"target_words_mismatch:{case.case_id}")
        if length_band_for_target_words(spec.target_words) != "STANDARD":
            errors.append(f"length_band_mismatch:{case.case_id}")

    expected = len(wave["representative_ages"]) * len(wave["families"])
    if len(cases) != expected:
        errors.append(f"case_count:{len(cases)}:{expected}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile LUMI qualification waves.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("materialize", "validate", "matrix"):
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

    print(
        json.dumps(
            matrix_payload(wave_path, output_root=output_root),
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()
