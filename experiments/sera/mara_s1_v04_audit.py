"""SERA v0.4 — read-only audit of the archived 243-word Mara scene.

NOT a new model run, gold truth set, or state commit. The nine candidate
annotations are analyst curated and their exact quote spans are rechecked.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.mara_s1_live import make_entry
from experiments.sera.world_state_v02 import canonical

PATH = (Path(__file__).resolve().parent
        / "fixtures/mara_s1_real_eventgraph_candidates_v03.json")
EXPECTED_SHA = "80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03"


def audit_real_mara(path: Path = PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    prose = data["prose"]
    if sha256(prose.encode("utf-8")).hexdigest() != EXPECTED_SHA:
        raise ValueError("MARA_PROSE_HASH_MISMATCH")
    if data.get("source_prose_sha256") != EXPECTED_SHA:
        raise ValueError("MARA_PROSE_METADATA_MISMATCH")
    if data.get("source_type") != "ANALYST_CURATED_LIVE_SCENE_INSPECTION":
        raise ValueError("MARA_SOURCE_TYPE_INVALID")
    if data.get("production_commit_authorized") is not False:
        raise ValueError("MARA_PRODUCTION_COMMIT_FORBIDDEN")
    if not isinstance(data.get("candidates"), list) or len(data["candidates"]) != 9:
        raise ValueError("MARA_ANNOTATED_EVENT_COUNT_INVALID")

    entry = make_entry()
    physical_missing: set[str] = set()
    reported_topic_refs: set[str] = set()
    rows = []
    seen = set()
    for i, event in enumerate(data["candidates"], start=1):
        cid = event["candidate_id"]
        if cid in seen or event["time"]["scene_ordinal"] != i:
            raise ValueError("MARA_EVENT_ID_OR_ORDINAL_INVALID")
        seen.add(cid)
        ev = event["evidence"]
        start, end = ev["start"], ev["end"]
        if (type(start) is not int or type(end) is not int or
            not 0 <= start < end <= len(prose) or
            prose[start:end] != ev["quote"]):
            raise ValueError(f"MARA_EVIDENCE_SPAN_MISMATCH:{cid}")
        if event["status"] != "HOLD" or event["typed_world_event"] is not None:
            raise ValueError(f"MARA_UNAUTHORIZED_PROMOTION:{cid}")
        if event["time"]["exact_minute"] is not None:
            raise ValueError(f"MARA_UNGROUNDED_ACTION_CLOCK:{cid}")

        blockers = set(event["blockers"])
        blockers.add("V04_UNRESOLVED_TIME_AND_EVENT_SCHEMA")
        for obj in event["objects"]:
            ident = obj["id"]
            if ident not in entry["entities"]:
                if ident.startswith("new:"):
                    physical_missing.add(ident)
                    blockers.add("V04_PHYSICAL_ENTITY_INTRODUCTION_REQUIRED")
                elif obj["role"] == "TOPIC":
                    reported_topic_refs.add(ident)
                    blockers.add("V04_TOPIC_REF_NOT_A_PHYSICAL_PRESENCE")
                else:
                    blockers.add("V04_UNREGISTERED_OBJECT_REFERENCE")
        rows.append({
            "event_id": cid,
            "ordinal": i,
            "epistemic": event["epistemic"],
            "object_refs": [o["id"] for o in event["objects"]],
            "caused_by": list(event["caused_by"]),
            "quote": ev["quote"],
            "blockers": sorted(blockers),
            "status": "HOLD",
            "commit_authorized": False,
        })
    return {
        "protocol": "sera.mara-s1-structural-audit.v0.4",
        "source_type": data["source_type"],
        "source_prose_sha256": EXPECTED_SHA,
        "candidate_count": len(rows),
        "candidate_statuses": dict(Counter(r["status"] for r in rows)),
        "unregistered_physical_candidates": sorted(physical_missing),
        "unregistered_reported_topics": sorted(reported_topic_refs),
        "prior_live_coverage": "HOLD",
        "prior_live_jev": "ESCALATE",
        "eventgraph_committed_count": 0,
        "production_db_writes": 0,
        "commit_authorized": False,
        "rows": rows,
    }


if __name__ == "__main__":
    print(json.dumps(audit_real_mara(), ensure_ascii=False, indent=2))
