import json
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import pytest
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_reservations import (
    PaidGrantV1, PaidLedgerV1, GitHubLedgerStore, ReservationError, run_reserved,
)

PREFLIGHT = {"fixture": "bounded", "runner_preflight": {"fixture": "bounded"}}


class MemoryAuthority:
    """One authority shared by independent local/CI clients, with true SHA CAS."""
    def __init__(self, ledger, barrier=None):
        self.ledger, self.version = ledger, 0
        self.lock, self.barrier = threading.Lock(), barrier
        self.writes, self.fail_write = 0, None
        self.reads = 0
    def read(self, grant_id):
        with self.lock:
            self.reads += 1
            pair = self.version, self.ledger.model_copy(deep=True)
        if self.barrier is not None and pair[0] == 0:
            self.barrier.wait(timeout=5)
        return pair
    def write(self, grant_id, expected, ledger):
        with self.lock:
            self.writes += 1
            if self.writes == self.fail_write or self.version != expected:
                raise ReservationError("CAS rejected/uncertain")
            self.ledger = ledger.model_copy(deep=True)
            self.version += 1
            return self.version


def authority(barrier=None):
    grant = PaidGrantV1(id="approved", approval_evidence_sha256="a"*64,
        max_calls=4, max_cost_usd="0.60", scopes=[dict(id=s, preflight_sha256=canonical_sha256(PREFLIGHT),
        max_calls=2, max_cost_usd="0.40", allowed_models=["qualified"]) for s in ("A", "B")])
    return MemoryAuthority(PaidLedgerV1(grant=grant,status="OPEN"),barrier)


@pytest.fixture(autouse=True)
def fake_rates(monkeypatch):
    import src.model_registry
    monkeypatch.setattr(src.model_registry,"require_qualification_runtime_profile",lambda model: {
        "metadata":{"pricing_usd_per_million_tokens":{"input":0,"output":0}}})


def usage(cost=0.10):
    return "text", {"usage":{"cost":cost,"prompt_tokens":10,"completion_tokens":10,"total_tokens":20}}, {}


def execute(store, invoke, transport, scope="A", preflight=PREFLIGHT):
    return run_reserved(store=store,grant_id="approved",scope_id=scope,preflight=preflight,
                        executor_id=threading.current_thread().name,invoke=invoke,transport=transport)


def one(call):
    return call(model="qualified",max_tokens=100,user_prompt="story",api_key="never-store-this")


def test_concurrent_local_and_ci_only_one_dispatches():
    store = authority(threading.Barrier(2))
    calls = []
    def transport(**kwargs): calls.append(kwargs); return usage()
    def actor():
        try: execute(store,one,transport); return "accepted"
        except ReservationError: return "denied"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:actor(),range(2)))
    assert sorted(results) == ["accepted","denied"]
    assert len(calls) == 1
    assert store.ledger.reservations["A"]["status"] == "SETTLED"


def test_two_different_scopes_racing_cannot_overreserve_shared_budget():
    store = authority(threading.Barrier(2)); calls=[]
    def transport(**kwargs): calls.append(1); return usage()
    def actor(scope):
        try: execute(store,one,transport,scope=scope); return True
        except ReservationError: return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(actor,("A","B")))
    assert sum(results) == 1 and len(calls) == 1


def test_consumed_scope_cannot_restart_in_another_checkout():
    store=authority();execute(store,one,lambda **k:usage())
    with pytest.raises(ReservationError,match="consumed"):
        execute(store,one,lambda **k:pytest.fail("No dispatch"))


def test_complete_settlement_frees_unused_budget_for_other_approved_scope():
    store=authority()
    execute(store,one,lambda **k:usage(),scope="A")
    execute(store,one,lambda **k:usage(),scope="B")
    assert sum(Decimal(r["actual_cost_usd"]) for r in store.ledger.reservations.values()) == Decimal("0.20")


def test_unknown_dispatch_keeps_whole_reservation_and_cannot_retry():
    store=authority();calls=[]
    def transport(**k):calls.append(1);raise TimeoutError("Uncertain")
    def invoke(call):
        for _ in range(2):
            try:one(call)
            except Exception:pass
        return {"status":"REJECT_NON_CONVERGENT"}
    with pytest.raises(ReservationError,match="uncertain"):
        execute(store,invoke,transport)
    assert len(calls)==1 and store.ledger.reservations["A"]["status"]=="UNCERTAIN"
    with pytest.raises(ReservationError,match="exhausted"):
        execute(store,one,lambda **k:pytest.fail("No fallback"),scope="B")


def test_lost_settlement_write_never_releases_reserved_budget():
    store=authority();store.fail_write=2
    with pytest.raises(ReservationError):execute(store,one,lambda **k:usage())
    assert store.ledger.reservations["A"]["status"]=="RESERVED"
    with pytest.raises(ReservationError):execute(store,one,lambda **k:pytest.fail("No retry"))


@pytest.mark.parametrize("defect",["closed","unknown_scope","wrong_preflight"])
def test_closed_or_unapproved_authority_never_dispatches(defect):
    store=authority();scope="A";pf=PREFLIGHT
    if defect=="closed":store.ledger.status="CLOSED"
    if defect=="unknown_scope":scope="invented"
    if defect=="wrong_preflight":pf={"fixture":"different"}
    with pytest.raises(ReservationError):execute(store,one,lambda **k:pytest.fail("No dispatch"),scope=scope,preflight=pf)
    assert store.writes==0


@pytest.mark.parametrize("bad",[None,True,-1,float("nan"),float("inf")])
def test_invalid_provider_spend_keeps_reservation_held(bad):
    store=authority()
    with pytest.raises(ReservationError):execute(store,one,lambda **k:usage(bad))
    assert store.ledger.reservations["A"]["status"]=="UNCERTAIN"


def test_missing_token_usage_is_uncertain():
    store=authority()
    def bad(**k):out=usage();del out[1]["usage"]["total_tokens"];return out
    with pytest.raises(KeyError):execute(store,one,bad)
    assert store.ledger.reservations["A"]["status"]=="UNCERTAIN"


def test_call_count_and_models_are_enforced_by_gated_transport():
    store=authority();calls=[]
    def transport(**k):calls.append(1);return usage()
    def three(call):one(call);one(call);one(call)
    with pytest.raises(ReservationError):execute(store,three,transport)
    assert len(calls)==2
    with pytest.raises(ReservationError):execute(authority(),lambda call:call(model="unapproved"),transport)
    assert len(calls)==2


def test_conservative_cost_denial_happens_before_dispatch(monkeypatch):
    import src.model_registry
    monkeypatch.setattr(src.model_registry,"require_qualification_runtime_profile",lambda model:{
        "metadata":{"pricing_usd_per_million_tokens":{"input":100000,"output":100000}}})
    with pytest.raises(ReservationError,match="spend ceiling"):
        execute(authority(),one,lambda **k:pytest.fail("No dispatch"))


def test_registry_network_error_is_sanitized_and_has_no_local_fallback():
    class Offline:
        def request(self,*a,**kw):raise TimeoutError("secret-token")
    store=GitHubLedgerStore(repository="owner/lab",token="secret-token",session=Offline())
    with pytest.raises(ReservationError) as error:
        execute(store,one,lambda **k:pytest.fail("No local fallback"))
    assert "secret-token" not in str(error.value)


def test_registry_conflict_denies_claim_without_retry():
    class Response:
        status_code=409
    class Conflict:
        count=0
        def request(self,*a,**kw):self.count+=1;return Response()
    session=Conflict();store=GitHubLedgerStore(repository="owner/lab",token="token",session=session)
    with pytest.raises(ReservationError,match="409"):
        store.write("approved","old-sha",authority().ledger)
    assert session.count==1


def test_revocation_between_calls_prevents_the_second_dispatch():
    store=authority();calls=[]
    def transport(**k):calls.append(1);return usage()
    def invoke(call):
        one(call)
        store.ledger.status="CLOSED"
        one(call)
    with pytest.raises(ReservationError,match="revoked"):
        execute(store,invoke,transport)
    assert len(calls)==1 and store.ledger.status=="CLOSED"


def test_authority_lost_after_reservation_never_dispatches():
    store=authority();normal_read=store.read
    def read(gid):
        if store.version:raise ReservationError("Authority offline")
        return normal_read(gid)
    store.read=read
    with pytest.raises(ReservationError):execute(store,one,lambda **k:pytest.fail("No dispatch"))
    assert store.ledger.reservations["A"]["status"]=="RESERVED"


def test_missing_registered_grant_never_creates_a_local_claim():
    class Missing:
        count=0
        def request(self,*a,**kw):
            self.count+=1
            return type("Response",(),{"status_code":404})()
    session=Missing();store=GitHubLedgerStore(repository="owner/lab",token="token",session=session)
    with pytest.raises(ReservationError,match="404"):
        execute(store,one,lambda **k:pytest.fail("No dispatch"))
    assert session.count==1


@pytest.mark.parametrize("case",["closed","accept","drift"])
def test_common_cli_gates_the_actual_runner_transport(tmp_path,monkeypatch,capsys,case):
    import sys
    import src.spineforge_relay_v1_paid_entry as entry
    store=authority()
    closed=case=="closed"
    if closed:store.ledger.status="CLOSED"
    monkeypatch.chdir(tmp_path)
    fixture=tmp_path/"tests/fixtures/story.json";fixture.parent.mkdir(parents=True);fixture.write_text("{}")
    pf=tmp_path/"evidence/spineforge-relay/preflight.json";pf.parent.mkdir(parents=True);pf.write_text(json.dumps(PREFLIGHT))
    monkeypatch.setenv("GH_TOKEN","synthetic-registry-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY","synthetic-provider-secret")
    monkeypatch.setattr(entry,"GitHubLedgerStore",lambda **k:store)
    def prepare_fixture(path):
        assert not path.is_absolute()
        return {"changed":True} if case=="drift" else PREFLIGHT
    monkeypatch.setattr(entry,"prepare_reserved_story",prepare_fixture)
    calls=[]
    def transport(**kwargs):calls.append(1);return usage()
    monkeypatch.setattr(entry,"_request_once",transport)
    def runner(**kwargs):
        assert not closed
        kwargs["output"].mkdir(parents=True)
        kwargs["call_fn"](model="qualified",max_tokens=100,api_key=kwargs["api_key"])
        return {"status":"ACCEPT","known_cost_usd":0.10,"usage_complete":True}
    monkeypatch.setattr(entry,"execute_story",runner)
    monkeypatch.setattr(sys,"argv",["paid-entry","--repository","owner/lab","--grant-id","approved","--scope-id","A","--executor-id","local","--fixture","tests/fixtures/story.json","--preflight","evidence/spineforge-relay/preflight.json","--output","evidence/spineforge-relay/fresh"])
    assert entry.main() == (0 if case=="accept" else 2)
    assert len(calls) == (1 if case=="accept" else 0)
    assert store.reads == 0 if case=="drift" else store.reads>0
    stdout=capsys.readouterr().out
    assert "synthetic-provider-secret" not in stdout and "synthetic-registry-secret" not in stdout
    if case=="accept":
        receipt=json.loads((tmp_path/"evidence/spineforge-relay/fresh/shared-authorization-receipt.json").read_text())
        assert receipt["checkout_local_fallback"] is False


@pytest.mark.parametrize("path",["../outside.json","sources/reference.json","evidence/spineforge-relay/run.json"])
def test_cli_fixture_paths_cannot_escape_the_fixture_area(tmp_path,monkeypatch,path):
    from src.spineforge_relay_v1_paid_entry import workspace_path
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ReservationError):workspace_path(path,"tests/fixtures")


def relay_kwargs():
    return dict(api_key="synthetic-only",model="qualified",system_prompt="test",user_prompt="test",
        temperature=0.0,max_tokens=100,seed=None,request_class="spineforge_relay_v1_q5t_guard",
        response_format={"type":"text"},require_parameters=True)


def test_legacy_direct_transport_is_blocked_before_any_http(monkeypatch):
    import src.spineforge_v19_transport as transport
    from src.spineforge_relay_v1_lease_context import UnreservedRelayTransportError
    monkeypatch.setattr(transport.requests,"post",lambda *a,**k:pytest.fail("No HTTP"))
    with pytest.raises(UnreservedRelayTransportError):transport._request_once(**relay_kwargs())


@pytest.mark.parametrize("mode",["one","double","different_prompt"])
def test_single_use_transport_capability_is_bound_to_exact_call(monkeypatch,mode):
    import src.spineforge_v19_transport as transport
    from src.spineforge_relay_v1_lease_context import UnreservedRelayTransportError
    calls=[]
    class Response:
        status_code=200
        ok=True
        def json(self):return {"choices":[{"finish_reason":"stop","message":{"content":"synthetic prose"}}],"usage":usage()[1]["usage"]}
    def post(*a,**k):calls.append(1);return Response()
    monkeypatch.setattr(transport.requests,"post",post)
    monkeypatch.setattr(transport,"normalize_openrouter_request",lambda model,payload,**k:payload)
    store=authority()
    def provider(**kwargs):
        if mode=="different_prompt":kwargs["user_prompt"]="unapproved replacement"
        result=transport._request_once(**kwargs)
        if mode=="double":transport._request_once(**kwargs)
        return result
    invoke=lambda call:call(**relay_kwargs())
    if mode=="one":execute(store,invoke,provider)
    else:
        with pytest.raises(UnreservedRelayTransportError):execute(store,invoke,provider)
    assert len(calls)=={"one":1,"double":1,"different_prompt":0}[mode]


def test_corrupted_frozen_source_snapshot_cannot_pass(tmp_path,monkeypatch):
    from src.spineforge_relay_v1_source_archives import verify_historical_source
    import hashlib
    monkeypatch.chdir(tmp_path)
    original=b"original transport"
    sha=hashlib.sha256(original).hexdigest()
    source=tmp_path/"src/transport.py";source.parent.mkdir();source.write_bytes(b"new active gate")
    root=tmp_path/"evidence/spineforge-relay/frozen-sources";root.mkdir(parents=True)
    archive=root/(sha+".bin");archive.write_bytes(original)
    (root/"registry.json").write_text(json.dumps({"schema":"spineforge-relay.frozen-source-registry.v1","entries":[{"source_path":"src/transport.py","sha256":sha,"archive_path":str(archive)}]}))
    row={"path":"src/transport.py","sha256":sha}
    verify_historical_source(row)
    archive.write_bytes(b"corrupted")
    with pytest.raises(RuntimeError,match="corrupt frozen"):
        verify_historical_source(row)


def test_provider_per_call_overrun_holds_reservation_and_stops():
    store=authority()
    with pytest.raises(ReservationError,match="beyond reservation"):
        execute(store,one,lambda **k:usage(0.20))
    assert store.ledger.reservations["A"]["status"]=="UNCERTAIN"


def test_reserved_preflight_binds_gate_sources_with_relative_paths(monkeypatch):
    import src.spineforge_relay_v1_paid_entry as entry
    from pathlib import Path
    monkeypatch.setattr(entry,"prepare_story",lambda fixture:{"fixture":fixture.as_posix()})
    relative=Path("tests/fixtures/example.json")
    first=entry.prepare_reserved_story(relative)
    assert first==entry.prepare_reserved_story(relative.resolve())
    assert first["fixture"]=="tests/fixtures/example.json"
    assert {row["path"] for row in first["gate_sources"]} >= {
        "src/spineforge_relay_v1_reservations.py","src/spineforge_relay_v1_lease_context.py"}


def test_concurrent_calls_cannot_share_one_scope_dispatch_slot():
    store=authority();entered=threading.Event();release=threading.Event();calls=[]
    def transport(**k):
        calls.append(1);entered.set();assert release.wait(timeout=5);return usage()
    def invoke(call):
        with ThreadPoolExecutor(max_workers=1) as pool:
            first=pool.submit(one,call)
            assert entered.wait(timeout=5)
            try:
                with pytest.raises(ReservationError,match="Concurrent"):
                    one(call)
            finally:release.set()
            return first.result()
    with pytest.raises(ReservationError,match="uncertain"):
        execute(store,invoke,transport)
    assert len(calls)==1 and store.ledger.reservations["A"]["status"]=="UNCERTAIN"


def test_boolean_cost_cannot_be_registered_as_money():
    payload=authority().ledger.grant.model_dump(mode="json")
    payload["max_cost_usd"]=True
    with pytest.raises(ReservationError):PaidGrantV1.model_validate(payload)
