"""Build/verify the v21-only freeze without modifying historical verifiers."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v21_constraints import derive_constraints, digest_json, load_constraints, sha_file

PROFILE = Path("data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json")
APPROVAL = Path("evidence/spineforge-v20-human-review/36910614976-approved.json")
SELECTION = Path("data/specifications/story_lab/spineforge_v21_bridge_constraint_selection.json")
CONSTRAINTS = Path("evidence/spineforge-v21-zero-cost/approved-spine-constraints.json")
SOURCE = Path("evidence/spineforge-v20-paid-writer/37204419845/age12-island-v20-story-quality-repair-c10-product.json")
AUDIT = Path("evidence/spineforge-v20-paid-writer/37203770084/age12-island-v20-story-quality-reaudit-c9-product.json")
HANDOFF = Path("evidence/spineforge-v20-writer-handoff/36910614976-writer-ready.json")


def dependency_paths() -> list[Path]:
    roots = set(Path("src").glob("spineforge_v21_*.py"))
    roots.update(Path("tests").glob("test_spineforge_v21_*.py"))
    roots.update(Path("prompts").glob("spineforge_v21_*.md"))
    roots.update(Path("data/specifications/story_lab").glob("spineforge_v21_*.json"))
    story = json.loads(SOURCE.read_text())
    roots.update([APPROVAL, SELECTION, CONSTRAINTS, SOURCE, AUDIT, HANDOFF,
                  Path(story["repaired_story_path"]), Path("configs/model_runtime_profiles.yaml"),
                  Path("requirements.txt"), Path(".github/workflows/spineforge-v21-zero-cost.yml")])
    pending = list(roots)
    while pending:
        path = pending.pop()
        if path.suffix != ".py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [r.name for r in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                if module and module.startswith("src."):
                    dep = Path(module.replace(".", "/") + ".py")
                    if not dep.is_file():
                        raise RuntimeError(f"Missing runtime dependency: {dep}")
                    if dep not in roots:
                        roots.add(dep)
                        pending.append(dep)
    return sorted(roots)


def seal(profile: dict) -> dict:
    profile = {k: v for k, v in profile.items() if k != "profile_sha256"}
    return {**profile, "profile_sha256": digest_json(profile)}


def build_profile(source_commit: str) -> dict:
    approval = json.loads(APPROVAL.read_text())
    constraints = derive_constraints(approval, json.loads(SELECTION.read_text()),
                                     approval_file_sha256=sha_file(APPROVAL))
    CONSTRAINTS.parent.mkdir(parents=True, exist_ok=True)
    CONSTRAINTS.write_text(json.dumps(constraints, ensure_ascii=False, indent=2) + "\n")
    story = json.loads(SOURCE.read_text())
    policy = json.loads(Path("data/specifications/story_lab/spineforge_v21_bounded_quality_contract.json").read_text())
    writer_handoff = json.loads(HANDOFF.read_text())
    return seal({
        "schema_version": "spineforge-runtime-profile.v1",
        "runtime_id": "spineforge.v21.bounded-quality",
        "qualification_state": "ZERO_COST_FROZEN_PAID_NOT_AUTHORIZED",
        "runtime_freeze": {"enabled": True, "runtime_revision": "SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.3",
                           "source_commit": source_commit,
                           "files": [{"path": str(p), "sha256": sha_file(p)} for p in dependency_paths()]},
        "source_story": {"artifact_path": str(SOURCE), "artifact_id": story["artifact_id"],
                         "story_sha256": story["repaired_story_text_sha256"],
                         "story_file_sha256": story["repaired_story_file_sha256"],
                         "approved_spine_hash": approval["spine_hash"]},
        "approved_spine": {"artifact_path": str(APPROVAL), "selection_path": str(SELECTION),
                           "constraints_path": str(CONSTRAINTS), "constraints_sha256": constraints["artifact_sha256"],
                           "writer_handoff_path": str(HANDOFF)},
        "reader_profile": {k: writer_handoff[k] for k in ("exact_age", "target_words_min", "target_words_max")},
        "model_slots": {"BLOCKING_AUDITOR": "anthropic/claude-sonnet-5.5",
                        "SCENE_REPAIRER": "anthropic/claude-sonnet-5.5"},
        "cost_policy": {**policy["cost_policy"], "quality_total_ceiling_usd": 0.10,
                        "translation_ledger_separate": True,
                        "english_target_includes_spine_writer_and_rejected_attempts": True,
                        "stage_ceiling_semantics": "STOP_AFTER_ACTUAL_COST_REPORTED_NO_NEXT_CALL",
                        "provider_spend_cap_guaranteed": False,
                        "paid_preflight_required": ["explicit_user_budget_authorization", "current_provider_pricing_and_request_budget_review"]},
        "paid_boundary": {"paid_execution_authorized": False, "authorization_consumed": True,
                          "authorization_marker": "PAID-V21-BOUNDED-QUALITY-E2E",
                          "explicit_user_authorization_required": True,
                          "authorization_state": "NO_GRANT_ISSUED"},
    })


def verify_v21_runtime(profile_path: Path = PROFILE) -> dict:
    profile = json.loads(profile_path.read_text())
    if seal(profile) != profile:
        raise RuntimeError("v21 profile integrity drift (authorization/cost/source/config)")
    if profile.get("runtime_id") != "spineforge.v21.bounded-quality":
        raise RuntimeError("Unexpected v21 runtime")
    result = verify_spineforge_runtime(profile_path)
    expected = {str(p) for p in dependency_paths()}
    rows = profile["runtime_freeze"]["files"]
    if {r["path"] for r in rows} != expected or len(rows) != len(expected):
        raise RuntimeError("Incomplete frozen runtime dependency closure")
    load_constraints(profile)
    source = profile["source_story"]
    artifact = json.loads(Path(source["artifact_path"]).read_text())
    story_path = Path(artifact["repaired_story_path"])
    if (sha_file(story_path) != source["story_file_sha256"]
            or artifact["artifact_id"] != source["artifact_id"]
            or artifact["repaired_story_text_sha256"] != source["story_sha256"]):
        raise RuntimeError("Source story binding drift")
    approval = json.loads(Path(profile["approved_spine"]["artifact_path"]).read_text())
    handoff = json.loads(Path(profile["approved_spine"]["writer_handoff_path"]).read_text())
    if (handoff.get("spine_hash") != approval["spine_hash"]
            or profile["reader_profile"] != {k: handoff[k] for k in ("exact_age", "target_words_min", "target_words_max")}):
        raise RuntimeError("Writer handoff/approved Spine mismatch")
    result["profile_sha256"] = profile["profile_sha256"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    if args.write:
        if not args.source_commit or len(args.source_commit) != 40:
            parser.error("--write requires the source commit SHA")
        PROFILE.write_text(json.dumps(build_profile(args.source_commit), indent=2) + "\n")
    print(json.dumps(verify_v21_runtime(), indent=2))


if __name__ == "__main__":
    main()
