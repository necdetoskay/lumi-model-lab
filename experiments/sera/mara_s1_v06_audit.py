"""Frozen Mara S1 v0.6 coverage baseline. No models, no DB, no gold claims."""
from __future__ import annotations

import json
from pathlib import Path

from experiments.sera.coverage import prose_hash
from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
from experiments.sera.scene_assurance_v06 import audit_scene

LEXICON_PATH = (Path(__file__).resolve().parent /
                "fixtures/object_candidate_lexicon_v0.1.json")


def run() -> dict:
    source = json.loads(PATH.read_text(encoding="utf-8"))
    prose = source["prose"]
    if (prose_hash(prose) != EXPECTED_SHA or
        source["source_prose_sha256"] != EXPECTED_SHA or
        source["production_commit_authorized"] is not False):
        raise RuntimeError("SERA_V06_FROZEN_SOURCE_MISMATCH")
    state = entry_state()
    # train_41 is described in reports/documents, but not a physical entity
    # registered in the actual entry state. Do not canonize it here.
    registry = {k: v for k, v in REGISTRY.items()
                if k in state["entities"]}
    lexicon = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))["candidates"]
    inspection = audit_scene(
        prose=prose, scene_key=source["scene_id"],
        entry_revision=state["revision"], registry=registry,
        candidate_lexicon=lexicon,
    )
    if inspection["status"] != "HOLD":
        raise RuntimeError("SERA_V06_LIVE_SCENE_FALSE_PASS")
    refs = sorted({s["ref"] for s in inspection["t2_sightings"]})
    if not {"candidate:bench", "candidate:pencil"} <= set(refs):
        raise RuntimeError("SERA_V06_KNOWN_DOUBLE_OMISSION_REGRESSION")
    return {
        "schema": "sera.mara-s1-v06-baseline.v0.1",
        "original_prose_sha256": EXPECTED_SHA,
        "sentence_count": len(inspection["sentence_scan"]["sentences"]),
        "accounted_sentence_count":
            inspection["ledger_validation"]["accounted_sentences"],
        "candidate_refs": refs,
        "watch_case_cue_found": any(
            cue["quote"].lower() == "closed"
            for group in inspection["sentence_scan"]["sentence_cues"]
            for cue in group["cues"]
        ),
        "notebook_writing_cue_found": any(
            cue["quote"].lower() == "wrote"
            for group in inspection["sentence_scan"]["sentence_cues"]
            for cue in group["cues"]
        ),
        "event_candidates_from_analyst_annotation": len(source["candidates"]),
        "review_status": inspection["status"],
        "ground_truth_adjudicated": False,
        "model_calls": inspection["model_calls"],
        "canonical_db_writes": inspection["world_db_writes"],
        "canonical_commit_authorized": inspection["canonical_commit_authorized"],
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
