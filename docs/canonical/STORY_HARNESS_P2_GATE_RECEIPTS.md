# LUMI Story Harness P2 — Versioned StageResult + Executed Local Gate Receipts

**Status:** MODEL-LAB ONLY / read-only / no provider authorization / P2 partial qualification  
**Branch:** `experiment/story-harness-control-plane-v1` (Draft PR #275)  
**Source inputs:** Frozen six P1 artifacts from SpineForge V20 and Q25 (P1 source commit `2eb3d825b5baf8f0f16ccb23805f619d433c7236`).

## New capability

P0 had a mock sequential chain, P1 imported authentic **separate** historical cases.
P2 adds a typed and hashed *local check execution* envelope:

- `StageInput.v1`: original case identity, adapter, frozen source commit, imported manifest hash, exact SHA-256 digest of every required archived role.
- `GateReceipt.v1`: reference to `StageInput`, local gate ID and implementation-source SHA-256, artifact set fingerprint, and a status for the **actual integrity/schema check executed in the current process**.
- `StageResult.v1`: receipt hash, original historical gate decision *verbatim*, a fail-closed stop reason and explicit absence of authorization to execute another stage.
- `run P2`: each receipt is generated only after `inspect_historical` has freshly checked pinned artifact bytes/identities/schema. A user-provided receipt is never trusted as a stage gate: `verify_report` runs those same checks and compares every field to a newly derived report.

These bindings are cryptographic digests for **integrity**, not signatures/authentication of a user, model response, machine or human reviewer. A code hash proves which local verifier file the operator used; it is **not** a code-signing or remote attestation mechanism.

## Authority table

| P2 check | Verified this run? | What it does NOT prove |
|---|---|---|
| Frozen archive bytes equal pinned SHA-256 | YES | Remote branch authenticity, source-model semantic accuracy |
| Case ID, role, ledger and source-result schema | YES | The source's original gate actually ran correctly |
| Pinned source commit/path *claimed in manifest* | Matched to pinned local registry | Re-fetch/remote authentication (not done) |
| Original SpineForge `ACCEPT` | Preserved verbatim | Human identity/authentication, paid writer authorization |
| SpineForge failed story audit | Preserved verbatim | Any subsequent audit was successful |
| KITE-01 source-bound candidates | Preserved verbatim | Final StoryState or semantic certification |
| GREENHOUSE-01 originally rejected | Preserved verbatim | Historical failure can be silently rewritten as PASS |
| Canonical state write or downstream model run | NEVER | Production eligibility |

**Conservative P2 stop classes:**
`HISTORICAL_APPROVAL_UNAUTHENTICATED`,
`HISTORICAL_QUALITY_GATE_FAILED`,
`STATE_CANDIDATES_AWAIT_SEMANTIC_REVIEW`,
`HISTORICAL_EXTRACTOR_GATE_REJECTED`.

Every one of the four historical cases remains `STOPPED_PENDING_UNVERIFIED_GATE`.
The harness never invents a shared story dependency among cases.

## Contracts and exact limitations

- `src/story_harness_p2.py`: stdlib-only immutable dataclasses `StageInput`, `GateReceipt`, `StageResult`, deterministic `generate_receipts()` and `verify_report()`.
- `configs/story_harness_p1_frozen_import.json`: unchanged source envelope; no fake historical provenance or additional author-model outputs.
- Verifier version `p2.local-frozen-integrity-gate.v1`. Only the **local archive integrity/schema test** has an executed PASS.
- `original_spine_or_q25_gates_reexecuted=false` and `original_human_review_authenticated=false` are mandatory.
- `semantic_support_certified=false`, `full_story_state_qualified=false`, `state_commit_authorized=false`, `production_write_performed=false` and `downstream_stage_executions_authorized=0`.
- `provider_calls=0`, `provider_cost_usd="0"`; original provider usage in P1 remains historical data only.
- There is **no asynchronous or automatic model execution** and no real end-to-end same-story run. This is a narrow, auditable step toward a real stage gateway.

## Frozen replayable P2 receipt artifact

The four locally computed integrity receipts and typed stage records are
also stored in [pinned-local-integrity-receipts.json](../../evidence/story_harness_p2/pinned-local-integrity-receipts.json).
The artifact was generated with `generate_receipts` using original P1
archived files; **no model response was synthesized for it**. Every CI
run independently regenerates the result and compares the full JSON.
The receipt is still only proof of local archived-byte/schema verification,
**not** authentication of a historical human or semantic gate.

## Commands and tests

```sh
python -m unittest discover -s tests -p 'test_story_harness*.py' -q
python -m src.story_harness_p2 \
  --manifest configs/story_harness_p1_frozen_import.json \
  --repo-root .
python -m src.story_harness_p2 --repo-root . \\
  --verify-report evidence/story_harness_p2/pinned-local-integrity-receipts.json
```

Negative tests reject tampered historical decisions, altered source file hashes,
manually fabricated `GateReceipt` and `StageResult` fields, promoted authority
bits, cross-story chains, changed original source revisions and paid execution mode.
Deterministic output contains **no wall-clock timestamp**.

## Next step to reach a genuine production-meaningful gate

P2.1 must execute each *real existing stage validator* against the appropriate
frozen case with its exact versioned source/contract, capturing explicit gate
result and dependencies under a strict isolated runtime. The P2 local integrity
receipt does **not** substitute for that validator. The Q25 code/artifacts in
Draft PR #273 must remain unchanged and cannot be silently imported into a
live StoryState path. An independently reviewed semantic gate and genuine same-
story handoff remain prerequisites for meaningful `GATE_ACCEPTED` and any
subsequent model execution.

PR #275 stays Draft; P2 only implements the **typed contract + local receipt
boundary**, not a fully authenticated human/semantic stage gate.
