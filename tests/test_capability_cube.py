from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.capability_cube import (
    build_capability_cube,
    build_evidence,
    default_reading_mode_for_age_tier,
    materialize_evidence,
    narrative_age_tier_for_range,
    render_cube_markdown,
    resolve_relative_length_class,
    standard_target_words_for_age_tier,
    verify_evidence_integrity,
)
from src.schemas import StorySpec


def fake_result(
    *,
    accepted: bool = True,
    judge: float = 4.2,
    minimum: int = 4,
    continuity_model: str = "typesafe/jev-1.13",
    generation_protocol_version: str = "english-story-production.v1",
    evaluation_protocol_version: str = "english-story-evaluation.v1",
) -> dict:
    return {
        "pipeline": "english_story_pipeline_v1",
        "generation_protocol_version": generation_protocol_version,
        "evaluation_protocol_version": evaluation_protocol_version,
        "models": {
            "generator": "openai/gpt-5.6-luna",
            "continuity_evaluator": continuity_model,
            "semantic_judge": "anthropic/claude-haiku-4.5",
        },
        "accepted": accepted,
        "word_count": 2010,
        "target_words": 2000,
        "deterministic_errors": [],
        "repeat_8gram_ratio": 0.0,
        "whole_story_jev": {
            "shadow_signal": "CONTINUE",
            "positive_probabilities": {"causal_chain": 0.92},
        },
        "final_judge": {
            "average": judge,
            "minimum": minimum,
            "scores": {"coherence": minimum, "continuity": minimum},
            "critical_failures": [],
            "repair_targets": [],
        },
        "scenes": [
            {
                "scene": 1,
                "target_words": 300,
                "word_count": 310,
                "attempts": [{}, {}],
                "semantic_repairs": [{}],
                "jev": {
                    "shadow_signal": "CONTINUE",
                    "positive_probabilities": {"no_contradiction": 0.91},
                    "below_threshold": {},
                },
                "elapsed_seconds": 12.5,
            }
        ],
        "timings": {"total_pipeline_seconds": 120.0},
        "costs": {"total_pipeline_usd": 0.04},
        "story_title": "Test",
        "story": "A complete test story.",
    }


def write_spec(
    path: Path,
    *,
    age_min: int,
    age_max: int,
    family: str,
    words: int = 2000,
) -> None:
    path.write_text(
        "\n".join(
            [
                "title_hint: Test",
                f"age_min: {age_min}",
                f"age_max: {age_max}",
                "language: en",
                f"target_words: {words}",
                f"narrative_family: {family}",
                "protagonist: A careful explorer",
                "setting: A test world",
                "theme: Evidence",
                "premise: A test premise",
                "constraints:",
                "  - Keep continuity.",
                "",
            ]
        ),
        encoding="utf-8",
    )


class CapabilityCubeTests(unittest.TestCase):
    def test_narrative_age_tiers_match_project_lumi_policy(self) -> None:
        cases = [
            (3, 5, "EARLY_CHILD"),
            (6, 8, "CHILD"),
            (9, 12, "MIDDLE_CHILD"),
            (13, 17, "TEEN"),
            (18, 24, "YOUNG_ADULT"),
            (25, 39, "ADULT"),
            (40, 59, "MATURE_ADULT"),
            (60, 120, "SENIOR"),
        ]
        for age_min, age_max, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    narrative_age_tier_for_range(age_min, age_max),
                    expected,
                )

    def test_age_range_may_not_cross_narrative_tier(self) -> None:
        with self.assertRaisesRegex(ValueError, "must fit exactly one"):
            narrative_age_tier_for_range(8, 9)

    def test_story_spec_supports_adult_ages(self) -> None:
        spec = StorySpec(
            age_min=25,
            age_max=39,
            language="en",
            target_words=2000,
            narrative_family="emotional_development",
            protagonist="A",
            setting="B",
            theme="C",
            premise="D",
        )
        self.assertEqual(spec.age_max, 39)

    def test_age_aware_standard_targets_and_reading_modes(self) -> None:
        expected = {
            "EARLY_CHILD": (500, "READ_ALOUD"),
            "CHILD": (1500, "EARLY_READER"),
            "MIDDLE_CHILD": (2800, "INDEPENDENT_READER"),
            "TEEN": (3800, "INDEPENDENT_READER"),
            "YOUNG_ADULT": (4200, "INDEPENDENT_READER"),
            "ADULT": (4200, "INDEPENDENT_READER"),
            "MATURE_ADULT": (4200, "INDEPENDENT_READER"),
            "SENIOR": (4200, "INDEPENDENT_READER"),
        }
        for tier, (words, mode) in expected.items():
            with self.subTest(tier=tier):
                self.assertEqual(standard_target_words_for_age_tier(tier), words)
                self.assertEqual(default_reading_mode_for_age_tier(tier), mode)

    def test_relative_standard_is_age_dependent(self) -> None:
        self.assertEqual(
            resolve_relative_length_class(
                age_min=4,
                age_max=4,
                target_words=500,
                reading_mode="READ_ALOUD",
            ),
            ("READ_ALOUD", "STANDARD"),
        )
        self.assertEqual(
            resolve_relative_length_class(
                age_min=15,
                age_max=15,
                target_words=3800,
                reading_mode="INDEPENDENT_READER",
            ),
            ("INDEPENDENT_READER", "STANDARD"),
        )
        with self.assertRaisesRegex(ValueError, "outside every qualified"):
            resolve_relative_length_class(
                age_min=4,
                age_max=4,
                target_words=2000,
                reading_mode="READ_ALOUD",
            )

    def test_invalidated_wave_spec_cannot_be_packed(self) -> None:
        spec_path = Path(
            "data/specifications/waves/age-standard-v1/"
            "child--exploration-mystery.yaml"
        )
        with self.assertRaisesRegex(ValueError, "marked invalid"):
            build_evidence(
                result=fake_result(),
                spec_path=spec_path,
                run_id="invalidated-wave",
                source="unit_test",
            )

    def test_evidence_rejects_age_inappropriate_word_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "bad-early-child.yaml"
            write_spec(
                spec_path,
                age_min=4,
                age_max=4,
                family="exploration_mystery",
                words=2000,
            )
            with self.assertRaisesRegex(ValueError, "outside every qualified"):
                build_evidence(
                    result=fake_result(),
                    spec_path=spec_path,
                    run_id="bad-age-length",
                    source="unit_test",
                )

    def test_evidence_materialization_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            result = fake_result()
            evidence = build_evidence(
                result=result,
                spec_path=spec_path,
                run_id="run-1",
                source="unit_test",
            )
            destination = materialize_evidence(
                evidence=evidence,
                raw_result=result,
                spec_path=spec_path,
                story_text="Test\n\nA complete test story.",
                output_root=root / "evidence",
            )
            self.assertTrue((destination / "manifest.json").exists())
            with self.assertRaisesRegex(FileExistsError, "Immutable evidence"):
                materialize_evidence(
                    evidence=evidence,
                    raw_result=result,
                    spec_path=spec_path,
                    story_text="changed",
                    output_root=root / "evidence",
                )

    def test_evidence_integrity_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            result = fake_result()
            evidence = build_evidence(
                result=result,
                spec_path=spec_path,
                run_id="run-1",
                source="unit_test",
            )
            destination = materialize_evidence(
                evidence=evidence,
                raw_result=result,
                spec_path=spec_path,
                story_text="Test\n\nA complete test story.",
                output_root=root / "evidence",
            )
            self.assertEqual(
                verify_evidence_integrity(root / "evidence"),
                [],
            )
            (destination / "story.txt").write_text(
                "tampered\n",
                encoding="utf-8",
            )
            errors = verify_evidence_integrity(root / "evidence")
            self.assertEqual(len(errors), 1)
            self.assertIn("sha256_mismatch", errors[0])

    def test_cube_never_merges_different_age_or_family_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_child = root / "child.yaml"
            spec_teen = root / "teen.yaml"
            spec_social = root / "social.yaml"
            write_spec(
                spec_child,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            write_spec(
                spec_teen,
                age_min=15,
                age_max=15,
                family="exploration_mystery",
                words=3800,
            )
            write_spec(
                spec_social,
                age_min=6,
                age_max=8,
                family="friendship_social_problem",
            )
            rows = [
                build_evidence(
                    result=fake_result(judge=4.5),
                    spec_path=spec_child,
                    run_id="child-mystery",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(judge=3.5),
                    spec_path=spec_teen,
                    run_id="teen-mystery",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(judge=4.0),
                    spec_path=spec_social,
                    run_id="child-social",
                    source="unit_test",
                ),
            ]
            cube = build_capability_cube(rows)
            self.assertEqual(cube["observed_cell_count"], 3)
            keyed = {
                (
                    x["narrative_age_tier"],
                    x["reading_mode"],
                    x["narrative_family"],
                    x["relative_length_class"],
                ): x
                for x in cube["cells"]
            }
            self.assertEqual(
                keyed[("CHILD", "EARLY_READER", "exploration_mystery", "STANDARD")][
                    "average_final_judge"
                ],
                4.5,
            )
            self.assertEqual(
                keyed[("TEEN", "INDEPENDENT_READER", "exploration_mystery", "STANDARD")][
                    "average_final_judge"
                ],
                3.5,
            )
            self.assertEqual(
                keyed[("CHILD", "EARLY_READER", "friendship_social_problem", "STANDARD")][
                    "average_final_judge"
                ],
                4.0,
            )

    def test_cube_never_merges_different_evaluation_stacks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            rows = [
                build_evidence(
                    result=fake_result(
                        continuity_model="typesafe/jev-1.13",
                        judge=4.5,
                    ),
                    spec_path=spec_path,
                    run_id="stack-a",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(
                        continuity_model="openai/gpt-5.6-luna",
                        judge=4.0,
                    ),
                    spec_path=spec_path,
                    run_id="stack-b",
                    source="unit_test",
                ),
            ]
            cube = build_capability_cube(rows)
            self.assertEqual(cube["observed_cell_count"], 2)
            self.assertEqual(
                len({cell["evaluation_stack_sha256"] for cell in cube["cells"]}),
                2,
            )

    def test_failed_run_is_preserved_and_counts_against_pass_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            failure = fake_result(accepted=False, judge=0.0, minimum=0)
            failure["word_count"] = 0
            failure["final_judge"] = {}
            failure["scenes"] = []
            failure["terminal_error"] = {
                "type": "RuntimeError",
                "message": "synthetic failure",
            }
            evidence = build_evidence(
                result=failure,
                spec_path=spec_path,
                run_id="failed-run",
                source="unit_test",
            )
            destination = materialize_evidence(
                evidence=evidence,
                raw_result=failure,
                spec_path=spec_path,
                story_text=None,
                output_root=root / "evidence",
            )
            self.assertFalse((destination / "story.txt").exists())
            self.assertEqual(evidence.terminal_error["type"], "RuntimeError")
            cube = build_capability_cube([evidence])
            cell = cube["cells"][0]
            self.assertEqual(cell["pass_rate"], 0.0)
            self.assertEqual(cell["terminal_failure_count"], 1)
            self.assertEqual(cell["terminal_error_counts"], {"RuntimeError": 1})

    def test_exact_target_words_and_age_ranges_remain_visible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_a = root / "a.yaml"
            spec_b = root / "b.yaml"
            write_spec(
                spec_a,
                age_min=6,
                age_max=6,
                family="exploration_mystery",
                words=1800,
            )
            write_spec(
                spec_b,
                age_min=8,
                age_max=8,
                family="exploration_mystery",
                words=2200,
            )
            rows = [
                build_evidence(
                    result=fake_result(judge=4.5),
                    spec_path=spec_a,
                    run_id="age6-1800",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(judge=3.5),
                    spec_path=spec_b,
                    run_id="age8-2200",
                    source="unit_test",
                ),
            ]
            cell = build_capability_cube(rows)["cells"][0]
            self.assertEqual(cell["target_words_observed"], [1800, 2200])
            self.assertEqual(set(cell["target_word_breakdown"]), {"1800", "2200"})
            self.assertEqual(set(cell["age_range_breakdown"]), {"6-6", "8-8"})

    def test_cube_aggregates_continuity_probabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            evidence = build_evidence(
                result=fake_result(),
                spec_path=spec_path,
                run_id="continuity-scores",
                source="unit_test",
            )
            cell = build_capability_cube([evidence])["cells"][0]
            self.assertEqual(
                cell["scene_continuity_probability_average"]["no_contradiction"],
                0.91,
            )
            self.assertEqual(
                cell["whole_story_continuity_probability_average"]["causal_chain"],
                0.92,
            )

    def test_cube_never_merges_different_generation_protocols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=6,
                age_max=8,
                family="exploration_mystery",
            )
            rows = [
                build_evidence(
                    result=fake_result(
                        generation_protocol_version="english-story-production.v1",
                    ),
                    spec_path=spec_path,
                    run_id="protocol-a",
                    source="unit_test",
                ),
                build_evidence(
                    result=fake_result(
                        generation_protocol_version="english-story-production.v2",
                    ),
                    spec_path=spec_path,
                    run_id="protocol-b",
                    source="unit_test",
                ),
            ]
            cube = build_capability_cube(rows)
            self.assertEqual(cube["observed_cell_count"], 2)
            self.assertEqual(
                len(
                    {
                        cell["generation_protocol_sha256"]
                        for cell in cube["cells"]
                    }
                ),
                2,
            )

    def test_markdown_report_exposes_generation_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = root / "spec.yaml"
            write_spec(
                spec_path,
                age_min=13,
                age_max=17,
                family="puzzle_problem_solving",
                words=3800,
            )
            evidence = build_evidence(
                result=fake_result(
                    generation_protocol_version="english-story-production.v3",
                ),
                spec_path=spec_path,
                run_id="protocol-v3-report",
                source="unit_test",
            )
            markdown = render_cube_markdown(build_capability_cube([evidence]))
            self.assertIn("| Protocol |", markdown)
            self.assertIn("english-story-production.v3", markdown)

    def test_committed_qualification_evidence_integrity(self) -> None:
        root = Path("evidence/model_qualification")
        self.assertTrue(root.exists())
        self.assertEqual(verify_evidence_integrity(root), [])


if __name__ == "__main__":
    unittest.main()
