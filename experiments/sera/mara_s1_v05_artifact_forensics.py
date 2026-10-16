"""Offline forensic inspection of one frozen SERA M3.5 run artifact.

No model calls, no database writes, no raw prose output to CI logs.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

SOURCE_RUN = 38849464433
SOURCE_SHA = "80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03"


def inspect(path: Path) -> dict:
    raw_bytes = path.read_bytes()
    d = json.loads(raw_bytes)
    if (d.get("protocol") != "sera.mara-s1-typed-live.v0.5" or
        d.get("source_prose_sha256") != SOURCE_SHA or
        d.get("model_requested") != "google/gemini-3.7-flash" or
        d.get("launch_id") !=
            "sera-mara-s1-typed-v05-once-38849464433" or
        d.get("provider_attempts") != 1 or
        d.get("production_db_writes") != 0 or
        d.get("commit_authorized") is not False):
        raise ValueError("V05_ARTIFACT_PROVENANCE_INVALID")
    usage = d.get("provider_usage") or {}
    content = d.get("raw_content")
    if content is not None and not isinstance(content, str):
        raise ValueError("V05_ARTIFACT_CONTENT_INVALID")
    parsed = None
    parseable = False
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            parseable = True
        except ValueError:
            pass
    return {
        "protocol": "sera.mara-s1-v05-artifact-forensics.v0.1",
        "source_run": SOURCE_RUN,
        "source_result_sha256": sha256(raw_bytes).hexdigest(),
        "status": d["status"],
        "error_code": d.get("error_code"),
        "model": d["model_requested"],
        "observed_model": d.get("observed_model"),
        "finish_reason": d.get("finish_reason"),
        "provider_usage": usage,
        "provider_reported_cost": d.get("provider_reported_cost"),
        "raw_content_length": len(content) if content else 0,
        "raw_content_sha256": sha256(content.encode()).hexdigest()
            if content else None,
        "json_parseable": parseable,
        "json_top_level_keys": sorted(parsed) if isinstance(parsed, dict) else None,
        "raw_output_not_reprinted": True,
        "commit_authorized": False,
        "production_db_writes": 0,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("result_json", type=Path)
    args = ap.parse_args()
    print(json.dumps(inspect(args.result_json), ensure_ascii=False, indent=2))
