"""Append-only fixed-baseline budget journal for LUMI ten-case cohort.

This is an OFFLINE proof only, never a trusted provider account ledger.
Unlike case-by-case reserving, it reserves ALL ten cases before B01 begins.
No unknown charge can be released or retried. Journaling intent is durable
and the root is single-use. Files remain local evidence, not WORM storage.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_frozen_cohort_v1 import IDS, CAP, TRIAL_CAP
from src.story_harness_frozen_round_v1 import (
    simulate_seal, check_lock
)
from src.story_harness_cohort_launch_gate_v1 import (
    reconcile_cumulative_budget, usd, sha_obj, must
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-ten-budget-journal-offline.v1"
VALID = {"REJECT", "ACCEPT_CLAIMED", "OPERATIONAL_STOP"}
NAME = re.compile(r"^lumi-ten-[a-z0-9]{6,28}$")

def exclusive(path, data):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as h:
        h.write(canonical_json(data) + b"\n")
        h.flush()
        os.fsync(h.fileno())
    if os.name == "posix":
        parent = os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)

class OfflineCohortBudgetJournal:
    """A baseline of exactly ten claims and $4.40 PRE-reserved globally."""
    def __init__(self, repo_root, claims_root, *, run_id, snapshot,
                 clock=None):
        must(type(run_id) is str and NAME.fullmatch(run_id),
             "UNTRUSTED_RUN_ID")
        self.repo = Path(repo_root)
        root = Path(claims_root)
        must(root.is_dir() and not root.is_symlink() and
             not root.resolve().is_relative_to(self.repo.resolve()),
             "UNSAFE_LEDGER_ROOT")
        self.seal = simulate_seal(self.repo)
        check_lock(self.repo, self.seal)
        self.finances = reconcile_cumulative_budget(snapshot, now=clock)
        must(self.finances["all_required_ledger_claims_asserted"],
             "CLAIMED_EXTERNAL_LEDGER_INCOMPLETE")
        must(self.finances["first_ten_reserved_usd"] == format(
             10 * TRIAL_CAP, "f"), "WRONG_BASELINE_RESERVATION")
        self.root = root / run_id
        self.root.mkdir(mode=0o700, exist_ok=False)
        self.outcomes = []
        self.active = None
        self.halted = False
        self.spent = Decimal("0")
        self.untrusted_mock_only = True
        self.prior = usd(self.finances["prior_conservative_exposure_usd"])
        self.reservation = Decimal("10") * TRIAL_CAP
        exclusive(self.root / "00-full-ten-reservation.json", {
            "schema": SCHEMA, "run_id": run_id,
            "harness_sha256": sha_obj(self.seal),
            "baseline_case_ids": list(IDS),
            "prior_conservative_exposure_usd": format(self.prior, "f"),
            "new_full_ten_reserved_usd": format(self.reservation, "f"),
            "max_total_user_cap_usd": format(CAP, "f"),
            "entire_batch_reserved_before_first_attempt": True,
            "financial_truth_externally_attested": False,
            "provider_model_calls_authorized": 0,
            "simulated_offline_only": True,
            "refund_unused_reservation_mid_cohort": False,
        })

    def _enforce(self):
        check_lock(self.repo, self.seal)
        must(not self.halted, "GLOBAL_COHORT_STOP_ALREADY_CONSUMED")
        must(self.prior + self.reservation <= CAP,
             "CUMULATIVE_USER_BUDGET")

    def begin(self, case_id):
        self._enforce()
        must(self.active is None and len(self.outcomes) < 10 and
             type(case_id) is str and case_id == IDS[len(self.outcomes)],
             "OUT_OF_ORDER_OR_DUPLICATE_ATTEMPT")
        path = self.root / f"{case_id}-01-intent.json"
        exclusive(path, {
            "schema": SCHEMA, "case_id": case_id,
            "harness_sha256": sha_obj(self.seal),
            "max_new_cost_usd": format(TRIAL_CAP, "f"),
            "intent_consumed_no_retry": True,
            "model_transport_used": False,
        })
        self.active = case_id

    def finish(self, case_id, *, provider_reported_usd, outcome):
        self._enforce()
        must(self.active == case_id and case_id == IDS[len(self.outcomes)] and
             outcome in VALID, "CASE_UNSETTLED_OR_INVALID")
        value = usd(provider_reported_usd)
        must(value <= TRIAL_CAP and
             self.spent + value <= self.reservation and
             self.prior + self.spent + value <= CAP,
             "KNOWN_COST_EXCEEDS_RESERVATION")
        row = {
            "schema": SCHEMA, "case_id": case_id, "outcome": outcome,
            "provider_reported_usd": format(value, "f"),
            "cumulative_reported_usd": format(self.spent + value, "f"),
            "provider_spending_externally_verified": False,
            "accepted_story_quality_certified": False,
            "story_hotfixes": 0, "provider_model_retries": 0,
        }
        exclusive(self.root / f"{case_id}-02-outcome.json", row)
        self.spent += value
        self.outcomes.append(outcome)
        self.active = None
        return row

    def unknown_stop(self, case_id):
        must(self.active == case_id, "UNKNOWN_STOP_WRONG_CASE")
        self.halted = True
        self.active = None
        exclusive(self.root / f"{case_id}-02-unknown-charge-stop.json", {
            "schema": SCHEMA, "case_id": case_id,
            "safe_status": "STOP_UNKNOWN_OR_INVALID",
            "unknown_charge_not_assumed_zero": True,
            "prior_holds_and_full_ten_reservation_not_released": True,
            "next_story_dispatch_forbidden": True,
            "model_calls_authorized": 0,
        })

    def report(self):
        return {
            "schema": SCHEMA, "attempts_settled": len(self.outcomes),
            "cohort_complete": len(self.outcomes) == 10 and not self.halted,
            "missing": list(IDS[len(self.outcomes):]),
            "reported_spend_usd": format(self.spent, "f"),
            "baseline_reservation_usd": format(self.reservation, "f"),
            "global_stop": self.halted, "active_case": self.active,
            "future_story_fix_allowed": len(self.outcomes) == 10 and not self.halted,
            "independent_provider_reconciliation": False,
            "real_provider_model_calls": 0,
            "paid_dispatch_authorized": False,
        }
