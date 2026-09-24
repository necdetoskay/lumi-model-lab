import importlib.util
import unittest
from pathlib import Path


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v5 = load_module(
    "story_v5_whole_draft_prototype",
    "experiments/prototypes/story_v5_whole_draft_prototype.py",
)
pairwise = load_module(
    "story_pairwise_judge_v1",
    "experiments/prototypes/story_pairwise_judge_v1.py",
)


class TypedStateMutationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authority = {
            "revision": "r1",
            "entities": [
                {
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "entity_kind": "CHARACTER",
                    "expected_revision": 12,
                    "expected_fingerprint": "char-r12-fp",
                },
                {
                    "entity_ref": "WORLD:CURRENT",
                    "entity_kind": "WORLD",
                    "expected_revision": 8,
                    "expected_fingerprint": "world-r8-fp",
                },
            ],
            "allowed_mutations": [
                {
                    "mutation_type": "CHARACTER_KNOWLEDGE_ADD",
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "field_key": "knowledge.discoveries",
                },
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                },
            ],
        }

    def test_valid_authorized_mutation_passes(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                    "base_revision": 8,
                    "base_fingerprint": "world-r8-fp",
                    "value": "restored",
                    "evidence_scenes": [4],
                    "reason": "The final scene explicitly restores the marker.",
                }
            ],
        }
        self.assertEqual(v5.validate_outcome(outcome, 4, self.authority), [])

    def test_model_invented_field_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "invented.secret_field",
                    "base_revision": 8,
                    "base_fingerprint": "world-r8-fp",
                    "value": "anything",
                    "evidence_scenes": [2],
                    "reason": "Attempted free-form persistence.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertTrue(any(e.startswith("mutation_not_authorized:") for e in errors))

    def test_transient_emotion_cannot_be_persisted_without_authority(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "CHARACTER_STATE_SET",
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "field_key": "emotional_state",
                    "base_revision": 12,
                    "base_fingerprint": "char-r12-fp",
                    "value": "proud",
                    "evidence_scenes": [4],
                    "reason": "The protagonist feels proud in the ending.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertTrue(any(e.startswith("mutation_not_authorized:") for e in errors))

    def test_wrong_authority_revision_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "stale-r0",
            "mutations": [],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("outcome_authority_revision_mismatch", errors)

    def test_wrong_entity_base_revision_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                    "base_revision": 7,
                    "base_fingerprint": "world-r8-fp",
                    "value": "restored",
                    "evidence_scenes": [4],
                    "reason": "Stale revision must not commit.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_base_revision_mismatch", errors)

    def test_wrong_entity_fingerprint_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                    "base_revision": 8,
                    "base_fingerprint": "stale-world-fp",
                    "value": "restored",
                    "evidence_scenes": [4],
                    "reason": "Stale fingerprint must not commit.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_base_fingerprint_mismatch", errors)

    def test_epistemic_class_mismatch_fails_closed(self) -> None:
        authority = {
            "revision": "r1",
            "entities": [
                {
                    "entity_ref": "WORLD:CURRENT",
                    "entity_kind": "WORLD",
                    "expected_revision": 8,
                    "expected_fingerprint": "world-r8-fp",
                }
            ],
            "allowed_mutations": [
                {
                    "mutation_type": "WORLD_HYPOTHESIS_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "commons.sound_hypotheses",
                    "epistemic_class": "BEST_SUPPORTED_HYPOTHESIS",
                }
            ],
        }
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_HYPOTHESIS_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "commons.sound_hypotheses",
                    "epistemic_class": "FACT",
                    "base_revision": 8,
                    "base_fingerprint": "world-r8-fp",
                    "value": "unseen contact point caused the sound",
                    "evidence_scenes": [4],
                    "reason": "A hypothesis must not be upgraded into a fact.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, authority)
        self.assertIn("mutation_0_epistemic_class_mismatch", errors)

    def test_invalid_evidence_scene_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "CHARACTER_KNOWLEDGE_ADD",
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "field_key": "knowledge.discoveries",
                    "base_revision": 12,
                    "base_fingerprint": "char-r12-fp",
                    "value": "learned fact",
                    "evidence_scenes": [5],
                    "reason": "Scene 5 does not exist in this four-scene story.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_invalid_evidence_scene:5", errors)

    def test_stale_entity_revision_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                    "base_revision": 7,
                    "base_fingerprint": "world-r8-fp",
                    "value": "restored",
                    "evidence_scenes": [4],
                    "reason": "Attempt based on a stale entity revision.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_base_revision_mismatch", errors)

    def test_wrong_entity_fingerprint_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "WORLD_FACT_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "garden.marker_status",
                    "base_revision": 8,
                    "base_fingerprint": "wrong-fingerprint",
                    "value": "restored",
                    "evidence_scenes": [4],
                    "reason": "Attempt based on the wrong snapshot fingerprint.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_base_fingerprint_mismatch", errors)

    def test_duplicate_mutation_fails_closed(self) -> None:
        row = {
            "mutation_type": "WORLD_FACT_SET",
            "entity_ref": "WORLD:CURRENT",
            "field_key": "garden.marker_status",
            "base_revision": 8,
            "base_fingerprint": "world-r8-fp",
            "value": "restored",
            "evidence_scenes": [4],
            "reason": "Supported by ending.",
        }
        outcome = {
            "authority_revision": "r1",
            "mutations": [dict(row), dict(row)],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_1_duplicate", errors)


class ContextAuthorityAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = {
            "character": {
                "entity_ref": "CHARACTER:PROTAGONIST",
                "revision": 21,
                "fingerprint": "char-r21-fp",
            },
            "world": {
                "entity_ref": "WORLD:CURRENT",
                "revision": 34,
                "fingerprint": "world-r34-fp",
            },
            "opportunity": {
                "entity_ref": "OPPORTUNITY:CURRENT",
                "revision": 7,
                "fingerprint": "opp-r7-fp",
            },
            "saga": {
                "entity_ref": "SAGA:CURRENT",
                "revision": 9,
                "fingerprint": "saga-r9-fp",
            },
        }
        self.authority = {
            "entities": [
                {
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "expected_revision": 21,
                    "expected_fingerprint": "char-r21-fp",
                },
                {
                    "entity_ref": "WORLD:CURRENT",
                    "expected_revision": 34,
                    "expected_fingerprint": "world-r34-fp",
                },
                {
                    "entity_ref": "OPPORTUNITY:CURRENT",
                    "expected_revision": 7,
                    "expected_fingerprint": "opp-r7-fp",
                },
                {
                    "entity_ref": "SAGA:CURRENT",
                    "expected_revision": 9,
                    "expected_fingerprint": "saga-r9-fp",
                },
            ],
            "allowed_mutations": [
                {
                    "mutation_type": "WORLD_HYPOTHESIS_SET",
                    "entity_ref": "WORLD:CURRENT",
                    "field_key": "commons.sound_hypotheses",
                }
            ],
        }

    def test_exact_context_snapshot_alignment_passes(self) -> None:
        self.assertEqual(
            v5.validate_state_authority_context_alignment(
                self.context,
                self.authority,
            ),
            [],
        )

    def test_stale_authority_revision_vs_context_fails_closed(self) -> None:
        authority = {
            **self.authority,
            "entities": [dict(row) for row in self.authority["entities"]],
        }
        authority["entities"][1]["expected_revision"] = 33
        errors = v5.validate_state_authority_context_alignment(
            self.context,
            authority,
        )
        self.assertIn(
            "state_authority_context_revision_mismatch:WORLD:CURRENT",
            errors,
        )

    def test_stale_authority_fingerprint_vs_context_fails_closed(self) -> None:
        authority = {
            **self.authority,
            "entities": [dict(row) for row in self.authority["entities"]],
        }
        authority["entities"][0]["expected_fingerprint"] = "stale-char-fp"
        errors = v5.validate_state_authority_context_alignment(
            self.context,
            authority,
        )
        self.assertIn(
            "state_authority_context_fingerprint_mismatch:CHARACTER:PROTAGONIST",
            errors,
        )

    def test_authority_entity_absent_from_context_fails_closed(self) -> None:
        authority = {
            **self.authority,
            "entities": [
                *[dict(row) for row in self.authority["entities"]],
                {
                    "entity_ref": "NPC:UNSCOPED",
                    "expected_revision": 1,
                    "expected_fingerprint": "npc-fp",
                },
            ],
        }
        errors = v5.validate_state_authority_context_alignment(
            self.context,
            authority,
        )
        self.assertIn(
            "state_authority_entity_not_in_context:NPC:UNSCOPED",
            errors,
        )

    def test_mutation_entity_must_be_declared_by_authority(self) -> None:
        authority = {
            **self.authority,
            "allowed_mutations": [
                {
                    "mutation_type": "NPC_STATE_SET",
                    "entity_ref": "NPC:UNDECLARED",
                    "field_key": "status",
                }
            ],
        }
        errors = v5.validate_state_authority_context_alignment(
            self.context,
            authority,
        )
        self.assertIn(
            "state_authority_mutation_entity_undeclared:0:NPC:UNDECLARED",
            errors,
        )


class PairwiseCalibrationContractTests(unittest.TestCase):
    def test_reverse_winner_maps_labels_back_to_original_candidates(self) -> None:
        self.assertEqual(pairwise.reverse_winner("A"), "B")
        self.assertEqual(pairwise.reverse_winner("B"), "A")
        self.assertEqual(pairwise.reverse_winner("TIE"), "TIE")

    def test_swapped_order_disagreement_is_inconclusive_policy(self) -> None:
        forward = "B"
        reverse_normalized = "TIE"
        overall_consistent = forward == reverse_normalized
        calibrated_winner = forward if overall_consistent else "INCONCLUSIVE"
        status = "STABLE" if overall_consistent else "POSITION_SENSITIVE"
        self.assertEqual(status, "POSITION_SENSITIVE")
        self.assertEqual(calibrated_winner, "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
