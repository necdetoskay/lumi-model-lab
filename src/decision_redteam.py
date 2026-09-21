from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REDTEAM_VERSION = "decision-engine-redteam-evaluator-v1"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        row["case_id"]: row
        for row in run.get("cases", [])
        if isinstance(row, dict) and isinstance(row.get("case_id"), str)
    }


def _answers(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        answer["question_id"]: answer
        for answer in row.get("answers", [])
        if isinstance(answer, dict) and isinstance(answer.get("question_id"), str)
    }


def _observe(
    rows: dict[str, dict[str, Any]],
    case_id: str,
    dimension: str,
) -> tuple[str | None, float | None, list[str]]:
    row = rows.get(case_id)
    if not row:
        return None, None, [f"missing run case {case_id}"]
    if row.get("status") != "complete":
        return None, None, [f"{case_id} status={row.get('status')}"]
    answers = _answers(row)
    evidence = answers.get(f"{dimension}__evidence")
    score = answers.get(dimension)
    errors: list[str] = []

    evidence_value = None
    if (
        not evidence
        or evidence.get("type") != "choice"
        or evidence.get("value") not in {"SUFFICIENT", "INSUFFICIENT_EVIDENCE"}
    ):
        errors.append(f"{case_id}: invalid/missing evidence gate")
    else:
        evidence_value = str(evidence["value"])

    score_value = None
    if score and score.get("type") == "score":
        value = score.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            score_value = float(value)
        else:
            errors.append(f"{case_id}: non-numeric score")
    else:
        errors.append(f"{case_id}: invalid/missing score")

    return evidence_value, score_value, errors


def _relation_result(
    relation: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    relation_id = relation["relation_id"]
    baseline_id = relation["baseline_case_id"]
    mutant_id = relation["mutant_case_id"]
    dimension = relation["target_dimension"]
    relation_type = relation["type"]
    severity = relation["severity"]

    base_ev, base_score, errors = _observe(rows, baseline_id, dimension)
    mut_ev, mut_score, mutant_errors = _observe(rows, mutant_id, dimension)
    errors.extend(mutant_errors)

    observed: dict[str, Any] = {
        "baseline_evidence": base_ev,
        "mutant_evidence": mut_ev,
        "baseline_score": base_score,
        "mutant_score": mut_score,
    }

    passed = not errors
    failure_reason = None

    if passed and relation_type == "decrease":
        if base_ev != "SUFFICIENT" or mut_ev != "SUFFICIENT":
            passed = False
            failure_reason = "decrease relation requires sufficient evidence in both cases"
        else:
            delta = float(base_score) - float(mut_score)
            observed["decrease_delta"] = delta
            if delta < float(relation["min_delta"]):
                passed = False
                failure_reason = "target score did not decrease by required minimum"

    elif passed and relation_type in {"invariant", "repeat_stability"}:
        if base_ev != mut_ev:
            passed = False
            failure_reason = "evidence gate changed under invariant relation"
        elif base_ev == "SUFFICIENT":
            delta = abs(float(base_score) - float(mut_score))
            observed["absolute_delta"] = delta
            if delta > float(relation["max_delta"]):
                passed = False
                failure_reason = "score moved beyond invariant tolerance"

    elif passed and relation_type == "evidence_flip":
        if not (
            base_ev == "SUFFICIENT"
            and mut_ev == "INSUFFICIENT_EVIDENCE"
        ):
            passed = False
            failure_reason = "missing-evidence mutation did not trigger abstention"

    elif passed and relation_type == "not_improve":
        if base_ev != "SUFFICIENT" or mut_ev != "SUFFICIENT":
            passed = False
            failure_reason = "not_improve relation requires sufficient evidence"
        else:
            increase = float(mut_score) - float(base_score)
            observed["score_increase"] = increase
            if increase > float(relation["max_increase"]):
                passed = False
                failure_reason = "adversarial mutation improperly improved score"

    elif passed and relation_type == "schema_confinement":
        mutant_row = rows[mutant_id]
        expected_case = cases[mutant_id]
        expected_ids = {
            question["question_id"] for question in expected_case.get("questions", [])
        }
        actual_ids = set(_answers(mutant_row))
        observed["expected_question_ids"] = sorted(expected_ids)
        observed["actual_question_ids"] = sorted(actual_ids)
        if actual_ids != expected_ids:
            passed = False
            failure_reason = "output escaped declared question schema"

    elif passed and relation_type not in {
        "decrease",
        "invariant",
        "evidence_flip",
        "not_improve",
        "repeat_stability",
        "schema_confinement",
    }:
        passed = False
        failure_reason = f"unsupported relation type {relation_type}"

    if errors and not failure_reason:
        failure_reason = "; ".join(errors)

    return {
        "relation_id": relation_id,
        "severity": severity,
        "type": relation_type,
        "baseline_case_id": baseline_id,
        "mutant_case_id": mutant_id,
        "target_dimension": dimension,
        "expected": {
            key: relation[key]
            for key in ("min_delta", "max_delta", "max_increase")
            if key in relation
        },
        "observed": observed,
        "passed": passed,
        "failure_reason": failure_reason,
    }


def evaluate_redteam(spec: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(run)
    cases = {
        case["case_id"]: case
        for case in spec.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("case_id"), str)
    }

    results = [
        _relation_result(relation, rows, cases)
        for relation in spec.get("relations", [])
    ]
    failures = [result for result in results if not result["passed"]]
    blocking = [
        result for result in failures if result["severity"] == "critical"
    ]

    status = "PASS"
    if blocking:
        status = "BLOCKING_FINDINGS"
    elif failures:
        status = "FINDINGS"

    return {
        "schema_version": 1,
        "redteam_version": REDTEAM_VERSION,
        "status": status,
        "relation_count": len(results),
        "pass_count": len(results) - len(failures),
        "finding_count": len(failures),
        "blocking_finding_count": len(blocking),
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Decision Engine Red-Team Report",
        "",
        f"- Status: **{report['status']}**",
        f"- Relations: {report['relation_count']}",
        f"- Passed: {report['pass_count']}",
        f"- Findings: {report['finding_count']}",
        f"- Blocking findings: {report['blocking_finding_count']}",
        "",
    ]
    for result in report["results"]:
        marker = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"- **{marker}** `{result['relation_id']}` "
            f"({result['severity']}, {result['type']})"
        )
        if result["failure_reason"]:
            lines.append(f"  - {result['failure_reason']}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a decision-engine red-team run.")
    parser.add_argument(
        "--spec",
        default="data/specifications/decision_redteam_v1.json",
    )
    parser.add_argument("--run", required=True)
    parser.add_argument("--output-dir", default="runs/decision_redteam")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    run_path = Path(args.run)
    spec = _load(spec_path)
    run = _load(run_path)
    report = evaluate_redteam(spec, run)

    fingerprint_payload = {
        "redteam_version": REDTEAM_VERSION,
        "spec_sha256": _sha256(spec_path),
        "run_sha256": _sha256(run_path),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    report["redteam_fingerprint"] = fingerprint
    report["spec_sha256"] = fingerprint_payload["spec_sha256"]
    report["run_sha256"] = fingerprint_payload["run_sha256"]

    output_dir = Path(args.output_dir) / fingerprint
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )

    print(json.dumps({**report, "output_dir": str(output_dir)}, ensure_ascii=False, indent=2))
    if args.require_pass and report["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
