# Story Harness P4.3 — Offline-only v21.5 runner / real-provider dispatch kill switch

**Status:** Experimental v21.5 **offline-only** pre-dispatch and callback integration, Draft PR #275, issue #287. **Date:** 2026-10-13.
**New API usage:** 0 calls, $0. No English Master, Q25 extraction, canonical StoryState commit, production or main merge.

## Why this is a separate frozen runner

Original immutable **v21.4** remains untouched, revalidated at pinned source Git
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`. P4.2 proved that the isolated final-audit diagnostic can safely retain *redacted* SHA/shape/error metadata after a malformed response. P4.3 wires this mechanism to the **same original adapter callback shape** that a real provider would eventually use:

```text
Pinned V21.4 source/story/profile verify
  → P4.3 pre-dispatch kill switch (OFFLINE_ONLY)
  → atomic, one-shot OFFLINE claim
  → original execute_paid_quality_once(simulation=True)
       → original initial audit adapter   → fake transport
       → original scene repair adapter    → fake transport
       → original targeted final audit    → fake transport
             ├ valid simulated response → simulated ACCEPT (NOT quality evidence)
             └ malformed/transport error → v21.5 diagnostic quarantine
                     └ redacted immutable 0600/O_EXCL/fsync receipt → REJECT
  → no real provider network, English Master seal or Q25
```

The actual engine is `src.spineforge_v21_paid_quality_once.execute_paid_quality_once` from frozen v21.4. Original audit/repair/final adapter functions run directly with a **fake** call_fn argument, rather than monkeypatching the original `simulate_case`. The target is the real callback boundary; **a real provider adapter is NOT selected or enabled**. The code does not claim a production-grade real provider integration.

The separate runner source `src/story_harness_p43_runner.py` is pinned by SHA-256 in the P4.3 control plane. Profile `configs/story_harness_p43_offline_runner.json` is separately frozen by SHA-256; it binds the original 12-year-old island story artifact ID, exact source story hash, approved Spine hash, original profile SHA, the P4.2 diagnostic module SHA, frozen model-slot names and the three-cost-stage topology.

## Hard STOP before paid provider dispatch

There is **no route** in the P4.3 profile to a real provider. The pure `pre_dispatch_gate()` rejects any requested:

- `REAL_PROVIDER` mode, simulated user grant, live endpoint, unverified price quote or pretend billable input token count;
- second workflow attempt, retry or repeat use of an offline run ID;
- model-slot substitution, more than three model calls, second scene repair or full-story final audit;
- positive paid/canonical/English Master/Q25 authorization bit;
- claims that the $0.10 quality target is a guaranteed provider hard cap.

An atomic `offline-once-<run_id>.claimed` 0600/EXCL marker permits each local fake-provider experiment ID at most **one** pass. **It is not a paid user authorization or a real per-user spending token.** On replay, FileExistsError occurs before another fake-provider attempt. Real user authorization is deliberately absent, not inferred from a previous consent.

For each modeled outgoing request the runner records **stage, UTF-8 payload byte count and original max output tokens (3000/3500/1800)**; no story prose or prompt is placed in the committed summary. These metrics support future exposure review but are **not actual billable token counts**, current provider pricing, routing verification, or upper bounds. A paid run must be separately reviewed and authorized, with endpoint/pricing/token-budget checks; it cannot be enabled by simply toggling the offline profile.

## Four actual original callback cases, no paid calls

| Case | Original runtime quality status | Real quality acceptance |
| --- | --- | --- |
| One scene repair and valid targeted final response | `ACCEPT` **synthetic** | Denied |
| Malformed final audit unexpected field | `REJECT_PROVIDER_FAILURE` | Denied |
| Final audit missing cost/usage | `REJECT_PROVIDER_FAILURE` | Denied |
| Final audit invalid JSON from provider transport | `REJECT_PROVIDER_FAILURE` | Denied |

Each uses three mock callback attempts. The final-audit adapter receives raw response or transport errors; the P4.2 quarantine writes safely redacted diagnostic evidence **before** rethrowing a sanitized error to the unchanged v21.4 quality runtime. No secret or original provider response prose is stored. Missing cost is recorded as **incomplete accounting**, never `$0`; original runtime can account fewer than the three attempted model calls in that negative case, and the report distinguishes both.

The standalone runner actually persists the original v21 simulation envelope/result and JSONL stage ledger inside an isolated temporary directory. It scans those files and private diagnostic records for injected fake provider secrets, then returns only a stable scrubbed summary. It executes the same original source validations and constrained repair topology. The original archived paid v21.3 rejection is preserved.

## Source, evidence and CI

- Immutable offline profile: `configs/story_harness_p43_offline_runner.json`.
- Experimental original-callback runner: `src/story_harness_p43_runner.py`.
- Replay + negative proof controller: `src/story_harness_p43.py`.
- Tests: `tests/test_story_harness_p43.py`.
- Committed generated summary: `evidence/story_harness_p43/pinned-v21-5-offline-runner-receipt.json`.
- Prior gate P4.2 and the same-story P3/P4 qualifications **run again** before the P4.3 result can be presented.

The 13 dedicated offline tests cover fixed source SHA/profile, mutated cost/budget/model/authorization policies, real-mode attempts, non-consuming fake user grant rejection, invalid run IDs, symlinked outputs, once-claim replay, live original bounded callback results, fabricated quality ACCEPT, absent diagnostic receipt, accounting incompleteness and leaked provider keys.

Current result:

```text
stop_reason = REAL_PAID_DISPATCH_DISABLED_OFFLINE_RUNNER_QUALIFIED
mode = OFFLINE_SINGLE_ATTEMPT_V21_5_RUNNER_ONLY
real_paid_user_authorization_granted = false
actual_english_master_accepted = false
english_master_seal_emitted = false
q25_handoff_emitted = false
production_state_write_executed = false
provider_calls = 0
provider_cost_usd = "0"
```

## What this does NOT solve

P4.3's GREEN means the offline runner and fail-closed callback boundary work, **not** that the original island story is good or that it could be safely dispatched now. The historical latest true quality decision remains `LOCAL_REPAIR_REQUIRED`; the old paid final audit failed and lost its raw answer.

Real authorization requires a **newly versioned, explicitly authorized real-run mode** with independently verified current pricing and exact request-time usage/spend exposure; retention/access policies for diagnostic output, a signed/consumed user-grant ledger, and separate English Master real-positive attestation. None are active here. Changing stage model slots is permitted only through an independently frozen profile qualification; this phase has no dynamic model-switching feature.

A provider-side hard cost cap is not guaranteed merely because the application rejects after observed stage usage. Do not interpret the original per-stage limits as a guaranteed budget.

Reproduce offline:

```sh
git worktree add --detach /tmp/lumi-p43-pinned 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' 'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P43_ROOT=/tmp/lumi-p43-pinned
python -m unittest discover -s tests -p 'test_story_harness_p43.py' -v
python -m src.story_harness_p43 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P43_ROOT" \
  --verify-report evidence/story_harness_p43/pinned-v21-5-offline-runner-receipt.json
```

