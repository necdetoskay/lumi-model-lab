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

    def test_invalid_evidence_scene_fails_closed(self) -> None:
        outcome = {
            "authority_revision": "r1",
            "mutations": [
                {
                    "mutation_type": "CHARACTER_KNOWLEDGE_ADD",
                    "entity_ref": "CHARACTER:PROTAGONIST",
                    "field_key": "knowledge.discoveries",
                    "value": "learned fact",
                    "evidence_scenes": [5],
                    "reason": "Scene 5 does not exist in this four-scene story.",
                }
            ],
        }
        errors = v5.validate_outcome(outcome, 4, self.authority)
        self.assertIn("mutation_0_invalid_evidence_scene:5", errors)

    def test_duplicate_mutation_fails_closed(self) -> None:
        row = {
            "mutation_type": "WORLD_FACT_SET",
            "entity_ref": "WORLD:CURRENT",
            "field_key": "garden.marker_status",
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
