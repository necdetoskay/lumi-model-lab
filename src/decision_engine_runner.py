from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.decision_engine import (
    HARNESS_VERSION,
    DecisionCase,
    DecisionEngineIdentity,
    DecisionEngineMalformedOutput,
    DecisionEngineOutput,
    DecisionWorkloadProfile,
    validate_output,
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("api_key", "apikey", "token", "secret", "authorization")):
                result[key] = "[REDACTED]"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class ExternalCommandDecisionEngine:
    """Adapter boundary for local/open/hosted sidecars.

    The command receives one JSON request on stdin and must return one
    DecisionEngineOutput-compatible JSON object on stdout. shell=True is
    intentionally forbidden.
    """

    def __init__(
        self,
        identity: DecisionEngineIdentity,
        command: list[str],
        timeout_seconds: float = 30.0,
    ) -> None:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError("command engine requires a non-empty argv list")
        self.identity = identity
        self._command = command
        self._timeout_seconds = timeout_seconds

    def evaluate(
        self,
        *,
        workload: DecisionWorkloadProfile,
        case: DecisionCase,
    ) -> DecisionEngineOutput:
        request = {
            "schema_version": 1,
            "workload": workload.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
        }
        completed = subprocess.run(
            self._command,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self._timeout_seconds,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"external decision engine exited with code {completed.returncode}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("external decision engine returned non-JSON output") from exc
        return DecisionEngineOutput.model_validate(payload)


class FixtureDecisionEngine:
    def __init__(self, identity: DecisionEngineIdentity, outputs: dict[str, Any]) -> None:
        self.identity = identity
        self._outputs = outputs

    def evaluate(
        self,
        *,
        workload: DecisionWorkloadProfile,
        case: DecisionCase,
    ) -> DecisionEngineOutput:
        del workload
        payload = self._outputs.get(case.case_id)
        if payload is None:
            raise RuntimeError(f"fixture output missing for {case.case_id}")
        return DecisionEngineOutput.model_validate(payload)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_engine(config: dict[str, Any]):
    engine_type = config.get("type")
    identity = DecisionEngineIdentity.model_validate(config["identity"])

    if engine_type == "fixture":
        fixture_path = Path(config["fixture_path"])
        fixture = _load_json(fixture_path)
        return FixtureDecisionEngine(identity, fixture["outputs"])

    if engine_type == "command":
        return ExternalCommandDecisionEngine(
            identity,
            list(config["command"]),
            float(config.get("timeout_seconds", 30.0)),
        )

    raise ValueError(
        f"unsupported engine type {engine_type!r}; no fallback is allowed"
    )


def experiment_fingerprint(
    *,
    workload: DecisionWorkloadProfile,
    dataset_sha256: str,
    engine_identity: DecisionEngineIdentity,
) -> str:
    payload = {
        "harness_version": HARNESS_VERSION,
        "workload": workload.model_dump(mode="json"),
        "dataset_sha256": dataset_sha256,
        "engine_identity": engine_identity.model_dump(mode="json"),
    }
    return sha256_text(canonical_json(payload))


def run_experiment(config_path: Path, *, rerun: bool = False) -> dict[str, Any]:
    config = _load_yaml(config_path)
    workload = DecisionWorkloadProfile.model_validate(config["workload_profile"])
    dataset_path = Path(config["dataset_path"])
    dataset = _load_json(dataset_path)
    cases = [DecisionCase.model_validate(item) for item in dataset["cases"]]
    engine = build_engine(config["engine"])

    dataset_sha = sha256_file(dataset_path)
    fingerprint = experiment_fingerprint(
        workload=workload,
        dataset_sha256=dataset_sha,
        engine_identity=engine.identity,
    )

    output_root = Path(config.get("output_root", "runs/decision_engine"))
    experiment_dir = output_root / fingerprint
    existing = sorted(experiment_dir.glob("run-*")) if experiment_dir.exists() else []
    if existing and not rerun:
        return {
            "status": "ALREADY_EXISTS",
            "experiment_fingerprint": fingerprint,
            "existing_runs": [str(path) for path in existing],
        }

    now = datetime.now(timezone.utc)
    run_id = now.strftime("run-%Y%m%dT%H%M%S.%fZ")
    run_dir = experiment_dir / run_id
    case_dir = run_dir / "cases"
    case_dir.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, Any]] = []
    completed = 0
    malformed = 0
    runtime_errors = 0

    for case_index, case in enumerate(cases):
        request_payload = {
            "workload": workload.model_dump(mode="json"),
            "case": case.model_dump(mode="json"),
        }
        request_json = canonical_json(request_payload)
        request_fingerprint = sha256_text(request_json)
        state_size_bytes = len(
            canonical_json(case.state).encode("utf-8")
        )
        started = time.perf_counter()
        try:
            raw_output = engine.evaluate(workload=workload, case=case)
            validated = validate_output(
                workload=workload,
                case=case,
                output=raw_output,
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            row = {
                "case_id": case.case_id,
                "status": "complete",
                "request_fingerprint": request_fingerprint,
                "state_size_bytes": state_size_bytes,
                "question_count": len(case.questions),
                "latency_ms": latency_ms,
                "latency_class": "cold" if case_index == 0 else "warm",
                "answers": [a.model_dump(mode="json") for a in validated.answers],
                "provider_metadata": redact(validated.provider_metadata),
                "runtime_metadata": redact(validated.runtime_metadata),
                "usage": redact(validated.usage),
                "cost": redact(validated.cost),
            }
            evidence = {
                **row,
                "raw_output": redact(validated.raw_output),
            }
            completed += 1
        except DecisionEngineMalformedOutput as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            row = {
                "case_id": case.case_id,
                "status": "malformed_output",
                "request_fingerprint": request_fingerprint,
                "state_size_bytes": state_size_bytes,
                "question_count": len(case.questions),
                "latency_ms": latency_ms,
                "latency_class": "cold" if case_index == 0 else "warm",
                "error": str(exc),
            }
            evidence = row
            malformed += 1
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000.0
            row = {
                "case_id": case.case_id,
                "status": "runtime_error",
                "request_fingerprint": request_fingerprint,
                "state_size_bytes": state_size_bytes,
                "question_count": len(case.questions),
                "latency_ms": latency_ms,
                "latency_class": "cold" if case_index == 0 else "warm",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            evidence = row
            runtime_errors += 1

        (case_dir / f"{case.case_id}.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        rows.append(row)

    latencies = sorted(float(row["latency_ms"]) for row in rows)
    warm_latencies = sorted(
        float(row["latency_ms"]) for row in rows if row["latency_class"] == "warm"
    )

    def percentile(values: list[float], p: float) -> float | None:
        if not values:
            return None
        index = min(len(values) - 1, round((len(values) - 1) * p))
        return values[index]

    manifest = {
        "schema_version": 1,
        "harness_version": HARNESS_VERSION,
        "run_id": run_id,
        "created_at": now.isoformat(),
        "status": "complete" if malformed == 0 and runtime_errors == 0 else "completed_with_failures",
        "experiment_fingerprint": fingerprint,
        "config_path": str(config_path),
        "dataset_path": str(dataset_path),
        "dataset_sha256": dataset_sha,
        "dataset_id": dataset.get("dataset_id"),
        "dataset_version": dataset.get("dataset_version"),
        "workload_profile": workload.model_dump(mode="json"),
        "engine_identity": engine.identity.model_dump(mode="json"),
        "case_count": len(cases),
        "completed_count": completed,
        "malformed_output_count": malformed,
        "runtime_error_count": runtime_errors,
        "latency_ms": {
            "cold": float(rows[0]["latency_ms"]) if rows else None,
            "overall_p50": percentile(latencies, 0.50),
            "overall_p95": percentile(latencies, 0.95),
            "warm_p50": percentile(warm_latencies, 0.50),
            "warm_p95": percentile(warm_latencies, 0.95),
        },
        "cases": rows,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {**manifest, "run_dir": str(run_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a bounded decision-engine experiment.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--rerun", action="store_true")
    args = parser.parse_args()

    result = run_experiment(Path(args.config), rerun=args.rerun)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
