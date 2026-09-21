import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from src.saga_blueprint_generate import (
    ProviderError,
    build_experiment_fingerprint,
    load_runner_config,
    run_generation,
)
from src.saga_blueprint_contract import (
    load_fixture_manifest,
    load_profile,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "configs" / "saga_lab" / "narrative_architect_fixture_v1.yaml"
OPENROUTER_CONFIG = ROOT / "configs" / "saga_lab" / "narrative_architect_openrouter_v1.yaml"
FIXTURE_ID = "mature_adult_dormant_archivist"


def _temp_config(
    root: Path,
    source: Path,
    *,
    output_root: Path,
    mutate=None,
) -> Path:
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["profile_path"] = str(ROOT / payload["profile_path"])
    payload["fixture_manifest_path"] = str(ROOT / payload["fixture_manifest_path"])
    payload["prompt_path"] = str(ROOT / payload["prompt_path"])
    if payload["provider"].get("fixture_response_path"):
        payload["provider"]["fixture_response_path"] = str(
            ROOT / payload["provider"]["fixture_response_path"]
        )
    payload["output_root"] = str(output_root)
    if mutate:
        mutate(payload)
    path = root / "runner.yaml"
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


class SagaBlueprintGenerateTests(unittest.TestCase):
    def test_fixture_provider_persists_complete_evidence_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(
                root,
                BASE_CONFIG,
                output_root=root / "runs",
            )
            result = run_generation(
                config_path=config,
                fixture_id=FIXTURE_ID,
            )
            self.assertEqual(result["status"], "complete")
            run_dir = Path(result["run_dir"])
            expected = {
                "input_fixture.json",
                "system_prompt.txt",
                "user_prompt.txt",
                "request_config.json",
                "provider_request.json",
                "raw_response.json",
                "raw_content.txt",
                "parsed_blueprint.json",
                "validated_blueprint.json",
                "validation.json",
                "manifest.json",
            }
            self.assertTrue(expected.issubset({p.name for p in run_dir.iterdir()}))
            manifest = json.loads(
                (run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["validation"]["status"], "pass")
            self.assertEqual(manifest["usage"]["cost_usd"], 0.0)
            self.assertIsNotNone(manifest["latency_ms"])
            self.assertEqual(manifest["attempts"], 1)

    def test_exact_duplicate_is_blocked_and_rerun_is_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(root, BASE_CONFIG, output_root=root / "runs")
            first = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            second = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            third = run_generation(
                config_path=config,
                fixture_id=FIXTURE_ID,
                rerun=True,
            )
            self.assertEqual(first["status"], "complete")
            self.assertEqual(second["status"], "ALREADY_EXISTS")
            self.assertEqual(second["run_dir"], first["run_dir"])
            self.assertEqual(third["status"], "complete")
            self.assertNotEqual(third["run_dir"], first["run_dir"])
            self.assertIn("__rerun_", third["run_dir"])

    @patch("src.saga_blueprint_generate._fixture_provider")
    def test_malformed_json_fails_closed_and_raw_content_is_preserved(
        self,
        provider,
    ) -> None:
        provider.return_value = (
            {
                "id": "bad-json",
                "model": "fixture/narrative-architect-reference-v1",
                "provider": "local-fixture",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "{ not-valid-json"},
                    }
                ],
                "usage": {"cost": 0.0},
            },
            {"fixture": True},
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(root, BASE_CONFIG, output_root=root / "runs")
            result = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            self.assertEqual(result["status"], "parse_failed")
            run_dir = Path(result["run_dir"])
            self.assertEqual(
                (run_dir / "raw_content.txt").read_text(encoding="utf-8").strip(),
                "{ not-valid-json",
            )
            self.assertTrue((run_dir / "raw_response.json").exists())
            self.assertFalse((run_dir / "validated_blueprint.json").exists())


    @patch("src.saga_blueprint_generate._fixture_provider")
    def test_non_stop_finish_reason_fails_closed_before_parse(self, provider) -> None:
        provider.return_value = (
            {
                "id": "truncated",
                "model": "fixture/narrative-architect-reference-v1",
                "provider": "local-fixture",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": json.dumps(
                                json.loads(
                                    (
                                        ROOT
                                        / "data"
                                        / "specifications"
                                        / "saga_lab"
                                        / "narrative_architect_fixture_response_v1.json"
                                    ).read_text(encoding="utf-8")
                                )["blueprint"]
                            )
                        },
                    }
                ],
                "usage": {"cost": 0.0},
            },
            {"fixture": True},
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(root, BASE_CONFIG, output_root=root / "runs")
            result = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            self.assertEqual(result["status"], "generation_incomplete")
            run_dir = Path(result["run_dir"])
            self.assertTrue((run_dir / "raw_response.json").exists())
            self.assertTrue((run_dir / "validation.json").exists())
            self.assertFalse((run_dir / "parsed_blueprint.json").exists())

    @patch("src.saga_blueprint_generate._fixture_provider")
    def test_schema_invalid_json_is_validation_failure_not_provider_failure(
        self,
        provider,
    ) -> None:
        provider.return_value = (
            {
                "id": "bad-schema",
                "model": "fixture/narrative-architect-reference-v1",
                "provider": "local-fixture",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "schema": "character-narrative-blueprint.v1",
                                    "future_story_plan": ["story_1", "story_2"],
                                }
                            )
                        },
                    }
                ],
                "usage": {"cost": 0.0},
            },
            {"fixture": True},
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(root, BASE_CONFIG, output_root=root / "runs")
            result = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            self.assertEqual(result["status"], "validation_failed")
            run_dir = Path(result["run_dir"])
            self.assertTrue((run_dir / "parsed_blueprint.json").exists())
            self.assertTrue((run_dir / "validation.json").exists())
            self.assertFalse((run_dir / "validated_blueprint.json").exists())

    def test_missing_openrouter_key_is_provider_error_without_network_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(
                root,
                OPENROUTER_CONFIG,
                output_root=root / "runs",
            )
            with patch.dict(os.environ, {}, clear=True):
                with patch(
                    "src.saga_blueprint_generate._call_openrouter"
                ) as call:
                    result = run_generation(
                        config_path=config,
                        fixture_id=FIXTURE_ID,
                        model_override="provider/strong-model",
                    )
            self.assertEqual(result["status"], "provider_error")
            self.assertIn("OPENROUTER_API_KEY", result["provider_error"]["message"])
            call.assert_not_called()

    @patch("src.saga_blueprint_generate._call_openrouter")
    def test_api_key_is_used_but_never_written_to_artifacts(self, call) -> None:
        fixture_response = json.loads(
            (
                ROOT
                / "data"
                / "specifications"
                / "saga_lab"
                / "narrative_architect_fixture_response_v1.json"
            ).read_text(encoding="utf-8")
        )
        body = {
            "id": "mock-paid-response",
            "model": "provider/strong-model",
            "provider": "mock-provider",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            fixture_response["blueprint"],
                            ensure_ascii=False,
                        )
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
                "cost": 0.0123,
            },
        }
        call.return_value = (
            body,
            {
                "model": "provider/strong-model",
                "temperature": 0.35,
                "max_tokens": 16000,
            },
            1,
        )
        secret = "sk-test-SAGA-SECRET-MUST-NOT-LEAK"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(
                root,
                OPENROUTER_CONFIG,
                output_root=root / "runs",
            )
            with patch.dict(
                os.environ,
                {"OPENROUTER_API_KEY": secret, "USD_TRY_RATE": "50"},
                clear=False,
            ):
                result = run_generation(
                    config_path=config,
                    fixture_id=FIXTURE_ID,
                    model_override="provider/strong-model",
                )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(call.call_args.kwargs["api_key"], secret)
            run_dir = Path(result["run_dir"])
            all_text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in run_dir.rglob("*")
                if path.is_file()
            )
            self.assertNotIn(secret, all_text)
            manifest = json.loads(
                (run_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["usage"]["input_tokens"], 100)
            self.assertEqual(manifest["usage"]["output_tokens"], 200)
            self.assertEqual(manifest["usage"]["total_tokens"], 300)
            self.assertEqual(manifest["usage"]["cost_usd"], 0.0123)
            self.assertEqual(manifest["usage"]["cost_try"], 0.615)


    @patch("src.saga_blueprint_generate._fixture_provider")
    def test_strict_valid_but_static_invalid_blueprint_is_not_complete(
        self,
        provider,
    ) -> None:
        fixture_response = json.loads(
            (
                ROOT
                / "data"
                / "specifications"
                / "saga_lab"
                / "narrative_architect_fixture_response_v1.json"
            ).read_text(encoding="utf-8")
        )
        blueprint = fixture_response["blueprint"]
        blueprint["saga_blueprint"]["threads"][0]["milestones"][0]["required"] = True
        provider.return_value = (
            {
                "id": "static-invalid",
                "model": "fixture/narrative-architect-reference-v1",
                "provider": "local-fixture",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(blueprint, ensure_ascii=False)
                        },
                    }
                ],
                "usage": {"cost": 0.0},
            },
            {"fixture": True},
            1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = _temp_config(root, BASE_CONFIG, output_root=root / "runs")
            result = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            self.assertEqual(result["status"], "static_validation_failed")
            run_dir = Path(result["run_dir"])
            self.assertTrue((run_dir / "validated_blueprint.json").exists())
            self.assertTrue((run_dir / "static_validation.json").exists())
            static_report = json.loads(
                (run_dir / "static_validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(static_report["status"], "FAIL")
            self.assertFalse(static_report["semantic_evaluation_eligible"])
            self.assertIn(
                "MANDATORY_MILESTONE",
                {item["code"] for item in static_report["findings"]},
            )

    def test_fingerprint_changes_with_request_options(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a_path = _temp_config(root, BASE_CONFIG, output_root=root / "a")
            a_config = load_runner_config(a_path)
            profile = load_profile(Path(a_config.profile_path))
            fixtures = load_fixture_manifest(Path(a_config.fixture_manifest_path))
            fixture = next(x for x in fixtures.cases if x.case_id == FIXTURE_ID)
            a_fingerprint, _ = build_experiment_fingerprint(
                config_path=a_path,
                config=a_config,
                profile=profile,
                fixture=fixture,
                model="fixture/narrative-architect-reference-v1",
            )

            b_root = root / "bconfig"
            b_root.mkdir()
            b_path = _temp_config(
                b_root,
                BASE_CONFIG,
                output_root=root / "b",
                mutate=lambda payload: payload["request"].update(
                    {"temperature": 0.7}
                ),
            )
            b_config = load_runner_config(b_path)
            b_fingerprint, _ = build_experiment_fingerprint(
                config_path=b_path,
                config=b_config,
                profile=profile,
                fixture=fixture,
                model="fixture/narrative-architect-reference-v1",
            )
            self.assertNotEqual(a_fingerprint, b_fingerprint)


    def test_output_root_change_does_not_change_experiment_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a_dir = root / "a_cfg"
            b_dir = root / "b_cfg"
            a_dir.mkdir()
            b_dir.mkdir()
            a_path = _temp_config(a_dir, BASE_CONFIG, output_root=root / "runs_a")
            b_path = _temp_config(b_dir, BASE_CONFIG, output_root=root / "runs_b")

            a_config = load_runner_config(a_path)
            b_config = load_runner_config(b_path)
            profile = load_profile(Path(a_config.profile_path))
            fixtures = load_fixture_manifest(Path(a_config.fixture_manifest_path))
            fixture = next(x for x in fixtures.cases if x.case_id == FIXTURE_ID)

            a_fingerprint, _ = build_experiment_fingerprint(
                config_path=a_path,
                config=a_config,
                profile=profile,
                fixture=fixture,
                model="fixture/narrative-architect-reference-v1",
            )
            b_fingerprint, _ = build_experiment_fingerprint(
                config_path=b_path,
                config=b_config,
                profile=profile,
                fixture=fixture,
                model="fixture/narrative-architect-reference-v1",
            )
            self.assertEqual(a_fingerprint, b_fingerprint)

    def test_fixture_identity_mismatch_is_provider_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrong_response = root / "wrong.json"
            source = json.loads(
                (
                    ROOT
                    / "data"
                    / "specifications"
                    / "saga_lab"
                    / "narrative_architect_fixture_response_v1.json"
                ).read_text(encoding="utf-8")
            )
            source["fixture_id"] = "young_child_forest_explorer"
            wrong_response.write_text(
                json.dumps(source),
                encoding="utf-8",
            )

            config = _temp_config(
                root,
                BASE_CONFIG,
                output_root=root / "runs",
                mutate=lambda payload: payload["provider"].update(
                    {"fixture_response_path": str(wrong_response)}
                ),
            )
            result = run_generation(config_path=config, fixture_id=FIXTURE_ID)
            self.assertEqual(result["status"], "provider_error")
            self.assertIn("not 'mature_adult_dormant_archivist'", result["provider_error"]["message"])


if __name__ == "__main__":
    unittest.main()
