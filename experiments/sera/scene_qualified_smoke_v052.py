"""SERA v0.52 reproducible OFFLINE smoke: true full-qualification adapters.

Ari 2-sentence source performs a model-authored scripted rewrite and *full*
v0.23 re-qualification; real original Mara 28-sentence source is deliberately
given incomplete synthetic provider rows and MUST stop safely. No real provider,
no key lookup, no world writes. Outputs are explicitly labeled SYNTHETIC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.scene_qualified_model_lane_v052 import (
    FAKE_KEY, frozen_mara_offline,
)
from experiments.sera.tests.test_scene_qualified_model_lane_v052 import (
    MODELS, ari, bridge_provider,
)


def smoke(root):
    root = Path(root)
    ari_calls = []
    ari_first = ari(root/"ari", bridge_provider(ari_calls))
    ari_replay = ari(
        root/"ari",
        lambda **kw: (_ for _ in ()).throw(
            AssertionError("V052_ARI_MODEL_REPOST_FORBIDDEN")
        ),
    )
    assert ari_first == ari_replay
    assert ari_first["status"] == "FULL_SCENE_QUALIFIED_CANDIDATE_NONCANONICAL"
    assert ari_first["automatic_rewrites"] == 1
    assert [row[0] for row in ari_calls].count(MODELS["writer"]) == 1

    mara_calls = []
    def incomplete(*, key, model, prepared):
        assert key == FAKE_KEY
        assert model != MODELS["writer"]
        mara_calls.append(model)
        return {
            "error": None,
            "raw": {
                "id": "v052-scripted-missing-full-source-" + str(len(mara_calls)),
                "model": model,
                "usage": {"cost": "0"},
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": '{"rows":[]}'},
                }],
            },
        }
    mara_first = frozen_mara_offline(
        output_root=root/"mara", provider_call=incomplete, models=MODELS,
    )
    calls_before = len(mara_calls)
    mara_replay = frozen_mara_offline(
        output_root=root/"mara",
        provider_call=lambda **kw: (_ for _ in ()).throw(
            AssertionError("V052_MARA_MODEL_REPOST_FORBIDDEN")
        ),
        models=MODELS,
    )
    assert mara_first == mara_replay
    assert len(mara_calls) == calls_before
    assert mara_first["source_sentence_count"] == 28
    assert mara_first["status"] == "FAILED_SAFE_FINAL"
    assert mara_first["automatic_rewrites"] == 0

    for result in (ari_first,mara_first):
        assert result["provider_is_real"] is False
        assert result["new_paid_model_calls"] == 0
        assert result["observed_new_cost_usd"] == "0"
        assert result["canonical_commit_authorized"] is False
        assert result["production_db_writes"] == 0
        assert result["requires_manual_intervention"] is False
        assert result["full_28_sentence_genuine_model_semantics_approved"] is False

    proof = {
        "schema": "sera.v052-full-qualified-transport-smoke",
        "status": "SYNTHETIC_ARI_QUALIFIED_MARA_28_FAILED_SAFE",
        "transport": "SCRIPTED_OFFLINE_NO_REAL_LLM",
        "ari_original_source_sentence_count": ari_first["source_sentence_count"],
        "ari_automatic_rewrites": ari_first["automatic_rewrites"],
        "ari_full_v023_qualification": (
            ari_first["status"] == "FULL_SCENE_QUALIFIED_CANDIDATE_NONCANONICAL"
        ),
        "ari_model_callback_count": len(ari_calls),
        "mara_frozen_source_sha256": mara_first["source_sha256"],
        "mara_original_source_sentence_count": 28,
        "mara_status": mara_first["status"],
        "mara_provider_callback_count": calls_before,
        "restart_extra_callbacks": 0,
        "new_real_provider_calls": 0,
        "new_provider_cost_usd": "0",
        "model_output_token_ceiling_set": False,
        "human_story_edits": 0,
        "genuine_real_mara_repair_qualified": False,
        "canonical_commit_authorized": False,
        "production_db_writes": 0,
    }
    target = root/"proof.json"
    target.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n",
                      encoding="utf-8")
    return proof


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output-root",type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(smoke(args.output_root),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
