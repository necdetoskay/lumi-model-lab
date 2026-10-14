"""One common B01..B10 SpineForge→Writer→QA→Master→Q25→State adapter.

NO ENTRYPOINT, NO SECRET, NO PROVIDER DISPATCH. Transport must be supplied
by a separately approved runner. Results from injected transport are only
STRUCTURAL/UNVERIFIED and never a genuine paid model or release ACCEPT.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from src.story_harness_runtime_v1 import RuntimeHarness
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p417_live_pilot import (
    BoundedOncePilot, MODEL, money, STAGE_MAX_USD, USD_CAP
)
from src.story_harness_p422_independent_audit import (
    verify_auditor_reply, STAGE_COST_CAP
)
from src.story_harness_p424_q25_evidence import COST_CAP
from src.story_harness_cohort_source_v1 import load_original_case, ORIGINAL_FILES
from src.story_harness_cohort_stages_v1 import (
    prepare_quality_request, make_pilot_bundle, prepare_real_q25_request,
    validate_real_q25_response, read_only_state_projection
)
from src.story_harness_frozen_cohort_v1 import IDS, CAP, TRIAL_CAP
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-common-end-to-end-transcript.v1"
STAGE_MAX = {
    "SPINEFORGE": STAGE_MAX_USD["SPINEFORGE"],
    "WRITER": STAGE_MAX_USD["WRITER"],
    "QUALITY": STAGE_COST_CAP,
    "Q25": COST_CAP,
}
MAX_POSTS = 4

def must(ok, reason):
    if not ok:
        raise HarnessStop("COMMON_PIPELINE_STOP_" + reason)

def exclusive(path, data):
    from src.story_harness_p423_master import write_exclusive
    write_exclusive(path, canonical_json(data) + b"\n")

class ProviderCostUnknown(HarnessStop):
    """Provider transport or charge unaccounted; global paid batch MUST STOP."""

class TrialLedger:
    """Charges from actual response envelopes; cannot assume missing cost is $0."""
    def __init__(self, transport, harness):
        must(callable(transport), "MISSING_TRANSPORT")
        must(isinstance(harness, RuntimeHarness), "HARNESS_INSTANCE_REQUIRED")
        self.harness = harness
        self.transport = transport
        self.total = Decimal("0")
        self.count = 0
        self.by_stage = {}
        self.unknown_cost = False
        self.generation_ids = {}
    def post(self, stage, body):
        must(stage in STAGE_MAX and stage not in self.by_stage and
             self.count < MAX_POSTS, "STAGE_REPLAY_OR_BAD_ORDER")
        must(body.get("model") == MODEL and body.get("stream") is False and
             body.get("provider", {}).get("allow_fallbacks") is False and
             body.get("usage") == {"include": True},
             "UNSAFE_PROVIDER_ROUTE")
        self.harness.authorize_stage(stage, body)
        self.count += 1  # consumed before potentially ambiguous provider POST
        try:
            response = self.transport(body)
        except Exception:
            self.unknown_cost = True
            raise ProviderCostUnknown("Transport may already have been billed") from None
        usage = response.get("usage") if type(response) is dict else None
        try:
            cost = money(usage.get("cost") if type(usage) is dict else None)
        except Exception:
            self.unknown_cost = True
            raise ProviderCostUnknown("Provider response cost missing/invalid") from None
        # The supplied data can be a mocked response; this ledger is NOT
        # provider-independent authentication, just arithmetic+contract.
        self.total += cost
        self.by_stage[stage] = cost
        self.generation_ids[stage] = response.get("id")
        if (cost <= 0 or cost > STAGE_MAX[stage] or
                self.total > TRIAL_CAP or
                self.total > CAP):
            self.unknown_cost = True
            raise ProviderCostUnknown("Provider cost exceeded bounded stage limit")
        return response

def run_one_case_with_injected_transport(repo_root, case_id, claim_root, *, transport, harness):
    """One new non-retryable attempt, all original artifacts written once.

    The caller must independently seal a versioned cohort lock and reconcile
    the $20 user aggregate limit before passing an actual paid transport.
    This function itself neither grants payment nor certifies real ACCEPT.
    """
    must(case_id in IDS, "UNKNOWN_CASE")
    must(isinstance(harness, RuntimeHarness) and
         harness.case_id == case_id, "HARNESS_NOT_BOUND_TO_CASE")
    harness.verify_immutable()
    root = Path(claim_root)
    must(root.is_dir() and not root.is_symlink(), "BAD_CLAIM_ROOT")
    folder = root / case_id
    folder.mkdir(mode=0o700, exist_ok=False)
    producer = folder / "producer"
    producer.mkdir(mode=0o700)
    plan = load_plan(repo_root)
    ledger = TrialLedger(transport, harness)
    exclusive(folder / "00-harness-receipt.json", harness.receipt())
    pilot = BoundedOncePilot(str(producer), case_id=case_id, plan=plan, run_variant="r06")
    try:
        pilot.execute(transport=lambda body: ledger.post(
            "SPINEFORGE" if ledger.count == 0 else "WRITER", body))
        trust = {
            name: hashlib.sha256((pilot.dir / name).read_bytes()).hexdigest()
            for name in ORIGINAL_FILES
        }
        # Materialize the source receipt/hashed artifacts BEFORE calling QA.
        exclusive(folder / "01-producer-trust.json", {
            "case_id": case_id, "original_file_sha256": trust,
            "externally_attested": False
        })
        source = load_original_case(repo_root, producer, case_id=case_id,
                                    trusted_file_sha256=trust)
        harness.bind_story(source)
        request = prepare_quality_request(source)
        exclusive(folder / "02-quality-intent.json", {
            "case_id": case_id,
            "story_sha256": source["story"]["story_sha256"],
            "request_sha256": hashlib.sha256(canonical_json(request)).hexdigest(),
            "at_most_one_post": True, "auto_retries": False
        })
        reply = ledger.post("QUALITY", request)
        audit = verify_auditor_reply(source, reply)
        exclusive(folder / "03-quality-receipt.json", audit)
        if audit["quality_initial_verdict"] == "REJECT":
            return report(case_id, folder, ledger, "REJECT", source=source)
        bundle = make_pilot_bundle(source, audit)
        master = folder / "ENGLISH_MASTER.txt"
        from src.story_harness_p423_master import write_exclusive
        write_exclusive(master, bundle["english_master_text"].encode("utf-8"))
        exclusive(folder / "04-master.json", bundle["master"])
        q25_wire = prepare_real_q25_request(bundle)
        exclusive(folder / "05-q25-intent.json", {
            "case_id": case_id, "story_sha256": source["story"]["story_sha256"],
            "request_sha256": hashlib.sha256(canonical_json(q25_wire)).hexdigest(),
            "at_most_one_post": True, "auto_retries": False
        })
        response = ledger.post("Q25", q25_wire)
        q25 = validate_real_q25_response(bundle, response)
        exclusive(folder / "06-q25-receipt.json", q25)
        final = read_only_state_projection(bundle, q25)
        exclusive(folder / "07-final-state-draft.json", final)
        must(final["story_sha256"] == source["story"]["story_sha256"] and
             final["production_state_write_authorized"] is False,
             "FINAL_STATE_NOT_SAME_STORY")
        harness.verify_immutable()
        return report(case_id, folder, ledger, "ACCEPT_CLAIMED", source=source)
    except ProviderCostUnknown:
        # NO retry and NO next paid case unless the unknown charge is reconciled.
        raise
    except Exception:
        # P4.17 may sanitize/re-wrap a transport error; never lose unknown
        # provider charge state just because the nested generator caught it.
        if ledger.unknown_cost:
            raise ProviderCostUnknown("Unknown billed charge: global STOP") from None
        # If cost was safely reported, a localized stage failure is a FAILURE,
        # not permission to modify Harness or run a second attempt.
        return report(case_id, folder, ledger, "OPERATIONAL_STOP")

def report(case_id, folder, ledger, status, *, source=None):
    must(status in ("REJECT", "ACCEPT_CLAIMED", "OPERATIONAL_STOP"),
         "INVALID_RESULT_STATUS")
    return {
        "schema": SCHEMA, "case_id": case_id, "status": status,
        "model_call_envelopes_observed": ledger.count,
        "transport_origin_independently_attested": False,
        "independent_quality_certified_for_release": False,
        "story_sha256": source["story"]["story_sha256"] if source else None,
        "provider_reported_stage_cost_usd": {
            k: format(v, "f") for k, v in ledger.by_stage.items()
        },
        "provider_reported_total_usd": format(ledger.total, "f"),
        "run_once_root": folder.name,
        "harness_manifest_sha256": ledger.harness.manifest_sha256,
        "harness_memory_sha256": ledger.harness.memory_snapshot_sha256,
        "harness_tools_invoked": list(ledger.harness.invoked),
        "manual_story_edits": 0, "automatic_retries": 0,
        "production_change": False,
    }
