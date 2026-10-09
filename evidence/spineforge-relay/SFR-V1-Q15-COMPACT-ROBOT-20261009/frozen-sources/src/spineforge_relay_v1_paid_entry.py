"""Shared local/CI entrypoint. Grants must already exist in the remote registry."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from src.spineforge_relay_v1_reservations import GitHubLedgerStore, run_reserved, ReservationError
from src.spineforge_relay_v1_runner import execute_story, prepare as prepare_story
from src.spineforge_v19_transport import _request_once
from src.spineforge_relay_v1_q5t import save


def workspace_path(value, prefix):
    root = Path.cwd().resolve()
    path = (root/value).resolve()
    if not path.is_relative_to((root/prefix).resolve()):
        raise ReservationError("Path is outside the approved workspace area")
    return path


def prepare_reserved_story(fixture):
    """Freeze both the existing story runner and the outer reservation gate."""
    fixture = workspace_path(fixture, "tests/fixtures").relative_to(Path.cwd().resolve())
    sources = ["src/spineforge_relay_v1_paid_entry.py", "src/spineforge_relay_v1_reservations.py",
               "src/spineforge_relay_v1_lease_context.py", "src/spineforge_v19_transport.py", "requirements.txt"]
    runner_preflight = prepare_story(fixture)
    normalize_text = runner_preflight.get("schema") == "spineforge-relay.repeatability-preflight.v2"
    def source_sha(path):
        data = Path(path).read_bytes()
        if normalize_text:
            data = data.replace(b"\r\n", b"\n")
        return hashlib.sha256(data).hexdigest()
    return {"schema": "spineforge-relay.reserved-preflight.v1", "fixture": fixture.as_posix(),
            "registry_branch": "sfr-paid-reservations", "runner_preflight": runner_preflight,
            "gate_sources": [{"path": p, "sha256": source_sha(p)} for p in sources]}


def main():
    parser = argparse.ArgumentParser()
    for field in ("repository", "grant-id", "scope-id", "executor-id", "fixture", "preflight", "output"):
        parser.add_argument("--"+field, required=True)
    args = parser.parse_args()
    try:
        fixture = workspace_path(args.fixture, "tests/fixtures")
        preflight_path = workspace_path(args.preflight, "evidence/spineforge-relay")
        output = workspace_path(args.output, "evidence/spineforge-relay")
        if output.exists() or output == Path("evidence/spineforge-relay").resolve():
            raise ReservationError("Output must be a fresh evidence directory")
        preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
        # Frozen fixture paths must be identical across local and CI checkouts.
        fixture = fixture.relative_to(Path.cwd().resolve())
        if prepare_reserved_story(fixture) != preflight:
            raise ReservationError("Frozen story preflight drift; no reservation consumed")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not token or not api_key:
            raise ReservationError("Both registry and provider credentials are required")
        store = GitHubLedgerStore(repository=args.repository, token=token)
        def invoke(call):
            try:
                return execute_story(fixture_path=fixture, api_key=api_key, preflight=preflight["runner_preflight"], output=output, call_fn=call)
            finally:
                output.mkdir(parents=True, exist_ok=True)
                save(output/"shared-authorization-receipt.json", {
                    "grant_id": args.grant_id, "scope_id": args.scope_id,
                    "executor_id": args.executor_id, "shared_authority_used": True,
                    "checkout_local_fallback": False, "automatic_retry": False,
                })
        result = run_reserved(store=store, grant_id=args.grant_id, scope_id=args.scope_id,
                              preflight=preflight, executor_id=args.executor_id,
                              invoke=invoke, transport=_request_once)
        print(json.dumps({k: result.get(k) for k in ("status", "known_cost_usd", "usage_complete")}))
        return 0 if result.get("status") == "ACCEPT" else 2
    except Exception as exc:
        # Never print request headers, credentials or raw provider exceptions.
        print("Paid execution denied/stopped without retry: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
