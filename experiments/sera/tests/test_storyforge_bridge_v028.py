"""SERA v0.28 StoryForge contract adapter; zero real model charges."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.storyforge_bridge_v028 import run, prepare
from experiments.sera.tests.test_composed_ordered_facets_v027 import (
    SOURCE, SCENE, clock, relations, model,
)
from experiments.sera.tests.test_world_state_v02 import base

WORLD_ID = "synthetic-world:v028"
ROLES = {
    "writer": "synthetic/writer", "sweep": "synthetic/source",
    "semantic": "synthetic/semantic", "facet": "synthetic/facet",
}
PROFILES = {
    name: {
        "model_id": value, "provider": "openrouter",
        "match": {"type": "exact", "value": value},
        "qualification_ready": True,
        "profile_sha256": "a"*64,
        "runtime_contract_sha256": "b"*64,
        "production_policy_sha256": "c"*64,
    }
    for name,value in ROLES.items()
}
REGISTRY = {"vane": ["Vane"], "mara": ["Mara"],
            "vane_watch": ["watch"], "mara_notebook": ["notebook"]}
FACETS = {"openables": ["vane_watch"], "documents": ["mara_notebook"]}


def fake_request():
    return {
        "schema_version": "storyforge-request.v1",
        "profile_id": "LSF-A4-W500-v1.0-rc1",
        "request_id": "request-v028-1",
        "active_world_id": WORLD_ID,
        "always_required": [], "candidate_facts": [],
        "story_intent": {
            "family": "mystery", "opportunity": "observe clock",
            "references": {"required_fact_ids": [], "hard_guard_fact_ids": []},
        },
        "generation_profile": {"exact_age": 12,
                               "language_of_generation": "en"},
    }


def fake_result():
    return {
        "schema_version": "storyforge-result.v1",
        "profile_id": "LSF-A4-W500-v1.0-rc1",
        "request_id": "request-v028-1",
        "status": "publication_ready", "publication_ready": True,
        "context_packet": {"immutable": "original-registered-world"},
        "plan": {"beats": [{"id": "B1", "beat": "source scene"}]},
        "english_story": SOURCE,
        "turkish_story": "Türkçe çeviri",
        "proposed_story_outcome": {
            "proposed_state_changes": [{"kind": "object_state"}],
        },
        "evidence": {
            "story_gate": {"pass": True},
            "fidelity_gate": {"pass": True},
        },
    }


def world_scope(w=None):
    return {
        "active_world_id": WORLD_ID,
        "entry_world_sha256": digest(w or base()),
        "storyforge_request_id": "request-v028-1",
        "policy_version": "signed-external-snapshot-v1",
    }


def true_verifier(scope):
    # In production this callback MUST authenticate the app's signed
    # world/profile/registry snapshot. This is lab-only true attestation.
    return scope["policy_version"] == "signed-external-snapshot-v1"


def fake_attestor(name):
    for proof in PROFILES.values():
        if proof["model_id"] == name:
            return deepcopy(proof)
    raise CoverageError("UNKNOWN_MODEL")


def signed_grant():
    _, _, contract = prepare(
        request=fake_request(), result=fake_result(),
        world=base(), trusted_scope=world_scope(),
        verify_scope=true_verifier,
        models=deepcopy(ROLES), model_attestor=fake_attestor,
        scene_span={"start": 0, "end": len(SOURCE)},
        scene_key=SCENE, job_id="job-v028-scene-1",
    )
    return {
        "approved": True,
        "job_id": "job-v028-scene-1",
        "scene_key": SCENE,
        "request_sha256": contract["request_sha256"],
        "result_sha256": contract["result_sha256"],
        "world_sha256": contract["world_sha256"],
        "model_profile_sha256": contract["model_profile_sha256"],
        "budget_policy_id": "synthetic-preauthorized-small-budget-v1",
    }


def fake_grant_verifier(grant):
    return grant.get("budget_policy_id") == (
        "synthetic-preauthorized-small-budget-v1"
    )


def launch(root, **updates):
    options = {
        "request": fake_request(), "result": fake_result(),
        "world": base(), "trusted_scope": world_scope(),
        "verify_scope": true_verifier, "models": deepcopy(ROLES),
        "model_attestor": fake_attestor,
        "scene_span": {"start": 0, "end": len(SOURCE)},
        "scene_key": SCENE, "job_id": "job-v028-scene-1",
        "work_root": root, "registry": deepcopy(REGISTRY),
        "candidate_lexicon": {}, "typed_registry": deepcopy(FACETS),
        "trusted_temporal_builder": clock,
        "temporal_policy_id": "app-station-archive-v027",
        "trusted_relation_builder": relations,
        "relation_policy_id": "application-facts-v027",
        "max_rewrites": 0,
    }
    options.update(updates)
    return run(**options)


class StoryForgeBridgeV028Tests(unittest.TestCase):
    def test_dry_run_does_not_call_provider_and_is_not_canon_authority(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            def forbidden(**kwargs):
                self.fail("Dry-run must never call any paid provider")
            first = launch(root, provider_call=forbidden)
            again = launch(root, provider_call=forbidden)
            files = list(root.rglob("*.json"))
        self.assertEqual(first, again)
        self.assertEqual(first["status"],
                         "DRY_RUN_READY_NO_MODEL_CALLS_NONCANONICAL")
        self.assertEqual(first["provider_calls"], 0)
        self.assertEqual(first["model_cost_usd"], "0")
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertEqual(first["world_db_writes"], 0)
        self.assertEqual(len(files), 1)

    def test_actual_staged_v027_worker_consumes_storyforge_accepted_source(self):
        calls = []
        with TemporaryDirectory() as temp:
            root = Path(temp)
            before = deepcopy(base())
            first = launch(root, paid_authorized=True,
                           paid_grant=signed_grant(),
                           verify_paid_grant=fake_grant_verifier,
                           api_key="synthetic-not-a-real-key",
                           provider_call=model(calls))
            second = launch(root, paid_authorized=True,
                            paid_grant=signed_grant(),
                            verify_paid_grant=fake_grant_verifier,
                            api_key="synthetic-not-a-real-key",
                            provider_call=lambda **kw:self.fail(
                                "Already receipted model must not rebill"))
            evidence = list((root/"job-v028-scene-1").rglob(
                "*evidence/*.json"
            ))
        self.assertEqual(first, second)
        self.assertEqual(first["status"],
                         "SCENE_EVIDENCE_QUALIFIED_NONCANONICAL")
        self.assertEqual(first["scene_sha256"], prose_hash(SOURCE))
        self.assertEqual(first["sera_scene_result"]["rewrite_count"], 0)
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertFalse(first["sera_scene_result"]
                         ["canonical_commit_authorized"])
        self.assertEqual(before, base())
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(len(evidence), 1)

    def test_storyforge_editorial_ready_does_not_bypass_storyforge_gates(self):
        bad = fake_result()
        bad["evidence"]["story_gate"]["pass"] = False
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_UNVERIFIED_STORYFORGE_EDITORIAL_EVIDENCE"
            ):
                launch(Path(temp), result=bad)
        rejected = fake_result()
        rejected["publication_ready"] = False
        rejected["status"] = "story_rejected"
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_STORYFORGE_EDITORIAL_GATE_NOT_ACCEPTED"
            ):
                launch(Path(temp), result=rejected)

    def test_wrong_story_id_and_world_binding_cannot_share_receipts(self):
        bad = fake_result()
        bad["request_id"] = "another-story"
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_STORYFORGE_REQUEST_RESULT_MISMATCH"
            ):
                launch(Path(temp), result=bad)
        w = world_scope()
        w["active_world_id"] = "another-world"
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_TRUSTED_WORLD_SCOPE_NOT_VERIFIED"
            ):
                launch(Path(temp), trusted_scope=w)

    def test_untrusted_policy_and_unready_model_fail_before_billing(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_TRUSTED_WORLD_SCOPE_NOT_VERIFIED"
            ):
                launch(Path(temp), verify_scope=lambda _: False)
        def fake_profile(name):
            attestation = fake_attestor(name)
            attestation["match"]["type"] = "fallback"
            return attestation
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_UNQUALIFIED_OR_UNPINNED_MODEL_PROFILE"
            ):
                launch(Path(temp), model_attestor=fake_profile)

    def test_source_span_must_match_exact_english_master(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_SOURCE_SLICE_OUT_OF_BOUNDS"
            ):
                launch(Path(temp), scene_span={"start": 0, "end": 999999})
        story = fake_result()
        story["english_story"] = "Different story."
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_SOURCE_SLICE_OUT_OF_BOUNDS"
            ):
                launch(Path(temp), result=story)

    def test_source_and_profile_changes_are_rejected_in_existing_job(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            launch(root)
            updated=fake_result()
            updated["context_packet"]["immutable"] = "tampered packet"
            with self.assertRaisesRegex(
                CoverageError, "V028_IMMUTABLE_JOB_CONTRACT_CHANGED"
            ):
                launch(root, result=updated)
            different = deepcopy(ROLES)
            different["writer"] = "synthetic/new-writer"
            def qualified(name):
                obj = fake_attestor("synthetic/writer")
                obj["model_id"] = name
                return obj
            with self.assertRaisesRegex(
                CoverageError, "V028_IMMUTABLE_JOB_CONTRACT_CHANGED"
            ):
                launch(root, models=different, model_attestor=qualified)

    def test_real_provider_never_called_when_paid_unauthorized(self):
        with TemporaryDirectory() as temp:
            output=launch(
                Path(temp),
                api_key="any-value-but-no-paid-consent",
                paid_authorized=False,
                provider_call=lambda **kwargs: self.fail(
                    "Unauthorized provider call"),
            )
        self.assertEqual(output["provider_calls"],0)
        self.assertEqual(output["status"],
                         "DRY_RUN_READY_NO_MODEL_CALLS_NONCANONICAL")

    def test_paid_flag_without_app_signed_scope_cannot_spend(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError,
                "V028_PAID_GRANT_NOT_AUTHENTICATED_OR_SCOPE_MISMATCH"
            ):
                launch(Path(temp), paid_authorized=True,
                       api_key="anything",
                       provider_call=lambda **kw:self.fail("must not bill"))
        wrong = signed_grant()
        wrong["world_sha256"] = "f"*64
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError,
                "V028_PAID_GRANT_NOT_AUTHENTICATED_OR_SCOPE_MISMATCH"
            ):
                launch(Path(temp), paid_authorized=True, paid_grant=wrong,
                       verify_paid_grant=fake_grant_verifier,
                       api_key="anything",
                       provider_call=lambda **kw:self.fail("must not bill"))
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError,
                "V028_PAID_GRANT_NOT_AUTHENTICATED_OR_SCOPE_MISMATCH"
            ):
                launch(Path(temp), paid_authorized=True,
                       paid_grant=signed_grant(),
                       verify_paid_grant=lambda g: False,
                       api_key="anything",
                       provider_call=lambda **kw:self.fail("must not bill"))

    def test_cannot_trigger_payment_without_provider_or_key(self):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_PAID_PROVIDER_NOT_CONFIGURED"
            ):
                launch(Path(temp), paid_authorized=True,
                       paid_grant=signed_grant(),
                       verify_paid_grant=fake_grant_verifier)
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(
                CoverageError, "V028_PAID_PROVIDER_NOT_CONFIGURED"
            ):
                launch(Path(temp), paid_authorized=True,
                       paid_grant=signed_grant(),
                       verify_paid_grant=fake_grant_verifier,
                       api_key="fake",provider_call=None)


if __name__ == "__main__":
    unittest.main()
