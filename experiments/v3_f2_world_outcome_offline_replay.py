"""Replay ONE actual archived model answer after a non-literary quote parser fix.

This does not send ANY provider request and does not re-interpret/edit
literary prose. A real Sol/Luna response is reused byte-for-byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_guard import SafetyStop
from experiments.v3_f2_world_outcome_evidence_gate import validate_judge_output

SOURCE=Path("evidence/v3-f2-world-outcome-luna-38726200623")
SOURCE_MODEL=SOURCE/"judge-model-response.json"
SOURCE_SHA="dd000b88809065e112ccf369a2b659eddffc48fd34698d7e68b3575feec5d95a"
MODEL="openai/gpt-5.6-luna"
GENERATION_ID="gen-1792063036-NcKV7agmrCPmqqOQEiWk"
SOURCE_RUN=38726200623
EXPECTED_COST=Decimal("0.0030664")


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path:Path,obj:dict):
    with path.open("x",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def replay(*,out_dir:Path)->dict:
    if out_dir.exists():
        raise SafetyStop("WORLD_REPLAY_DESTINATION_EXISTS")
    if sha(SOURCE_MODEL)!=SOURCE_SHA:
        raise SafetyStop("WORLD_REPLAY_ARCHIVED_MODEL_TAMPERED")
    frozen=verify_frozen_lane(Path(
        "data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json"
    ))
    if frozen["verified_files"]!=43:
        raise SafetyStop("WORLD_REPLAY_FROZEN_V3_INTEGRITY_FAILED")
    real=json.loads(SOURCE_MODEL.read_text(encoding="utf-8"))
    if (real.get("model")!=MODEL or real.get("generation_id")!=GENERATION_ID
        or real.get("source_story_sha256")!="990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8"
        or Decimal(str(real.get("reported_cost_usd")))!=EXPECTED_COST):
        raise SafetyStop("WORLD_REPLAY_PROVIDER_EVIDENCE_INVALID")
    events=[json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SOURCE.glob("[0-9][0-9][0-9]-*.json"))]
    kinds=[x["kind"] for x in events]
    if kinds!=[
        "WORLD_JUDGE_GRANT_VERIFIED",
        "GUARD_INSTALLED",
        "POST_INTENT",
        "HTTP_OBSERVED",
        "PROVIDER_OBSERVED",
        "STAGE_STOP",
    ]:
        raise SafetyStop("WORLD_REPLAY_ORIGINAL_STOP_EVIDENCE_MISMATCH")
    p=events[4]
    if (p.get("call_number")!=1 or p.get("model")!=MODEL
        or p.get("generation_id")!=GENERATION_ID
        or Decimal(str(p.get("reported_cost_usd")))!=EXPECTED_COST
        or events[5].get("model_posts")!=1
        or events[5].get("exception_type")!="OutcomeStop"):
        raise SafetyStop("WORLD_REPLAY_POST_HISTORY_INVALID")
    result=validate_judge_output(real["model_json"])
    proposals=result["approved_persistent_candidates"]
    count=sum(x["model_condition_verdict"]=="EARNED" for x in proposals)
    italic=sum(x=="ITALIC_CLOSER_BOUNDARY_ONLY" for x in
              result["branch_quote_provenance"]+
              [p for row in proposals for p in row["quote_provenance"]])
    if italic!=1:
        raise SafetyStop("WORLD_REPLAY_UNEXPECTED_MARKUP_MATCH_COUNT")
    if not 0<=count<=5:
        raise SafetyStop("WORLD_REPLAY_INVALID_VERDICT_COUNT")
    out_dir.mkdir(parents=True,mode=0o700)
    _write(out_dir/"world-outcome-proposal.json",result)
    manifest={
        "schema":"lumi.v3-f2.world-outcome-offline-evidence-replay.v1",
        "status":"MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED",
        "original_provider_run_id":SOURCE_RUN,
        "original_provider_response_sha256":SOURCE_SHA,
        "original_provider_generation_id":GENERATION_ID,
        "original_provider_model":MODEL,
        "provider_cost_usd_in_original_run":str(EXPECTED_COST),
        "additional_provider_posts":0,
        "additional_provider_cost_usd":"0",
        "source_original_run_result":"STAGE_STOP",
        "normalization_policy":"ONLY_EARLY_ITALIC_CLOSER_IF_ALL_PROSE_BYTES_EXACT",
        "italic_boundary_accepted_quote_count":italic,
        "model_selected_branch":result["model_selected_branch"],
        "model_earned_outcome_candidates":count,
        "reviewed_outcome_candidates":len(proposals),
        "model_response_was_not_edited":True,
        "publication_authorized":False,
        "published":False,
        "world_state_commit_authorized":False,
        "world_state_committed":False,
        "applied_operations":[],
        "proposal_sha256":sha(out_dir/"world-outcome-proposal.json"),
    }
    _write(out_dir/"offline-replay-manifest.json",manifest)
    return manifest


if __name__=="__main__":
    args=argparse.ArgumentParser()
    args.add_argument("--out-dir",required=True,type=Path)
    a=args.parse_args()
    result=replay(out_dir=a.out_dir)
    print(json.dumps({
        "status":result["status"],
        "branch":result["model_selected_branch"],
        "earned":result["model_earned_outcome_candidates"],
        "candidates":result["reviewed_outcome_candidates"],
        "provider_posts":0,
        "world_state_committed":False,
    },ensure_ascii=False))
