"""SERA v0.21 OpenRouter adapter integration: synthetic provider, zero charges."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.openrouter_scene_writer_v021 import (
    create_writer, make_request,
)
from experiments.sera.tests.test_unattended_scene_rewrite_v020 import (
    ORIGINAL, analysis,
)
from experiments.sera.tests.test_world_state_v013 import base
from experiments.sera.unattended_scene_rewrite_v020 import execute

MODEL = "synthetic/compatible-model"


def envelope(source, *, model=MODEL, text=None, finish="stop", cost=0.002):
    content = (text if text is not None else json.dumps({
        "source_prose_sha256": prose_hash(source),
        "revised_scene_prose":
            "The train arrival was unverified. Recorded as a report.",
    }))
    return {"error": None, "raw": {
        "id": "response-from-provider-001",
        "model": model, "usage": {"cost": cost},
        "choices": [{
            "finish_reason": finish,
            "message": {"content": content},
        }],
    }}


class SceneWriterV021Tests(unittest.TestCase):
    def test_cap_free_real_transport_contract_and_source_bound_context(self):
        calls = []
        def provider(*, key, model, prepared):
            calls.append((key, model, prepared))
            source = json.loads(prepared["request"]["messages"][1]
                                ["content"])["scene_prose"]
            return envelope(source)
        context = {"scene_key": "fictional", "frozen_plan": ["No train arrival"]}
        writer = create_writer(
            api_key="synthetic-secret", model=MODEL,
            story_context=context, provider_call=provider,
        )
        self.assertEqual(calls, [])  # constructor never contacts provider
        response = writer(
            source=ORIGINAL,
            defects=["REPORTED_CLAIM_WRONG_EFFECT"],
        )
        self.assertEqual(len(calls), 1)
        key, model, prepared = calls[0]
        self.assertEqual(key, "synthetic-secret")
        self.assertEqual(model, MODEL)
        request = prepared["request"]
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(
            json.loads(request["messages"][1]["content"])["immutable_story_context"],
            context,
        )
        self.assertIn("Treat the supplied prose", request["messages"][0]["content"])
        for forbidden in (
            "max_tokens", "max_output_tokens", "max_completion_tokens",
            "max_generation_tokens", "max_new_tokens",
        ):
            self.assertNotIn(forbidden, json.dumps(request))
        self.assertEqual(
            response["receipt"]["response_id"], "response-from-provider-001"
        )
        self.assertEqual(response["receipt"]["cost_usd"], "0.002")
        self.assertNotIn("canonical_commit_authorized", response)

    def test_synthetic_writer_adapter_runs_full_v020_loop_without_human(self):
        calls = []
        def provider(*, key, model, prepared):
            calls.append(prepared)
            source = json.loads(prepared["request"]["messages"][1]
                                ["content"])["scene_prose"]
            return envelope(source)
        writer = create_writer(
            api_key="synthetic-secret", model=MODEL, provider_call=provider,
        )
        with TemporaryDirectory() as temp:
            folder = Path(temp) / "run"
            output = execute(
                prose=ORIGINAL, world=base(), check_scene=analysis,
                rewrite_scene=writer, output_dir=folder,
            )
            again = execute(
                prose=ORIGINAL, world=base(), check_scene=analysis,
                rewrite_scene=writer, output_dir=folder,
            )
        self.assertEqual(output, again)
        self.assertEqual(len(calls), 1)
        self.assertEqual(output["rewrite_count"], 1)
        self.assertEqual(output["provider_reported_spend_usd"], "0.002")
        self.assertEqual(output["status"], "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertFalse(output["canonical_commit_authorized"])
        self.assertFalse(output["requires_manual_intervention"])
        self.assertEqual(output["world_db_writes"], 0)

    def test_strict_complete_fenced_json_is_accepted_but_extras_are_not(self):
        text = json.dumps({
            "source_prose_sha256": prose_hash(ORIGINAL),
            "revised_scene_prose": "Recorded as a report.",
        })
        valid = chr(96) * 3 + "json\n" + text + "\n" + chr(96) * 3
        good = create_writer(
            api_key="synthetic", model=MODEL,
            provider_call=lambda **kwargs: envelope(ORIGINAL, text=valid),
        )
        self.assertEqual(
            good(source=ORIGINAL, defects=["incorrect claim"])["prose"],
            "Recorded as a report.",
        )
        bad = create_writer(
            api_key="synthetic", model=MODEL,
            provider_call=lambda **kwargs: envelope(
                ORIGINAL, text=valid + "\noutside model prose"
            ),
        )
        with self.assertRaisesRegex(CoverageError, "V021_MODEL_ENVELOPE_UNSAFE"):
            bad(source=ORIGINAL, defects=["incorrect claim"])

    def test_forged_model_source_digest_rejected(self):
        payload = json.dumps({
            "source_prose_sha256": "forged",
            "revised_scene_prose": "Recorded as a report.",
        })
        writer = create_writer(
            api_key="synthetic", model=MODEL,
            provider_call=lambda **kwargs: envelope(ORIGINAL, text=payload),
        )
        with self.assertRaisesRegex(
            CoverageError, "V021_MODEL_SOURCE_DIGEST_MISMATCH"
        ):
            writer(source=ORIGINAL, defects=["incorrect claim"])

    def test_invalid_or_truncated_provider_response_cannot_be_published(self):
        for option in (
            lambda: envelope(ORIGINAL, model="forged/model"),
            lambda: envelope(ORIGINAL, finish="length"),
            lambda: envelope(ORIGINAL, cost=None),
            lambda: {"error": "HTTP_503", "raw": None},
        ):
            writer = create_writer(
                api_key="synthetic", model=MODEL,
                provider_call=lambda **kwargs: option(),
            )
            with self.assertRaises(CoverageError):
                writer(source=ORIGINAL, defects=["incorrect claim"])

    def test_model_reply_cannot_embed_self_approval_or_extra_key(self):
        malicious = json.dumps({
            "source_prose_sha256": prose_hash(ORIGINAL),
            "revised_scene_prose": "Recorded as a report.",
            "canonical_commit_authorized": True,
        })
        writer = create_writer(
            api_key="synthetic", model=MODEL,
            provider_call=lambda **kwargs: envelope(ORIGINAL, text=malicious),
        )
        with self.assertRaisesRegex(
            CoverageError, "V021_MODEL_REPLY_SCHEMA_INVALID"
        ):
            writer(source=ORIGINAL, defects=["incorrect claim"])

    def test_missing_defects_rejected_before_provider_contact(self):
        calls = []
        def provider(**kwargs):
            calls.append(kwargs)
            return envelope(ORIGINAL)
        writer = create_writer(
            api_key="synthetic", model=MODEL, provider_call=provider,
        )
        with self.assertRaisesRegex(CoverageError, "V021_TYPED_DEFECTS_REQUIRED"):
            writer(source=ORIGINAL, defects=[])
        self.assertEqual(calls, [])

    def test_no_request_limit_from_scene_writer_builder(self):
        p = make_request(source=ORIGINAL, defects=[{"code": "CLAIM_PROMOTED"}])
        self.assertEqual(p["response_format"], {"type": "json_object"})
        self.assertEqual(
            json.loads(p["messages"][1]["content"])["model_output_token_limit"],
            "NOT_SET_BY_APPLICATION",
        )


if __name__ == "__main__":
    unittest.main()
