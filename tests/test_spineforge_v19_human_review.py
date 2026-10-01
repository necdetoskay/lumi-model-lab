from pathlib import Path

import pytest

from src.narrative_spine_v1_contract import NarrativeSpineV1, SpineProductGateV19
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_human_review import (
    build_human_approval,
    render_human_preview,
    spine_hash,
)
from tests.test_spineforge_v19_runtime_mock import _spine


PACK = Path(
    "data/specifications/story_lab/age18_forbidden_cartographer_spine_context_pack_v1.json"
)


def test_preview_and_approval_are_bound_to_exact_spine_and_context():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    gate = SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready.",
    })
    preview = render_human_preview(spine=spine, pack=pack, gate=gate)
    assert spine_hash(spine) in preview
    assert pack.context_fingerprint in preview

    approval = build_human_approval(
        spine=spine,
        gate=gate,
        source_context_pack_id=pack.context_pack_id,
        source_context_fingerprint=pack.context_fingerprint,
        current_context_pack=pack,
        reviewer_note="Approved after reading the same hashed preview.",
    )
    assert approval["spine_hash"] == spine_hash(spine)
    assert approval["human_review"]["story_writer_authorized"] is True


def test_stale_context_fingerprint_blocks_human_approval():
    pack = SpineContextPackV1.model_validate_json(PACK.read_text(encoding="utf-8"))
    spine = NarrativeSpineV1.model_validate(_spine(pack))
    gate = SpineProductGateV19.model_validate({
        "schema": "spineforge-v19-product-gate.v1",
        "decision": "ACCEPT",
        "blocking_findings": [],
        "summary": "Ready.",
    })
    with pytest.raises(RuntimeError):
        build_human_approval(
            spine=spine,
            gate=gate,
            source_context_pack_id=pack.context_pack_id,
            source_context_fingerprint="stale",
            current_context_pack=pack,
            reviewer_note="Should not approve stale product.",
        )
