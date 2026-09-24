from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from src.capability_coverage import build_coverage_plan, matrix_payload
from src.capability_cube import build_evidence
from src.qualification_wave import wave_cases

WAVE = Path("configs/qualification_waves/age-relative-standard-v2.yaml")


def fake_result(
    *,
    protocol: str,
    attempts: int = 6,
    semantic_repairs: int = 0,
    accepted: bool = True,
    continuity_model: str = "typesafe/jev-1.13",
) -> dict:
    attempt_rows = [{"kind": "generate"} for _ in range(max(attempts, 1))]
    repair_rows = [{} for _ in range(semantic_repairs)]
    return {
        "pipeline": "english_story_pipeline_v1",
        "generation_protocol_version": protocol,
        "evaluation_protocol_version": "english-story-evaluation.v1",
        "models": {
            "generator": "openai/gpt-5.6-luna",
            "continuity_evaluator": continuity_model,
            "semantic_judge": "anthropic/claude-haiku-4.5",
        },
        "accepted": accepted,
        "word_count": 1500 if accepted else 0,
        "target_words": 1500,
        "deterministic_errors": [],
        "repeat_8gram_ratio": 0.0,
        "whole_story_continuity": {
            "shadow_signal": "CONTINUE",
            "positive_probabilities": {"causal_chain": 0.9},
            "below_threshold": {},
        },
        "final_judge": {
            "average": 4.0 if accepted else None,
            "minimum": 4 if accepted else None,
            "scores": {"coherence": 4} if accepted else {},
            "critical_failures": [],
            "repair_targets": [],
        },
        "scenes": [
            {
                "scene": 1,
                "target_words": 250,
                "word_count": 250,
                "attempts": attempt_rows,
                "semantic_repairs": repair_rows,
                "jev": {
                    "shadow_signal": "CONTINUE",
                    "positive_probabilities": {"no_contradiction": 0.9},
                    "below_threshold": {},
                },
            }
        ],
        "timings": {"total_pipeline_seconds": 100.0},
        "costs": {"total_pipeline_usd": 0.04},
        "story_title": "Synthetic",
        "story": "Synthetic evidence.",
        "terminal_error": (
            None
            if accepted
            else {"type": "RuntimeError", "message": "synthetic failure"}
        ),
    }


def case_spec(age_tier: str, family: str) -> Path:
    for case in wave_cases(WAVE):
        if case.age_tier == age_tier and case.narrative_family == family:
            return case.spec_path
    raise AssertionError(f"missing case {age_tier}/{family}")


class CapabilityCoverageTests(unittest.TestCase):
    def test_empty_evidence_plan_is_age_balanced_and_reports_scope_gap(self) -> None:
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=[])
        self.assertEqual(plan["summary"]["executable_scope_case_count"], 24)
        self.assertEqual(plan["summary"]["canonical_standard_case_count"], 80)
        self.assertEqual(plan["summary"]["canonical_out_of_scope_case_count"], 56)
        self.assertEqual(plan["summary"]["current_protocol_unknown_case_count"], 24)
        self.assertEqual(len(plan["selected"]), 8)
        self.assertEqual(
            len({item["age_tier"] for item in plan["selected"]}),
            8,
        )
        self.assertTrue(
            all(item["current_status"] == "UNKNOWN" for item in plan["selected"])
        )

    def test_historical_burden_breaks_family_gap_tie_inside_age(self) -> None:
        emotional_spec = case_spec("CHILD", "emotional_development")
        exploration_spec = case_spec("CHILD", "exploration_mystery")
        evidence = [
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v1",
                    attempts=9,
                    semantic_repairs=3,
                ),
                spec_path=emotional_spec,
                run_id="historical-emotional",
                source="unit_test",
            ),
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v1",
                    attempts=6,
                    semantic_repairs=0,
                ),
                spec_path=exploration_spec,
                run_id="historical-exploration",
                source="unit_test",
            ),
        ]
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=evidence)
        child = next(
            item for item in plan["selected"] if item["age_tier"] == "CHILD"
        )
        self.assertEqual(child["narrative_family"], "emotional_development")
        self.assertEqual(child["historical_semantic_repairs_per_run"], 3.0)
        self.assertEqual(child["historical_scene_attempts_per_run"], 9.0)

    def test_current_protocol_evidence_is_not_counted_as_historical(self) -> None:
        spec = case_spec("TEEN", "puzzle_problem_solving")
        current = build_evidence(
            result=fake_result(
                protocol="english-story-production.v3",
                attempts=6,
                semantic_repairs=0,
            ),
            spec_path=spec,
            run_id="current-v3",
            source="unit_test",
        )
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=[current])
        candidate = next(
            item
            for item in plan["candidates"]
            if item["age_tier"] == "TEEN"
            and item["narrative_family"] == "puzzle_problem_solving"
        )
        self.assertEqual(candidate["current_run_count"], 1)
        self.assertEqual(candidate["current_status"], "THIN")
        self.assertEqual(candidate["historical_run_count"], 0)

    def test_high_repair_thin_cell_gets_single_sentinel_repeat_slot(self) -> None:
        spec = case_spec("MIDDLE_CHILD", "emotional_development")
        current = build_evidence(
            result=fake_result(
                protocol="english-story-production.v3",
                attempts=9,
                semantic_repairs=3,
            ),
            spec_path=spec,
            run_id="middle-child-emotional-heavy",
            source="unit_test",
        )
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=[current])
        sentinel = [
            item
            for item in plan["selected"]
            if item["selection_lane"] == "SENTINEL_REPEAT"
        ]
        self.assertEqual(len(sentinel), 1)
        self.assertEqual(
            sentinel[0]["case_id"],
            "middle-child--emotional-development",
        )
        self.assertEqual(sentinel[0]["current_semantic_repairs_per_run"], 3.0)
        self.assertEqual(
            plan["summary"]["sentinel_repeat_case_id"],
            "middle-child--emotional-development",
        )
        self.assertEqual(len({item["age_tier"] for item in plan["selected"]}), 8)
        self.assertEqual(
            sum(1 for item in plan["selected"] if item["age_tier"] == "MIDDLE_CHILD"),
            1,
        )

    def test_single_repair_thin_cell_does_not_trigger_sentinel_repeat(self) -> None:
        spec = case_spec("TEEN", "emotional_development")
        current = build_evidence(
            result=fake_result(
                protocol="english-story-production.v3",
                attempts=7,
                semantic_repairs=1,
            ),
            spec_path=spec,
            run_id="teen-emotional-one-repair",
            source="unit_test",
        )
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=[current])
        self.assertIsNone(plan["summary"]["sentinel_repeat_case_id"])
        self.assertFalse(
            any(
                item["selection_lane"] == "SENTINEL_REPEAT"
                for item in plan["selected"]
            )
        )

    def test_persistent_anomaly_on_one_fixture_requires_new_fixture(self) -> None:
        spec = case_spec("ADULT", "puzzle_problem_solving")
        evidence = [
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=9,
                    semantic_repairs=2,
                ),
                spec_path=spec,
                run_id="adult-puzzle-heavy-a",
                source="unit_test",
            ),
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=8,
                    semantic_repairs=2,
                ),
                spec_path=spec,
                run_id="adult-puzzle-heavy-b",
                source="unit_test",
            ),
        ]
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=evidence)
        candidate = next(
            item
            for item in plan["candidates"]
            if item["age_tier"] == "ADULT"
            and item["narrative_family"] == "puzzle_problem_solving"
        )
        self.assertEqual(candidate["current_distinct_spec_count"], 1)
        self.assertEqual(candidate["current_anomalous_run_count"], 2)
        self.assertEqual(candidate["current_anomalous_spec_count"], 1)
        self.assertTrue(candidate["diagnostic_fixture_required"])
        self.assertFalse(candidate["targeted_intervention_candidate"])
        self.assertIn(
            "adult--puzzle-problem-solving",
            plan["summary"]["diagnostic_fixture_required_case_ids"],
        )
        self.assertNotIn(
            "adult--puzzle-problem-solving",
            {item["case_id"] for item in plan["selected"]},
        )

    def test_anomaly_on_two_fixtures_becomes_intervention_candidate(self) -> None:
        spec = case_spec("ADULT", "puzzle_problem_solving")
        with tempfile.TemporaryDirectory() as tmp:
            variant = Path(tmp) / "adult-puzzle-variant.yaml"
            payload = yaml.safe_load(spec.read_text(encoding="utf-8"))
            payload["title_hint"] = "A Different Puzzle"
            payload["premise"] = (
                str(payload["premise"])
                + " The observable evidence and final decision differ from the base fixture."
            )
            variant.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            evidence = [
                build_evidence(
                    result=fake_result(
                        protocol="english-story-production.v3",
                        attempts=9,
                        semantic_repairs=2,
                    ),
                    spec_path=spec,
                    run_id="adult-puzzle-base-heavy",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(
                        protocol="english-story-production.v3",
                        attempts=8,
                        semantic_repairs=2,
                    ),
                    spec_path=variant,
                    run_id="adult-puzzle-variant-heavy",
                    source="unit_test",
                ),
            ]
            plan = build_coverage_plan(WAVE, batch_size=8, evidence=evidence)
            candidate = next(
                item
                for item in plan["candidates"]
                if item["age_tier"] == "ADULT"
                and item["narrative_family"] == "puzzle_problem_solving"
            )
            self.assertEqual(candidate["current_distinct_spec_count"], 2)
            self.assertEqual(candidate["current_anomalous_spec_count"], 2)
            self.assertFalse(candidate["diagnostic_fixture_required"])
            self.assertTrue(candidate["targeted_intervention_candidate"])
            self.assertIn(
                "adult--puzzle-problem-solving",
                plan["summary"]["targeted_intervention_candidate_case_ids"],
            )
            self.assertNotIn(
                "adult--puzzle-problem-solving",
                {item["case_id"] for item in plan["selected"]},
            )

    def test_one_heavy_then_clean_repeat_resolves_sentinel(self) -> None:
        spec = case_spec("MIDDLE_CHILD", "puzzle_problem_solving")
        evidence = [
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=10,
                    semantic_repairs=4,
                ),
                spec_path=spec,
                run_id="middle-puzzle-heavy",
                source="unit_test",
            ),
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=6,
                    semantic_repairs=0,
                ),
                spec_path=spec,
                run_id="middle-puzzle-clean",
                source="unit_test",
            ),
        ]
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=evidence)
        candidate = next(
            item
            for item in plan["candidates"]
            if item["age_tier"] == "MIDDLE_CHILD"
            and item["narrative_family"] == "puzzle_problem_solving"
        )
        self.assertEqual(candidate["current_anomalous_run_count"], 1)
        self.assertFalse(candidate["latest_current_run_anomalous"])
        self.assertTrue(candidate["sentinel_resolved_by_clean_repeat"])
        self.assertFalse(candidate["diagnostic_fixture_required"])
        self.assertFalse(candidate["targeted_intervention_candidate"])
        self.assertIsNone(plan["summary"]["sentinel_repeat_case_id"])

    def test_clean_then_heavy_repeat_reopens_sentinel(self) -> None:
        spec = case_spec("MIDDLE_CHILD", "puzzle_problem_solving")
        evidence = [
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=6,
                    semantic_repairs=0,
                ),
                spec_path=spec,
                run_id="middle-puzzle-clean-first",
                source="unit_test",
            ),
            build_evidence(
                result=fake_result(
                    protocol="english-story-production.v3",
                    attempts=10,
                    semantic_repairs=4,
                ),
                spec_path=spec,
                run_id="middle-puzzle-heavy-latest",
                source="unit_test",
            ),
        ]
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=evidence)
        candidate = next(
            item
            for item in plan["candidates"]
            if item["age_tier"] == "MIDDLE_CHILD"
            and item["narrative_family"] == "puzzle_problem_solving"
        )
        self.assertTrue(candidate["latest_current_run_anomalous"])
        self.assertFalse(candidate["sentinel_resolved_by_clean_repeat"])
        self.assertEqual(
            plan["summary"]["sentinel_repeat_case_id"],
            "middle-child--puzzle-problem-solving",
        )

    def test_different_evaluation_stack_is_ignored(self) -> None:
        spec = case_spec("CHILD", "emotional_development")
        foreign = build_evidence(
            result=fake_result(
                protocol="english-story-production.v3",
                attempts=12,
                semantic_repairs=5,
                continuity_model="openai/gpt-5.6-luna",
            ),
            spec_path=spec,
            run_id="foreign-evaluator",
            source="unit_test",
        )
        plan = build_coverage_plan(WAVE, batch_size=8, evidence=[foreign])
        candidate = next(
            item
            for item in plan["candidates"]
            if item["age_tier"] == "CHILD"
            and item["narrative_family"] == "emotional_development"
        )
        self.assertEqual(candidate["current_run_count"], 0)
        self.assertEqual(candidate["historical_run_count"], 0)
        self.assertEqual(candidate["current_status"], "UNKNOWN")

    def test_matrix_contains_only_selected_cases_and_generic_roles(self) -> None:
        plan = build_coverage_plan(WAVE, batch_size=4, evidence=[])
        matrix = matrix_payload(plan)["include"]
        self.assertEqual(len(matrix), 4)
        self.assertTrue(
            all(row["generator_model"] == "openai/gpt-5.6-luna" for row in matrix)
        )
        self.assertTrue(
            all(
                row["continuity_evaluator_model"] == "typesafe/jev-1.13"
                for row in matrix
            )
        )
        self.assertTrue(
            all(
                row["semantic_judge_model"] == "anthropic/claude-haiku-4.5"
                for row in matrix
            )
        )


if __name__ == "__main__":
    unittest.main()
