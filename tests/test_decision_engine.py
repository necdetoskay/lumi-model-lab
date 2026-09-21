import json
import tempfile
import unittest
from pathlib import Path

import yaml

from src.decision_engine import (
    DecisionAnswer,
    DecisionCase,
    DecisionEngineIdentity,
    DecisionEngineMalformedOutput,
    DecisionEngineOutput,
    DecisionQuestion,
    DecisionWorkloadProfile,
    validate_output,
)
from src.decision_engine_runner import experiment_fingerprint, run_experiment


class DecisionEngineTests(unittest.TestCase):
    def test_rejects_choice_outside_allowlist(self) -> None:
        workload = DecisionWorkloadProfile(
            profile_id="x1",
            profile_version="1",
            input_schema_version="1",
            question_set_version="1",
            risk_class="L2",
            abstention_options=["ESCALATE"],
        )
        case = DecisionCase(
            case_id="c1",
            state={},
            questions=[
                DecisionQuestion(
                    question_id="next",
                    type="choice",
                    instructions="Pick one",
                    choices=["CONTINUE", "ESCALATE"],
                )
            ],
        )
        output = DecisionEngineOutput(
            answers=[
                DecisionAnswer(
                    question_id="next",
                    type="choice",
                    value="DELETE_DATABASE",
                )
            ]
        )
        with self.assertRaises(DecisionEngineMalformedOutput):
            validate_output(workload=workload, case=case, output=output)


    def test_boolean_requires_native_probability_true(self) -> None:
        workload = DecisionWorkloadProfile(
            profile_id="x1",
            profile_version="1",
            input_schema_version="1",
            question_set_version="1",
            risk_class="L2",
        )
        case = DecisionCase(
            case_id="c-bool",
            state={},
            questions=[
                DecisionQuestion(
                    question_id="safe",
                    type="boolean",
                    instructions="Is the action safe?",
                )
            ],
        )
        output = DecisionEngineOutput(
            answers=[
                DecisionAnswer(
                    question_id="safe",
                    type="boolean",
                    value=True,
                )
            ]
        )
        with self.assertRaises(DecisionEngineMalformedOutput):
            validate_output(workload=workload, case=case, output=output)

    def test_score_requires_explicit_levels(self) -> None:
        workload = DecisionWorkloadProfile(
            profile_id="judge",
            profile_version="1",
            input_schema_version="1",
            question_set_version="1",
            risk_class="L2",
        )
        case = DecisionCase(
            case_id="c-score",
            state={},
            questions=[
                DecisionQuestion(
                    question_id="quality",
                    type="score",
                    instructions="Score quality",
                    score_min=0,
                    score_max=2,
                )
            ],
        )
        output = DecisionEngineOutput(
            answers=[
                DecisionAnswer(
                    question_id="quality",
                    type="score",
                    value=1.0,
                )
            ]
        )
        with self.assertRaises(DecisionEngineMalformedOutput):
            validate_output(workload=workload, case=case, output=output)

    def test_fingerprint_changes_with_engine_identity(self) -> None:
        workload = DecisionWorkloadProfile(
            profile_id="x1",
            profile_version="1",
            input_schema_version="1",
            question_set_version="1",
            risk_class="L2",
        )
        a = DecisionEngineIdentity(
            engine_family="fixture",
            provider_runtime="local",
            model_id="a",
        )
        b = DecisionEngineIdentity(
            engine_family="fixture",
            provider_runtime="local",
            model_id="b",
        )
        self.assertNotEqual(
            experiment_fingerprint(
                workload=workload,
                dataset_sha256="0" * 64,
                engine_identity=a,
            ),
            experiment_fingerprint(
                workload=workload,
                dataset_sha256="0" * 64,
                engine_identity=b,
            ),
        )

    def test_runner_refuses_silent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_path = root / "dataset.json"
            fixture_path = root / "fixture.json"
            config_path = root / "config.yaml"
            output_root = root / "runs"

            dataset_path.write_text(
                json.dumps(
                    {
                        "dataset_id": "d",
                        "dataset_version": "1",
                        "cases": [
                            {
                                "case_id": "c1",
                                "state": {"x": 1},
                                "questions": [
                                    {
                                        "question_id": "next",
                                        "type": "choice",
                                        "instructions": "Pick",
                                        "choices": ["CONTINUE", "ESCALATE"],
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fixture_path.write_text(
                json.dumps(
                    {
                        "outputs": {
                            "c1": {
                                "answers": [
                                    {
                                        "question_id": "next",
                                        "type": "choice",
                                        "value": "CONTINUE",
                                        "confidence": 0.9,
                                    }
                                ],
                                "raw_output": {"next": "CONTINUE"},
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "workload_profile": {
                            "profile_id": "x1",
                            "profile_version": "1",
                            "input_schema_version": "1",
                            "question_set_version": "1",
                            "risk_class": "L2",
                            "abstention_options": ["ESCALATE"],
                        },
                        "dataset_path": str(dataset_path),
                        "engine": {
                            "type": "fixture",
                            "identity": {
                                "engine_family": "fixture",
                                "provider_runtime": "local",
                                "model_id": "fixture-a",
                            },
                            "fixture_path": str(fixture_path),
                        },
                        "output_root": str(output_root),
                    }
                ),
                encoding="utf-8",
            )

            first = run_experiment(config_path)
            self.assertEqual(first["status"], "complete")

            second = run_experiment(config_path)
            self.assertEqual(second["status"], "ALREADY_EXISTS")

            third = run_experiment(config_path, rerun=True)
            self.assertEqual(third["status"], "complete")
            self.assertNotEqual(first["run_id"], third["run_id"])


if __name__ == "__main__":
    unittest.main()
