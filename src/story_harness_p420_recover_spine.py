"""P4.20 read-only recovery of ORIGINAL B01-r05 SpineForge content by generation ID.

No model generation, no retry, no cost claim, no guessed/reconstructed Spine.
If OpenRouter account does not store this completion, explicit not-recoverable.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, approve_spine_for_writer
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p420-generation-content-recovery.v1"
GEN_ID = "gen-1791912726-aHBjPEj5p3CU0qvEv6im"
EXPECTED_SPINE = "4931ea2bf744d001137d4cdcd7bb6d2d39f19e52b82f05c4972941a8b64a9054"
SOURCE_PACK = "91854710f46db13ee2599d567ca2fcbbcd945af50515a779ddee58211ee050dc"
ROOT_NAME = "p420-r05-spine-recovery-v01"
ENDPOINT = "https://openrouter.ai/api/v1/generation/content?id=" + GEN_ID
MAX_BODY = 131072


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HarnessStop("Generation-content redirected, deny request")


def must(condition, message):
    if not condition:
        raise HarnessStop(message)


def exact_source(repo_root):
    plan = load_plan(repo_root)
    case = next(c for c in plan["cases"] if c["id"] == "B01")
    pack = compile_case(case)
    must(pack["pack_sha256"] == SOURCE_PACK, "B01 frozen source pack drift")
    return pack


def read_content_once(api_key, *, opener=None):
    must(type(api_key) is str and api_key.startswith("sk-or-") and
         10 <= len(api_key) <= 256, "Missing inference key for read-only retrieval")
    req=urllib.request.Request(
        ENDPOINT, method="GET",
        headers={"Authorization":"Bearer "+api_key,
                 "Accept":"application/json"},
    )
    open_fn=(opener or urllib.request.build_opener(_NoRedirect())).open
    try:
        with open_fn(req,timeout=15) as response:
            must(response.status==200 and response.geturl()==ENDPOINT,
                 "Unexpected generation-content URL/status")
            data=response.read(MAX_BODY+1)
            must(len(data)<=MAX_BODY,"Large generation-content refused")
        payload=json.loads(data)
        must(type(payload) is dict and type(payload.get("data")) is dict,
             "Malformed generation content response")
        return {"http_status":200,"data":payload["data"]}
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403,404):
            return {"http_status":exc.code,"data":None}
        raise HarnessStop("Provider generation-content request unsuccessful") from None
    except HarnessStop:
        raise
    except Exception:
        raise HarnessStop("Provider content retrieval unknown, no repeated query") from None


def verify_original_completion(pack, data, *, expected_spine_sha256=EXPECTED_SPINE):
    must(type(data) is dict and
         type(data.get("output")) is dict,
         "Generation content not recorded by provider")
    raw = data["output"].get("completion")
    must(type(raw) is str and 0<len(raw)<=MAX_BODY,
         "Provider saved no recoverable text completion")
    try:
        outer=json.loads(raw)
        must(type(outer) is dict, "Saved completion is not a JSON object")
        if set(outer)=={"source_pack_sha256","spine_summary","beats_json"}:
            must(type(outer["beats_json"]) is str, "Saved beats_json not string")
            beats=json.loads(outer["beats_json"])
            obj={"source_pack_sha256":outer["source_pack_sha256"],
                 "spine_summary":outer["spine_summary"],
                 "beats":beats}
        else:
            obj=outer
    except (ValueError,TypeError,KeyError):
        raise HarnessStop("Saved model output cannot be parsed as original Spine") from None
    prepared=approve_spine_for_writer(pack,obj)
    must(prepared["spine_sha256"]==expected_spine_sha256,
         "Provider completion is not exact original r05 Spine SHA")
    return prepared


def _write(path,obj):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):
        flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(canonical_json(obj)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def recover_once(repo_root,run_root,api_key,*,transport=read_content_once,
                 expected_spine_sha256=EXPECTED_SPINE):
    pack=exact_source(repo_root)
    root=Path(run_root)
    must(root.is_dir() and not root.is_symlink(),
         "Private persistent read-only recovery run root required")
    claim=root/ROOT_NAME
    claim.mkdir(mode=0o700,exist_ok=False)
    _write(claim/"00-intent.json",{
        "schema":SCHEMA,"generation_id":GEN_ID,
        "source_pack_sha256":pack["pack_sha256"],
        "expected_spine_sha256":expected_spine_sha256,
        "model_posts_allowed":0,
        "retrieval_method":"READ_ONLY_GET",
        "retry_allowed":False,
    })
    try:
        response=transport(api_key)
        must(type(response) is dict and
             type(response.get("http_status")) is int,
             "Invalid generation-content transport receipt")
        status=response["http_status"]
        if status in (401,403,404):
            result={"schema":SCHEMA,"status":"CONTENT_UNAVAILABLE",
                    "http_status":status,"model_posts":0,
                    "new_model_spend_usd":"0",
                    "spine_recovered":False,"quality_accepted":False}
        else:
            must(status==200,"Unexpected generation-content response status")
            prepared=verify_original_completion(pack,response.get("data"),
                     expected_spine_sha256=expected_spine_sha256)
            result={"schema":SCHEMA,"status":"EXACT_ORIGINAL_SPINE_RECOVERED",
                    "http_status":200,"model_posts":0,
                    "new_model_spend_usd":"0",
                    "spine_recovered":True,"quality_accepted":False,
                    "source_pack_sha256":pack["pack_sha256"],
                    "spine_sha256":prepared["spine_sha256"],
                    "provider_generation_id":GEN_ID}
            # An immutable source artifact is needed before any audit.
            _write(claim/"original-spine.json",prepared)
        _write(claim/"01-receipt.json",result)
        return result
    except Exception:
        if not (claim/"01-receipt.json").exists():
            _write(claim/"01-receipt.json",{
                "schema":SCHEMA,"status":"RECOVERY_STOP_UNKNOWN",
                "model_posts":0,"new_model_spend_usd":"0",
                "spine_recovered":False,"quality_accepted":False,
                "retry_allowed":False,
            })
        raise HarnessStop("Original generation-content retrieval not admitted") from None


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--run-root")
    parser.add_argument("--recover-once",action="store_true")
    args=parser.parse_args()
    if not args.recover_once:
        print(json.dumps({"schema":SCHEMA,"model_posts":0,
                          "live_read_only_GET":False,
                          "spine_recovered":False,
                          "expected_story_source":SOURCE_PACK},
                         sort_keys=True))
    else:
        must(os.getenv("LUMI_P420_READ_ONLY")=="SINGLE_GENERATION_CONTENT_LOOKUP",
             "Read-only recovery not explicitly armed")
        result=recover_once(args.repo_root,args.run_root,
                            os.getenv("OPENROUTER_API_KEY",""))
        print(json.dumps(result,sort_keys=True))
