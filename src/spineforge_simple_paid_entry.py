"""Generic shared-reservation entry; never creates its own paid authorization."""
import argparse
import json
import os
from pathlib import Path
from src.spineforge_production_reservations_v2 import GitHubLedgerStoreV2,run_reserved,ReservationError
from src.spineforge_v19_transport import _request_once
from src.spineforge_simple_story import execute,prepare
from src.spineforge_relay_v1_q5t import save


def sanitized_failure(exc,secret):
    def clean(value):
        if isinstance(value,str):return value.replace(secret,"[REDACTED]") if secret else value
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,dict):
            forbidden={"authorization","api_key","apikey","api-key","x-api-key","headers","token","access_token","refresh_token","password","secret"}
            return {k:clean(v) for k,v in value.items() if k.lower() not in forbidden}
        return value
    trace=getattr(exc,"trace",None) or {}
    fields={k:trace[k] for k in ("stage","status_code","model","request_class","attempts","retry_suppressed","error_body","error","raw_usage","usage","cost") if k in trace}
    return dict(failure_type=type(exc).__name__,automatic_retry=False,diagnostics=clean(fields))


def workspace_path(value,prefix):
    root=Path.cwd().resolve();path=(root/value).resolve()
    if not path.is_relative_to((root/prefix).resolve()):raise ReservationError("Path outside approved workspace area")
    return path.relative_to(root)


def main():
    parser=argparse.ArgumentParser()
    for name in ("repository","grant-id","scope-id","executor-id","request","seed","freeze","config","preflight","output"):
        parser.add_argument("--"+name,required=True)
    args=parser.parse_args()
    try:
        paths={name:workspace_path(getattr(args,name),"tests/fixtures") for name in ("request","seed","freeze","config")}
        pfpath=workspace_path(args.preflight,"evidence/spineforge-relay")
        output=workspace_path(args.output,"evidence/spineforge-relay")
        if output.exists() or output==Path("evidence/spineforge-relay"):raise ReservationError("Fresh output required")
        preflight=json.loads(pfpath.read_text(encoding="utf8"))
        if preflight["config"].get("budget_policy")!="BETWEEN_CALLS":raise ReservationError("V2 budget policy required")
        if preflight!=prepare(paths["request"],paths["seed"],paths["freeze"],paths["config"]):raise ReservationError("Frozen pipeline preflight drift")
        token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN");key=os.environ.get("OPENROUTER_API_KEY")
        if not token or not key:raise ReservationError("Credentials missing")
        store=GitHubLedgerStoreV2(repository=args.repository,token=token)
        count=0
        def capture(**kwargs):
            nonlocal count
            count+=1
            root=output/"transport-captures";root.mkdir(parents=True,exist_ok=True)
            prefix=root/f"dispatch-{count}"
            save(str(prefix)+"-input.json",{k:v for k,v in kwargs.items() if k!="api_key"})
            try:
                text,body,actual=_request_once(**kwargs)
                save(str(prefix)+"-response.json",{k:body[k] for k in ("id","model","choices","usage") if k in body})
                save(str(prefix)+"-request.json",actual)
                return text,body,actual
            except Exception as exc:
                save(str(prefix)+"-failure.json",sanitized_failure(exc,kwargs.get("api_key")));raise
        def invoke(call):
            try:
                return execute(request_path=paths["request"],seed_path=paths["seed"],freeze_path=paths["freeze"],config_path=paths["config"],
                    preflight=preflight,output=output,api_key=key,call_fn=call)
            finally:
                output.mkdir(parents=True,exist_ok=True)
                save(output/"shared-authorization-receipt.json",dict(grant_id=args.grant_id,scope_id=args.scope_id,executor_id=args.executor_id,
                    shared_authority_used=True,checkout_local_fallback=False,automatic_retry=False))
        result=run_reserved(store=store,grant_id=args.grant_id,scope_id=args.scope_id,preflight=preflight,executor_id=args.executor_id,invoke=invoke,transport=capture)
        print(json.dumps({k:result.get(k) for k in ("status","phase","provider_calls","known_cost_usd","usage_complete")}))
        return 0 if result["status"]=="ACCEPT" else 2
    except Exception as exc:
        print("Generic execution denied/stopped without retry: "+type(exc).__name__);return 2


if __name__=="__main__":raise SystemExit(main())
