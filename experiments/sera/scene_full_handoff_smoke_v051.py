"""v0.51 original real Mara receipts -> v0.50 -> actual v0.22/21/20 safe stop.

Offline synthetic provider replies only. Separate Ari two-sentence control
demonstrates the automatic full-scene rewrite/recheck path can become ready.
Neither run grants semantic gold nor G2 authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.scene_full_handoff_v051 import run_real_mara_shadow
from experiments.sera.tests.test_automated_row_recovery_v050 import (
    scripted_provider,
)
from experiments.sera.tests.test_scene_full_handoff_v051 import (
    bad_mara_full_provider, ari_source_stage, ari_gate, rewrite_box,
)
from experiments.sera.tests.test_fresh_scene_evidence_worker_v022 import fake_model


def smoke(*,receipt_root,output_root):
    root=Path(output_root)
    row_calls=[]
    full_calls=[]
    def unreachable_writer(**kwargs):
        raise AssertionError("V051_MARA_REWRITE_NEEDS_FULL_EVIDENCE")
    first=run_real_mara_shadow(
        receipt_root=receipt_root,output_root=root/"mara",
        row_provider=scripted_provider(
            row_calls,invalid_first={"s006","s004"}
        ),
        full_provider=bad_mara_full_provider(full_calls),
        writer=unreachable_writer,
    )
    before=(len(row_calls),len(full_calls))
    second=run_real_mara_shadow(
        receipt_root=receipt_root,output_root=root/"mara",
        row_provider=lambda **kw:(_ for _ in ()).throw(
            AssertionError("V051_ROW_REPLAY_PROHIBITED")),
        full_provider=lambda **kw:(_ for _ in ()).throw(
            AssertionError("V051_FULL_REPLAY_PROHIBITED")),
        writer=unreachable_writer,
    )
    assert first==second
    assert before==(28,2)
    assert first["original_real_receipts_verified"]==14
    assert first["row_stage"]["candidate_source_rows_reextracted"]==5
    assert first["row_stage"]["source_blind_advisories"]==21
    assert first["full_stage"]["stage_reached_actual_v020_v021_v022"]
    assert first["full_stage"]["status"]=="FAILED_SAFE_FINAL"
    assert first["full_stage"]["automatic_rewrites"]==0
    # Positive control is a different 2-sentence source, never presented as
    # Mara's 28-sentence physical qualification.
    model_calls=[]
    writer_calls=[]
    positive=ari_gate(
        root/"ari-control",ari_source_stage(),
        fake_model(model_calls),rewrite_box(writer_calls),
    )
    replay=ari_gate(
        root/"ari-control",ari_source_stage(),
        lambda **kw:(_ for _ in ()).throw(
            AssertionError("V051_ARI_MODEL_REPOST_PROHIBITED")),
        lambda **kw:(_ for _ in ()).throw(
            AssertionError("V051_ARI_WRITER_REPOST_PROHIBITED")),
    )
    assert positive==replay
    assert positive["status"]=="FULL_SCENE_STRUCTURAL_CANDIDATE_NONCANONICAL"
    assert positive["automatic_rewrites"]==1
    assert len(writer_calls)==1
    assert first["canonical_commit_authorized"] is False
    result={
        "schema":"sera.v051-real-mara-to-full-scene-revalidation-shadow",
        "status":"SOURCE_BOUND_AUTO_REPAIR_HANDOFF_AND_FULL_SCENE_GATE_VERIFIED",
        "real_historical_mara_receipts_verified":14,
        "real_previous_spend_usd":first["original_real_spend_usd"],
        "mara_source_sentence_count":28,
        "scripted_mara_row_reextractions":5,
        "scripted_mara_blind_advisories":21,
        "scripted_mara_row_fallbacks":2,
        "mara_scripted_row_calls_initial":before[0],
        "mara_scripted_full_scene_model_calls_initial":before[1],
        "mara_full_scene_outcome":first["full_stage"]["status"],
        "mara_scene_rewrite_count":first["full_stage"]["automatic_rewrites"],
        "mara_new_provider_calls_on_replay":0,
        "positive_ari_2_sentence_control":{
            "full_scene_status":positive["status"],
            "automatic_rewrites":positive["automatic_rewrites"],
            "synthetic_model_calls":len(model_calls),
            "replay_calls":0,
        },
        "new_paid_openrouter_calls":0,
        "new_paid_cost_usd":"0",
        "mara_28_sentence_true_semantic_correction_proven":False,
        "mara_g2_publish_qualified":False,
        "manual_story_repairs_required":0,
        "canonical_commit_authorized":False,
        "production_world_db_writes":0,
        "sqlite_lab_world_db_writes":0,
    }
    root.mkdir(parents=True,exist_ok=True)
    (root/"proof.json").write_text(
        json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
        encoding="utf-8",
    )
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt-root",type=Path,required=True)
    p.add_argument("--output-root",type=Path,required=True)
    args=p.parse_args()
    smoke(receipt_root=args.receipt_root,output_root=args.output_root)


if __name__=="__main__":
    main()
