"""P4.41: B04 original accepted English Master -> one genuine Q25 proposal.

Read-only evidence; no Canon mutation. Exactly one provider POST if a reviewed,
source-locked B04 grant is supplied. No automatic retries or fallbacks.
"""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p424_q25_evidence import (
    extraction_wire, verify_model_response, SAFE_FAILURE_CODE, COST_CAP, MODEL, money
)
from src.story_harness_p440_b04_master import (
    original_b04, load_b04_quality, manifest_for,
    MASTER_DIR, AUDIT_SHA, AUDITOR_ID
)
from src.story_harness_p439_b04_quality import SOURCE_SHA, SPINE_SHA, STORY_SHA
from src.story_harness_p417_live_pilot import https_post_once
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p441-b04-evidence-proposal.v1"
RUN_NAME = "p441-b04-r06-q25-evidence-v01"
PRIOR_RESERVED = Decimal("1.929558")
USER_CAP = Decimal("10.00")

def must(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def load_b04_bundle(repo_root, producer_root, quality_root, master_root):
    source = original_b04(repo_root, producer_root)
    audit = load_b04_quality(repo_root, quality_root)
    _, expected = manifest_for(source, audit)
    folder = Path(master_root) / MASTER_DIR
    master_path = folder / "ENGLISH_MASTER.txt"
    manifest_path = folder / "master-manifest.json"
    must(folder.is_dir() and not folder.is_symlink()
         and master_path.is_file() and manifest_path.is_file()
         and not master_path.is_symlink() and not manifest_path.is_symlink(),
         "B04 Master missing/unsafe")
    master_raw = master_path.read_bytes()
    actual = json.loads(manifest_path.read_bytes())
    must(actual == expected
         and manifest_path.read_bytes() == canonical_json(expected) + b"\n"
         and master_raw == source["story"]["story_text"].encode("utf-8")
         and hashlib.sha256(master_raw).hexdigest() == STORY_SHA
         and actual["original_quality_receipt_sha256"] == AUDIT_SHA
         and actual["independent_auditor_generation_id"] == AUDITOR_ID
         and actual["q25_read_only_extraction_allowed"] is True
         and actual["production_state_write_authorized"] is False,
         "B04 original Master bytes/quality admission mismatch")
    must(PRIOR_RESERVED + COST_CAP <= USER_CAP,
         "B04 $10 aggregate provider budget cap exceeded")
    return {"source":source, "audit":audit, "master":actual,
            "english_master_text":master_raw.decode("utf-8")}

def b04_q25_wire(bundle):
    must(bundle["source"]["case_id"] == "B04"
         and bundle["source"]["story"]["story_sha256"] == STORY_SHA,
         "Wrong case/source to B04 Q25")
    wire = extraction_wire(bundle)
    system = wire["messages"][0]["content"]
    must(wire["response_format"]["json_schema"]["name"] ==
         "lumi_b04_q25_evidence_proposal_v1"
         and "AT_MARKET" in system and "AT_STUDIO" in system
         and "AT_VILLAGE" not in system and "AT_HOME" not in system
         and json.loads(wire["messages"][1]["content"])["case_id"] == "B04",
         "B04 Q25 spatial grammar mixed with other story")
    wire["messages"][0]["content"] += (
        " B04-specific: Emir is in the STUDIO after leaving the MARKET; "
        "use a verbatim quotation from the last 40 percent showing his STUDIO "
        "arrival, such as 'The studio was quiet when he arrived.' "
        "for final location and discovered STUDIO. This is a supported "
        "observation, not permission to invent other travel. The paint is "
        "still exhausted and the requested map is still missing. Emir's own "
        "pencil sketch is not the map he wanted. Preserve BOTH original "
        "open obligations as OPEN unless unmistakable later prose proves "
        "otherwise. No object owner may be inferred from carrying or use."
    )
    must(len(canonical_json(wire)) < 24000, "B04 Q25 request too large")
    return wire

def check_b04_response(bundle, response):
    result = verify_model_response(bundle, response)
    evidence = result["evidence_proposal"]
    must(result["case_id"] == "B04"
         and result["source_pack_sha256"] == SOURCE_SHA
         and result["spine_sha256"] == SPINE_SHA
         and result["story_sha256"] == STORY_SHA
         and result["provenance_verified"] is True
         and result["quote_matching_verified"] is True
         and result["production_state_write_authorized"] is False
         and result["semantic_state_fully_certified"] is False
         and result["final_story_state_committed"] is False,
         "B04 Q25 not authentic read-only evidence")
    must(evidence["final_location"]["location_id"] == "STUDIO"
         and "studio" in evidence["final_location"]["quote"].lower()
         and [d["location_id"] for d in evidence["discovered_locations"]] == ["STUDIO"]
         and "studio" in evidence["discovered_locations"][0]["quote"].lower(),
         "Emir's real STUDIO arrival not supported")
    must([(v["obligation"], v["status"]) for v in evidence["open_obligation_outcomes"]]
         == [(o, "OPEN") for o in bundle["source"]["pack"]["open_obligations"]],
         "B04 spent paint/missing map cannot be falsely closed")
    result["schema"] = SCHEMA
    return result

def _write(path, value):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(canonical_json(value)+b"\n")
        f.flush()
        os.fsync(f.fileno())

def q25_once(bundle, claim_root, *, transport):
    root = Path(claim_root)
    must(root.is_dir() and not root.is_symlink(),
         "Missing protected B04 one-shot Q25 root")
    wire = b04_q25_wire(bundle)
    folder = root / RUN_NAME
    folder.mkdir(mode=0o700, exist_ok=False)
    _write(folder/"00-intent.json", {
        "schema":SCHEMA, "case_id":"B04",
        "source_pack_sha256":SOURCE_SHA, "spine_sha256":SPINE_SHA,
        "story_sha256":STORY_SHA,
        "request_sha256":hashlib.sha256(canonical_json(wire)).hexdigest(),
        "maximum_model_posts":1,"stage_cost_cap_usd":format(COST_CAP,"f"),
        "prior_conservative_budget_reserved_usd":format(PRIOR_RESERVED,"f"),
        "user_total_cap_usd":format(USER_CAP,"f"),
        "automatic_retry":False,"production_state_write_authorized":False,
    })
    response = None
    try:
        response = transport(wire)
        result = check_b04_response(bundle,response)
        _write(folder/"01-q25-evidence.json",result)
        return result
    except Exception as exc:
        usage = response.get("usage") if isinstance(response,dict) else None
        price=None
        if isinstance(usage,dict):
            try: price=money(usage.get("cost"))
            except HarnessStop: pass
        gid=response.get("id") if isinstance(response,dict) else None
        if not (isinstance(gid,str) and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",gid)):
            gid=None
        reason=(SAFE_FAILURE_CODE.get(str(exc),"B04_Q25_CONTRACT_REJECT")
                if isinstance(exc,HarnessStop) else "B04_Q25_PROVIDER_OR_UNKNOWN")
        if not (folder/"01-q25-evidence.json").exists():
            _write(folder/"01-q25-evidence.json",{
                "schema":SCHEMA,"case_id":"B04","status":"STOP_UNKNOWN_OR_INVALID",
                "safe_failure_code":reason,"provider_generation_id":gid,
                "provider_reported_cost_usd":format(price,"f") if price is not None else None,
                "source_story_sha256":STORY_SHA,"model_post_attempt_consumed":True,
                "automatic_retry":False,"production_state_write_authorized":False,
            })
        raise HarnessStop("B04 Q25 attempt consumed, no retry: "+reason) from None

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root",default=".")
    p.add_argument("--producer-root")
    p.add_argument("--quality-root")
    p.add_argument("--master-root")
    p.add_argument("--q25-root")
    p.add_argument("--paid-once",action="store_true")
    a=p.parse_args()
    if not a.paid_once:
        print(json.dumps({"case_id":"B04","provider_calls":0,"stage_cap_usd":"0.050",
                          "production_state_write_authorized":False},sort_keys=True))
        return
    must(os.getenv("LUMI_P441_B04_Q25") == "ONE_REAL_B04_MASTER_Q25",
         "No separate B04 paid single-use Q25 grant")
    must(all((a.producer_root,a.quality_root,a.master_root,a.q25_root)),
         "Protected original B04 source chain missing")
    key=os.getenv("OPENROUTER_API_KEY","")
    must(key.startswith("sk-or-"),"OpenRouter inference key unavailable")
    bundle=load_b04_bundle(a.repo_root,a.producer_root,a.quality_root,a.master_root)
    result=q25_once(bundle,a.q25_root,transport=lambda body:https_post_once(key,body))
    print(json.dumps({"case_id":"B04","q25_generation_id":result["generation_id"],
                      "provider_reported_cost_usd":result["provider_reported_cost_usd"],
                      "final_location_proposal":result["evidence_proposal"]["final_location"]["location_id"],
                      "state_committed":False,"production_state_write_authorized":False},sort_keys=True))

if __name__=="__main__":
    main()
