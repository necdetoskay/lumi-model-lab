from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def verify_frozen_lane(profile_path:Path)->dict[str,Any]:
    profile=json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version")!="story-lane-profile.v2":
        raise RuntimeError("Frozen lane requires story-lane-profile.v2.")
    freeze=profile.get("runtime_freeze") or {}
    if freeze.get("enabled") is not True:
        raise RuntimeError("Lane runtime freeze is not enabled.")
    files=freeze.get("files") or []
    if not files:
        raise RuntimeError("Frozen lane has no runtime file hashes.")

    mismatches=[]
    for row in files:
        path=Path(str(row["path"]))
        expected=str(row["sha256"])
        if not path.exists():
            mismatches.append({"path":str(path),"reason":"missing"})
            continue
        actual=sha256_file(path)
        if actual!=expected:
            mismatches.append({
                "path":str(path),
                "reason":"sha256_mismatch",
                "expected":expected,
                "actual":actual,
            })

    if mismatches:
        raise RuntimeError(
            "Frozen lane runtime changed: "+json.dumps(mismatches,ensure_ascii=False)
        )
    return {
        "lane_id":profile["lane_id"],
        "runtime_revision":freeze["runtime_revision"],
        "verified_files":len(files),
        "verified":True,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--profile",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(verify_frozen_lane(a.profile),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
