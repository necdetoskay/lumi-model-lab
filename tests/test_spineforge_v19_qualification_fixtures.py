from __future__ import annotations

import json
from pathlib import Path

from src.spine_context_pack_v1 import SpineContextPackV1, fingerprint_value
from src.spineforge_v19_obligations import load_qualification_cases


def test_all_six_v19_context_fixtures_are_frozen_and_valid():
    cases = load_qualification_cases().cases
    assert len(cases) == 6
    assert all(case.context_fixture_status == "FROZEN" for case in cases)

    seen_ids = set()
    for case in cases:
        path = Path(case.context_fixture_ref)
        assert path.exists(), path
        raw = json.loads(path.read_text(encoding="utf-8"))
        pack = SpineContextPackV1.model_validate(raw)
        assert pack.context_pack_id not in seen_ids
        seen_ids.add(pack.context_pack_id)
        assert int(pack.reader_profile["exact_age"]) == case.obligations.exact_age
        assert pack.knowledge_boundaries["reveal_policy"]["hidden_truth_answers_included"] is False
        expected = fingerprint_value({k: v for k, v in raw.items() if k != "context_fingerprint"})
        assert pack.context_fingerprint == expected


def test_frozen_v19_fixtures_do_not_carry_hidden_truth_payload_fields():
    for case in load_qualification_cases().cases:
        text = Path(case.context_fixture_ref).read_text(encoding="utf-8").lower()
        assert '"hidden_statement"' not in text
        assert '"reveal_steps"' not in text
