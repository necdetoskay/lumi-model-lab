"""v0.43 offline dual-real-model source graph and risk classification tests.

These examples are local counterfactuals, never declared gold for Mara S1.
"""
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.scene_trace_dual_real_v043 import source_risks


class DualRealModelSceneTraceV043Tests(unittest.TestCase):
    def test_source_bound_static_watch_false_transition_flag(self):
        risks=source_risks(
            source_sentence=(
                "Teodor Vane stood beside the bench, his pocket "
                "watch open in his palm."
            ),
            model_event={"kind":"CHANGE_STATE"},
        )
        self.assertEqual(risks,[
            "STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK",
        ])
        self.assertEqual(source_risks(
            source_sentence="Teodor Vane opened his pocket watch.",
            model_event={"kind":"CHANGE_STATE"},
        ),[])
        self.assertEqual(source_risks(
            source_sentence=(
                "Teodor Vane stood beside the bench, his pocket "
                "watch open in his palm."
            ),
            model_event={"kind":"OBSERVE"},
        ),[])

    def test_real_pencil_source_warns_on_unattributed_motion_only(self):
        text="Vane watched the pencil move."
        self.assertEqual(source_risks(
            source_sentence=text,
            model_event={"kind":"MOVE"},
        ),["PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN"])
        self.assertEqual(source_risks(
            source_sentence=text,
            model_event={"kind":"OBSERVE"},
        ),[])
        self.assertEqual(source_risks(
            source_sentence="Mara moved the pencil.",
            model_event={"kind":"MOVE"},
        ),[])

    def test_source_risk_checks_are_never_physical_truth_approval(self):
        for kind in ("TRANSFER","CLAIM_MENTION","KNOWLEDGE_UPDATE","OBSERVE"):
            self.assertEqual(source_risks(
                source_sentence="Vane watched the pencil move.",
                model_event={"kind":kind},
            ),[])
        with self.assertRaisesRegex(
            CoverageError,"SCENETRACE_V043_RISK_INPUT_INVALID"
        ):
            source_risks(
                source_sentence="Vane watched the pencil move.",
                model_event={"kind":None},
            )


if __name__ == "__main__":
    unittest.main()
