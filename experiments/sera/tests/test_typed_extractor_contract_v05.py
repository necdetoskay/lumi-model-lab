"""SERA M3.5 offline typed extraction protocol regression tests."""
from __future__ import annotations

from copy import deepcopy
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.typed_extractor_contract_v05 import (
    MAPPINGS, SUPPORTED, bind_typed_response, make_typed_request,
    typed_json_schema, validate_raw_typed,
)
from experiments.sera.tests.test_world_state_v02 import base

SCENE = "hook_empty_platform"
PROSE = "Vane examined his pocket watch."
REGISTRY = {"vane": ["Vane"], "vane_watch": ["pocket watch"]}


def raw_event(*, typ="INTERACT_OBJECT", args=None, minute=None,
              modality="ASSERTED", quote=PROSE):
    if args is None:
        args = {"actor_id": "vane", "object_id": "vane_watch",
                "interaction": "EXAMINE"}
    return {
        "type": typ, "arguments": args, "at": minute,
        "modality": modality, "evidence_quote": quote,
        "occurrence": 0,
    }


def payload(event=None):
    return {
        "mentions": [
            {"entity_ref": "vane", "role": "PRESENT",
             "evidence_quote": "Vane", "occurrence": 0},
            {"entity_ref": "vane_watch", "role": "INTERACTED",
             "evidence_quote": "pocket watch", "occurrence": 0},
        ],
        "events": [event if event is not None else raw_event()],
    }


class TypedExtractorProtocolTests(unittest.TestCase):
    def test_schema_discriminates_every_operation_with_required_arguments(self):
        schema = typed_json_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), {"mentions", "events"})
        variants = schema["properties"]["events"]["items"]["oneOf"]
        self.assertEqual(len(variants), len(SUPPORTED))
        self.assertEqual(
            {v["properties"]["type"]["enum"][0] for v in variants},
            set(SUPPORTED),
        )
        for v in variants:
            args = v["properties"]["arguments"]
            self.assertTrue(args["required"])
            self.assertFalse(args["additionalProperties"])
        assert "TELL_FACT" in MAPPINGS

    def test_blind_request_contains_no_writer_or_model_self_judgment(self):
        request = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertFalse(request["commit_authorized"])
        self.assertEqual(request["entry_revision"], 0)
        content = request["messages"][1]["content"]
        self.assertIn("pocket watch", content)
        self.assertNotIn("writer_report", content)
        self.assertNotIn("jev_verdict", content)
        self.assertIn('"declared_claim_ids":[]', content)

    def test_full_output_bound_by_exact_quotes_and_state(self):
        req = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        out = bind_typed_response(
            raw=payload(), request=req, prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        self.assertEqual(out["source_role"], "INDEPENDENT")
        self.assertEqual(out["status"], "HOLD")
        self.assertEqual(out["normalized_events"][0]["world_type"],
                         "INTERACT_ENTITY")
        self.assertEqual(out["normalized_events"][0]["time"]["exact_minute"],
                         None)
        self.assertEqual(
            out["normalized_events"][0]["blockers"],
            ["EVENT_V04_RELATIVE_TIME_UNRESOLVED"],
        )
        self.assertFalse(out["commit_authorized"])

    def test_empty_arguments_rejected_before_normalizer(self):
        with self.assertRaisesRegex(CoverageError,
                                    "V05_EVENT_ARGUMENTS_INVALID"):
            validate_raw_typed(payload(raw_event(args={})))

    def test_each_operation_requires_exact_model_keys(self):
        for kind, (fields, _) in MAPPINGS.items():
            with self.subTest(kind=kind):
                incomplete = {name: "dummy" for name in fields}
                incomplete.pop(next(iter(fields)))
                with self.assertRaisesRegex(CoverageError,
                                            "V05_EVENT_ARGUMENTS_INVALID"):
                    validate_raw_typed(payload(raw_event(
                        typ=kind, args=incomplete,
                    )))
                extras = {name: "dummy" for name in fields}
                extras["undeclared"] = "x"
                with self.assertRaisesRegex(CoverageError,
                                            "V05_EVENT_ARGUMENTS_INVALID"):
                    validate_raw_typed(payload(raw_event(
                        typ=kind, args=extras,
                    )))

    def test_unknown_physical_action_is_explicit_unmapped_holding(self):
        raw = payload(raw_event(
            typ="UNMAPPED_STATE_CHANGE",
            args={"description": "Watch case closed",
                  "kind_hint": "object_case_state"},
        ))
        req = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        out = bind_typed_response(
            raw=raw, request=req, prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        self.assertEqual(out["status"], "HOLD")
        self.assertIn("EVENT_V04_UNSUPPORTED:UNMAPPED_STATE_CHANGE",
                      out["normalized_events"][0]["blockers"])

    def test_unmapped_empty_description_rejected(self):
        raw = payload(raw_event(
            typ="UNMAPPED_STATE_CHANGE",
            args={"description": "", "kind_hint": "case"},
        ))
        with self.assertRaisesRegex(CoverageError,
                                    "V05_EVENT_ARGUMENT_VALUE_INVALID"):
            validate_raw_typed(raw)

    def test_fabricated_time_claim_not_added_by_contract(self):
        req = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        self.assertIn("NEVER guess a clock", req["messages"][0]["content"])
        out = bind_typed_response(
            raw=payload(), request=req, prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        self.assertIsNone(out["report"]["events"][0]["at"])

    def test_tampered_request_prose_hash_rejected(self):
        request = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        request["prose_sha256"] = "x" * 64
        with self.assertRaisesRegex(CoverageError,
                                    "V05_REQUEST_BINDING_MISMATCH"):
            bind_typed_response(
                raw=payload(), request=request, prose=PROSE,
                scene_key=SCENE, entry=base(),
            )

    def test_bad_quote_occurrence_fails_closed(self):
        request = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        data = payload()
        data["events"][0]["evidence_quote"] = "nonexistent event"
        with self.assertRaisesRegex(CoverageError,
                                    "EXTRACTOR_QUOTE_NOT_FOUND"):
            bind_typed_response(
                raw=data, request=request, prose=PROSE,
                scene_key=SCENE, entry=base(),
            )

    def test_invalid_time_bool_and_extra_output_fields(self):
        data = payload(raw_event(minute=True))
        with self.assertRaisesRegex(CoverageError, "V05_EVENT_TIME_INVALID"):
            validate_raw_typed(data)
        data = payload()
        data["world_state"] = {"mara": {"knowledge": ["whatever"]}}
        with self.assertRaisesRegex(CoverageError, "V05_RAW_SCHEMA_INVALID"):
            validate_raw_typed(data)

    def test_reported_claim_never_promoted_by_schema(self):
        data = payload(raw_event(
            typ="LEARN_FACT",
            args={"character_id": "vane",
                  "fact_id": "train_41_physically_arrived"},
        ))
        req = make_typed_request(
            prose=PROSE, scene_key=SCENE, entry=base(), registry=REGISTRY,
        )
        out = bind_typed_response(
            raw=data, request=req, prose=PROSE,
            scene_key=SCENE, entry=base(),
        )
        self.assertIn("EVENT_V04_UNATTRIBUTED_FACT",
                      out["normalized_events"][0]["blockers"])


if __name__ == "__main__":
    unittest.main()
