import copy
import importlib.util
import json
import unittest
from pathlib import Path


def load_module(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


commit_v1 = load_module(
    "state_commit_simulator_v1",
    "experiments/prototypes/state_commit_simulator_v1.py",
)


class StateCommitSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = json.loads(
            Path(
                "experiments/state_commit/v1/production-like-initial-state.json"
            ).read_text(encoding="utf-8")
        )
        self.authority = json.loads(
            Path(
                "experiments/state_authority/age10-1500-production-context.json"
            ).read_text(encoding="utf-8")
        )
        self.outcome = json.loads(
            Path(
                "experiments/state_commit/v1/production-like-outcome.json"
            ).read_text(encoding="utf-8")
        )
        self.key = "story:prodlike-deniz:revision:1"

    def commit_once(self):
        return commit_v1.commit(
            state=copy.deepcopy(self.state),
            authority=self.authority,
            outcome=self.outcome,
            idempotency_key=self.key,
        )

    def test_atomic_commit_updates_each_touched_entity_once(self) -> None:
        committed, result = self.commit_once()

        self.assertEqual(result["status"], "COMMITTED")
        self.assertEqual(
            result["mutated_entities"],
            [
                "CHARACTER:PROTAGONIST",
                "OPPORTUNITY:CURRENT",
                "SAGA:CURRENT",
                "WORLD:CURRENT",
            ],
        )
        self.assertEqual(
            committed["entities"]["CHARACTER:PROTAGONIST"]["revision"],
            22,
        )
        self.assertEqual(committed["entities"]["WORLD:CURRENT"]["revision"], 35)
        self.assertEqual(committed["entities"]["SAGA:CURRENT"]["revision"], 10)
        self.assertEqual(
            committed["entities"]["OPPORTUNITY:CURRENT"]["revision"],
            8,
        )
        self.assertEqual(
            committed["entities"]["WORLD:CURRENT"]["values"][
                "local_area.OLD_PUMP_PATH.status"
            ],
            "RUMORED",
        )
        self.assertEqual(
            committed["entities"]["OPPORTUNITY:CURRENT"]["values"]["status"],
            "CONSUMED",
        )
        self.assertIsInstance(
            committed["entities"]["WORLD:CURRENT"]["values"][
                "commons.sound_hypotheses"
            ],
            str,
        )

    def test_identical_replay_is_idempotent_noop(self) -> None:
        committed, first = self.commit_once()
        before_replay = copy.deepcopy(committed)

        replayed, replay = commit_v1.commit(
            state=committed,
            authority=self.authority,
            outcome=self.outcome,
            idempotency_key=self.key,
        )

        self.assertEqual(first["status"], "COMMITTED")
        self.assertEqual(replay["status"], "IDEMPOTENT_REPLAY")
        self.assertEqual(replayed, before_replay)
        self.assertEqual(
            replayed["entities"]["CHARACTER:PROTAGONIST"]["revision"],
            22,
        )
        discoveries = replayed["entities"]["CHARACTER:PROTAGONIST"]["values"][
            "knowledge.discoveries"
        ]
        learned = self.outcome["mutations"][0]["value"]
        self.assertEqual(discoveries.count(learned), 1)

    def test_stale_revision_aborts_all_mutations(self) -> None:
        stale = copy.deepcopy(self.state)
        stale["entities"]["WORLD:CURRENT"]["revision"] = 35
        before = copy.deepcopy(stale)

        returned, result = commit_v1.commit(
            state=stale,
            authority=self.authority,
            outcome=self.outcome,
            idempotency_key=self.key,
        )

        self.assertEqual(result["status"], "CONFLICT")
        self.assertTrue(
            any("stale_revision" in item for item in result["conflicts"])
        )
        self.assertEqual(returned, before)
        self.assertEqual(
            returned["entities"]["CHARACTER:PROTAGONIST"]["revision"],
            21,
        )
        self.assertEqual(
            returned["entities"]["OPPORTUNITY:CURRENT"]["values"]["status"],
            "AVAILABLE",
        )

    def test_stale_fingerprint_aborts_all_mutations(self) -> None:
        stale = copy.deepcopy(self.state)
        stale["entities"]["WORLD:CURRENT"]["fingerprint"] = "changed-world-fp"
        before = copy.deepcopy(stale)

        returned, result = commit_v1.commit(
            state=stale,
            authority=self.authority,
            outcome=self.outcome,
            idempotency_key=self.key,
        )

        self.assertEqual(result["status"], "CONFLICT")
        self.assertTrue(
            any("stale_fingerprint" in item for item in result["conflicts"])
        )
        self.assertEqual(returned, before)

    def test_same_idempotency_key_with_different_outcome_is_rejected(self) -> None:
        committed, first = self.commit_once()
        changed_outcome = copy.deepcopy(self.outcome)
        changed_outcome["mutations"][0]["value"] += " changed"
        before = copy.deepcopy(committed)

        returned, result = commit_v1.commit(
            state=committed,
            authority=self.authority,
            outcome=changed_outcome,
            idempotency_key=self.key,
        )

        self.assertEqual(first["status"], "COMMITTED")
        self.assertEqual(result["status"], "IDEMPOTENCY_COLLISION")
        self.assertEqual(returned, before)

    def test_apply_failure_rolls_back_prior_working_copy_changes(self) -> None:
        broken = copy.deepcopy(self.state)
        broken["entities"]["CHARACTER:PROTAGONIST"]["values"][
            "knowledge.discoveries"
        ] = "not-a-list"

        reordered = copy.deepcopy(self.outcome)
        # Apply a valid world mutation first, then force the character append to fail.
        world = next(
            row
            for row in reordered["mutations"]
            if row["entity_ref"] == "WORLD:CURRENT"
        )
        character = next(
            row
            for row in reordered["mutations"]
            if row["entity_ref"] == "CHARACTER:PROTAGONIST"
        )
        rest = [
            row
            for row in reordered["mutations"]
            if row not in (world, character)
        ]
        reordered["mutations"] = [world, character, *rest]
        before = copy.deepcopy(broken)

        returned, result = commit_v1.commit(
            state=broken,
            authority=self.authority,
            outcome=reordered,
            idempotency_key=self.key,
        )

        self.assertEqual(result["status"], "ABORTED")
        self.assertEqual(returned, before)
        self.assertIsNone(
            returned["entities"]["WORLD:CURRENT"]["values"][
                "commons.sound_hypotheses"
            ]
        )


if __name__ == "__main__":
    unittest.main()
