from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.spineforge_v21_bounded_quality import (
    build_bounded_quality_contract,
    build_scene_repair_handoff,
    build_scene_repair_cluster,
    next_quality_action,
    split_findings,
)

V20_REAUDIT = Path(
    "evidence/spineforge-v20-paid-writer/37203770084/"
    "age12-island-v20-story-quality-reaudit-c9-product.json"
)
V20_REPAIRED_STORY = Path(
    "evidence/spineforge-v20-paid-writer/37204419845/"
    "age12-island-v20-story-quality-repair-c10-product.json"
)
V21_CONTRACT = Path(
    "data/specifications/story_lab/spineforge_v21_bounded_quality_contract.json"
)
REPORT_PATH = Path(
    "evidence/spineforge-v21-zero-cost/bridge-regression-qualification.json"
)


def build_report() -> dict[str, Any]:
    runtime = json.loads(V21_CONTRACT.read_text(encoding="utf-8"))
    audit = json.loads(V20_REAUDIT.read_text(encoding="utf-8"))
    story = json.loads(V20_REPAIRED_STORY.read_text(encoding="utf-8"))

    findings = audit["findings"]
    segments = story["repaired_segments"]
    blocking, advisory = split_findings(findings)
    plan = build_scene_repair_cluster(
        findings=findings,
        story_segments=segments,
    )
    handoff = build_scene_repair_handoff(
        source_story_artifact_id=story["artifact_id"],
        source_story_sha256=story["repaired_story_text_sha256"],
        findings=findings,
        story_segments=segments,
        approved_spine_hash=(
            "f9c5bed93448d6c56787466ae583dfcee06d0f856641d9c3901136f142bffae6"
        ),
        canon_invariants=[
            "Arda performs the decisive cut.",
            "The cut must physically release Arda from the falling bridge event.",
            "Nisa assists the final recovery without replacing Arda's decisive action.",
        ],
    )

    initial_action = next_quality_action(
        audit_phase="INITIAL",
        blocking_finding_count=len(blocking),
        repair_count=0,
    )
    clean_final = next_quality_action(
        audit_phase="FINAL",
        blocking_finding_count=0,
        repair_count=1,
    )
    dirty_final = next_quality_action(
        audit_phase="FINAL",
        blocking_finding_count=1,
        repair_count=1,
    )

    contract = build_bounded_quality_contract()
    passed = (
        runtime["quality"]["scene_repair"]["max_executions"] == 1
        and runtime["quality"]["final_audit"]["max_executions"] == 1
        and runtime["quality"]["automatic_looping"] is False
        and contract["max_scene_repairs"] == 1
        and len(blocking) == 4
        and len(advisory) == 9
        and plan["cluster"]["start_span_id"] == "S159"
        and plan["cluster"]["end_span_id"] == "S177"
        and initial_action == "SCENE_REPAIR"
        and clean_final == "ACCEPT"
        and dirty_final == "REJECT_NON_CONVERGENT"
        and handoff["paid_execution_authorized"] is False
    )

    return {
        "schema": "spineforge-v21-zero-cost-qualification.v1",
        "status": "PASS" if passed else "FAIL",
        "paid_api_calls": 0,
        "source_revision": "SPINEFORGE-STORY-FIRST-FROZEN-v20.87",
        "architecture": contract,
        "bridge_regression": {
            "source_finding_count": len(findings),
            "blocking_finding_count": len(blocking),
            "advisory_finding_count": len(advisory),
            "blocking_finding_indexes": [row.index for row in blocking],
            "scene_cluster": plan["cluster"],
            "initial_action": initial_action,
            "clean_final_action": clean_final,
            "dirty_final_action": dirty_final,
        },
        "scene_repair_handoff": handoff,
        "production_policy": {
            "production_active_auditors_per_audit": 1,
            "shadow_auditor_in_production": False,
            "max_initial_audits": 1,
            "max_scene_repairs": 1,
            "max_final_audits": 1,
            "max_quality_model_calls": 3,
            "english_pipeline_target_usd": 0.10,
            "model_slots_replaceable_without_topology_change": True,
        },
    }


def main() -> None:
    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
