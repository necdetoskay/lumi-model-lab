from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import MockCanonicalStateV1, build_spine_context_pack
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v5_case_manifest import load_spineforge_v5_case

PROFILE = Path(
    "data/specifications/story_lab/"
    "spineforge_runtime_profile_v5_creative_structural_split_frozen.json"
)
CASE = Path(
    "data/specifications/story_lab/"
    "spineforge_v5_age18_forbidden_cartographer_case_v1.json"
)
LEDGER = Path(
    "data/specifications/story_lab/"
    "spineforge_v5_age18_forbidden_cartographer_cost_ledger_v1.json"
)


def test_v5_runtime_hashes_match() -> None:
    result = verify_spineforge_runtime(PROFILE)
    assert result["verified"] is True
    assert result["runtime_revision"] == "SPINEFORGE-CONTEXTPACK-FROZEN-v5"
    assert result["verified_files"] == 31


def test_v5_case_materializes_exact_expected_pack() -> None:
    case = load_spineforge_v5_case(CASE)
    source = MockCanonicalStateV1.model_validate_json(
        Path(case.canonical_state_source).read_text(encoding="utf-8")
    )
    pack = build_spine_context_pack(source)
    assert pack.context_pack_id == case.expected_context_pack_id
    assert pack.context_fingerprint == case.expected_context_fingerprint


def test_v5_starts_zero_spend_without_paid_trigger() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger["status"] == "READY_FOR_ATTEMPT_1"
    assert ledger["attempts"] == []
    assert ledger["v5_actual_spend"] == {
        "api_calls": 0,
        "total_tokens": 0,
        "cost_usd": 0,
        "latency_seconds": 0,
    }
    assert ledger["paid_boundary"]["authorized"] is False
    assert not Path("experiments/triggers/spineforge-v5.json").exists()


def test_v5_freeze_preserves_v1_v2_v3_v4_hashes() -> None:
    profiles = [
        ("data/specifications/story_lab/spineforge_runtime_profile_v1_frozen.json", 25),
        ("data/specifications/story_lab/spineforge_runtime_profile_v2_context_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v3_contract_recovery_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v4_normalizer_integrity_frozen.json", 26),
        ("data/specifications/story_lab/spineforge_runtime_profile_v5_creative_structural_split_frozen.json", 31),
    ]
    for path, count in profiles:
        result = verify_spineforge_runtime(Path(path))
        assert result["verified"] is True
        assert result["verified_files"] == count


def test_v5_runtime_has_no_case_specific_recovery() -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    forbidden = ["Leyra", "Ashen Gate", "Greyfen", "forbidden_cartographer"]
    for row in profile["runtime_freeze"]["files"]:
        path = Path(row["path"])
        if path.suffix.lower() not in {".py", ".md", ".yml", ".yaml", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} leaked into frozen v5 runtime {path}"
