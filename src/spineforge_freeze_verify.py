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


def verify_spineforge_runtime(profile_path:Path)->dict[str,Any]:
    profile=json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("schema_version")!="spineforge-runtime-profile.v1":
        raise RuntimeError("Unsupported SpineForge runtime profile.")
    freeze=profile.get("runtime_freeze") or {}
    if freeze.get("enabled") is not True:
        raise RuntimeError("SpineForge runtime is not frozen.")
    files=list(freeze.get("files") or [])
    if not files:
        raise RuntimeError("SpineForge freeze has no file hashes.")

    mismatches=[]
    for row in files:
        path=Path(str(row["path"]))
        if not path.exists():
            mismatches.append({"path":str(path),"reason":"missing"})
            continue
        actual=sha256_file(path)
        if actual!=str(row["sha256"]):
            mismatches.append({
                "path":str(path),
                "reason":"sha256_mismatch",
                "expected":str(row["sha256"]),
                "actual":actual,
            })
    if mismatches:
        raise RuntimeError(
            "SpineForge frozen runtime changed: "
            +json.dumps(mismatches,ensure_ascii=False)
        )
    return {
        "runtime_id":profile["runtime_id"],
        "runtime_revision":freeze["runtime_revision"],
        "verified_files":len(files),
        "verified":True,
    }


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--profile",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(
        verify_spineforge_runtime(a.profile),
        ensure_ascii=False,indent=2
    ))


if __name__=="__main__":
    main()
