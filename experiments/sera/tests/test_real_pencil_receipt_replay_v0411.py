"""v0.41.1 — model outputs never self-authorize physical identities/actions."""
import unittest
from copy import deepcopy

from experiments.sera.coverage import CoverageError
from experiments.sera.real_pencil_receipt_replay_v0411 import (
    normalize_only_safe_advisory_fields,
)


def example():
    return {"rows":[{
        "sentence_id":"s022",
        "mentions":[{
            "entity_ref":"new:pencil","role":"PRESENT",
            "evidence_quote":"pencil","occurrence":0,
            "reason":"optional explanatory text not in strict protocol",
        }],
        "events":[{
            "kind":"MOVE","epistemic":"OBSERVED_ACTION",
            "effect":"OBJECT","evidence_quote":"pencil move",
            "occurrence":0,"entity_refs":["new:pencil"],
            "reason":"motion described but no actor proven",
        }],
    }]}


class RealPencilReceiptReplayV0411Tests(unittest.TestCase):
    def test_nonsemantic_extra_mention_reason_removed_without_changing_original(self):
        original=example()
        preserved=deepcopy(original)
        normalized,repairs=normalize_only_safe_advisory_fields(original)
        self.assertEqual(original,preserved)
        self.assertEqual(len(repairs),1)
        self.assertEqual(repairs[0]["entity_ref"],"new:pencil")
        self.assertNotIn("reason",normalized["rows"][0]["mentions"][0])
        self.assertEqual(normalized["rows"][0]["events"],
                         preserved["rows"][0]["events"])
        self.assertEqual(normalized["rows"][0]["mentions"][0]["evidence_quote"],
                         "pencil")
        self.assertEqual(normalized["rows"][0]["mentions"][0]["role"],
                         "PRESENT")

    def test_unsafe_field_not_silently_stripped(self):
        original=example()
        original["rows"][0]["mentions"][0]["owner_id"]="mara"
        with self.assertRaisesRegex(
            CoverageError,"V0411_UNSAFE_EXTRA_MENTION_FIELD"
        ):
            normalize_only_safe_advisory_fields(original)

    def test_model_event_semantic_fields_never_edited(self):
        original=example()
        original["rows"][0]["events"][0]["actor_id"]="vane"
        normalized,_=normalize_only_safe_advisory_fields(original)
        self.assertEqual(normalized["rows"][0]["events"],
                         original["rows"][0]["events"])
        # Exact v0.10 binder must reject that illegal event field later;
        # this safe envelope repair never strips or accepts it.


if __name__=="__main__":
    unittest.main()
