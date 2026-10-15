"""SERA first-scene live runner: offline contracts only, no provider calls."""
from __future__ import annotations

import json
import unittest

from experiments.sera.mara_s1_live import (
    WRITER_MODEL, EXTRACTOR_MODEL, JEV_MODEL,
    REGISTRY, SCENE_KEY, SPEND_STOP_USD,
    deterministic_shadow, make_entry, writer_messages,
)
from experiments.sera.spine_contracts import (
    compile_scene_contracts, load_frozen_spine, SOURCE_RELATIVE_PATH,
)


class FirstScenePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spine = load_frozen_spine(__import__("pathlib").Path(
            SOURCE_RELATIVE_PATH
        ))
        cls.contracts = compile_scene_contracts(cls.spine)

    def test_read_only_first_scene_is_exact_hook(self):
        self.assertEqual(len(self.contracts), 9)
        self.assertEqual(self.contracts[0]["key"], "hook_empty_platform")
        self.assertEqual(self.contracts[1]["key"], "orient_rules_of_record")
        msgs = writer_messages(self.spine, self.contracts[0], make_entry())
        data = json.loads(msgs[1]["content"])
        self.assertEqual(data["scene_contract"]["key"], "hook_empty_platform")
        self.assertEqual(data["next_beat_guard"]["key"], "orient_rules_of_record")
        self.assertNotIn("full_story", data)

    def test_entry_has_watch_notebook_clock_and_telegram(self):
        s = make_entry()
        self.assertEqual(s["minute"], 135)
        for key in ("mara", "vane", "vane_watch", "mara_notebook",
                    "platform_clock", "archive_telegram"):
            self.assertIn(key, s["entities"])
        self.assertEqual(s["entities"]["vane_watch"]["holder"], "vane")
        self.assertEqual(s["entities"]["archive_telegram"]["holder"], "mara")
        self.assertEqual(s["entities"]["platform_clock"]["holder"], None)

    def test_pilot_does_not_infer_arrival_from_a_record(self):
        s = make_entry()
        claim = s["facts"]["reported_arrival_0210"]["claim"]
        self.assertIn("not proof of physical arrival", claim)
        self.assertNotIn("train_41", s["entities"])  # no physical train asserted

    def test_deterministic_shadow_refuses_uncalibrated_semantic_result(self):
        result = deterministic_shadow(
            entry=make_entry(), prose="Vane glanced at his watch.",
            coverage={"status": "HOLD"},
            verdict={"next_action": "LOCAL_REPAIR_REQUIRED"},
            writer={"events": []},
        )
        self.assertEqual(result["status"], "HOLD_COVERAGE")
        self.assertIsNone(result["exit_state"])

    def test_unknown_time_never_committed_even_with_false_semantic_ok(self):
        result = deterministic_shadow(
            entry=make_entry(), prose="Vane checked the watch.",
            coverage={"status": "RECONCILED_PENDING_SEMANTIC"},
            verdict={
                "next_action": "PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW"
            },
            writer={"events": [
                {"type": "INTERACT_OBJECT", "at": None, "modality": "ASSERTED",
                 "arguments": {"object_id": "vane_watch", "actor_id": "vane",
                               "interaction": "LOOK_AT"},
                 "start": 0, "end": 22}
            ]},
        )
        self.assertEqual(result["status"], "HOLD_UNGROUNDED_TIME_OR_MODALITY")

    def test_models_and_stop_are_frozen(self):
        self.assertEqual(WRITER_MODEL, "openai/gpt-5.6-luna")
        self.assertEqual(EXTRACTOR_MODEL, "anthropic/claude-haiku-4.5")
        self.assertEqual(JEV_MODEL, "typesafe/jev-1.13")
        self.assertEqual(SPEND_STOP_USD, 0.35)


if __name__ == "__main__":
    unittest.main()
