# Story Harness P4.1 — English Master seal evidence contract, genuine acceptance DENIED

**Date:** 2026-10-13. **PR:** #275 Draft. **Issue:** #285.
**Paid model calls:** 0. **New API spend:** $0.
No production state, no main merge, no new sealed English Master and no Q25 extraction.

## Why this stage exists

Previous evidence proved only a trustworthy **STOP** for the island story:

- P3.0: frozen Writer #3 is linked to the original SpineForge island story.
- P3.1: Audit 8 qualification PASS does not equal story acceptance; cycle 9
  last completed story audit = `LOCAL_REPAIR_REQUIRED`. Cycle 10 is repaired
  but still awaiting a completed re-audit.
- P3.2: `ENGLISH_MASTER_NOT_ADMISSIBLE` and no actual sealed island Master.
- P4.0: genuine frozen v21.4 runtime has a **bounded** topology, but
  mocked positive results are not real quality evidence. The historical
  paid attempt `37230896244` remains `REJECT_PROVIDER_FAILURE`.

P4.1 demonstrates the **positive mechanical data path** with that original
frozen v21 runtime while denying any elevation to actual story acceptance.

## Immutable identity and trust

`configs/story_harness_p41_seal_trust_registry.json` is pinned by exact
SHA-256. It binds the original island source commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`, the cycle-10 frozen story
artifact ID/hash, approved Spine hash, approval ID, ContextPack ID/fingerprint,
reader age 12, source runtime revision v21.4, three-call and single-repair
boundaries, and stage budgets.

Four trust roots are **explicitly empty** in the present cohort:

1. Actual, externally verified quality/provider receipts.
2. Independent authenticated reviewer/semantic accept attestations.
3. Registered immutable English Master seal hashes.
4. Registered Q25 source admission hashes.

The checker cannot infer a real seal from a status string, fabricated
signature boolean, unreviewed repair text, failed historical paid run,
or a positive **synthetic** model reply. The current `verify_actual_english_master_seal`
and `build_q25_source_request` functions intentionally fail closed pending
a separately authenticated and versioned trust-root admission process.
They must not be advertised as working real-positive seal issuance.

## Actually executed original bounded runtime

P4.1 reexecutes P4.0's verified historical source preflight and runs the
original `src.spineforge_v21_simulation.simulate_case` and
`execute_paid_quality_once(simulation=True)` in an isolated subprocess
with fake transport and provider sockets blocked. This executes the
**original** frozen v21 quality engine and source validators; it does
not call a model. Both the one-call clean path and the three-call
single-scene-repair path return synthetic `ACCEPT` to test the interface.

The immutable *mechanical preview* validates:

| Contract field | Required check |
| --- | --- |
| `EnglishMasterSealCandidate.v1` | Synthetic-only origin, no seal ID or trusted signature |
| Source | Same-story pinned artifact ID, original and accepted story SHA, Spine/context ID and fingerprint |
| Real v21 result mechanics | Valid original source result schema, accepted text SHA, one or three calls |
| Quality ledger | Stage order, each stage cost, aggregate tokens/cost, no second repair |
| Scene repair | Distinct repaired story SHA, unchanged outside-cluster span material |
| Final audit | Targeted repaired-scene-plus-boundaries, **never** another whole-story audit |
| Review | Expected blocker families, but **no** authenticated reviewer or semantic accept proof |
| Seal | `PREVIEW_NOT_A_SEAL`; English Master authorization **false** |

The original mock runtime includes elapsed-time measurements with tiny
nondeterministic variations. It verifies the original call input/response
hashes **inside the same subprocess**, but source-bound immutable
regression fingerprints use a normalized stage/usage/story projection
that **excludes mock-only elapsed time**. Real paid-source receipts
must retain their original token, cost and latency evidence; this
normalization does not create or rewrite paid historical artifacts.

## Separate read-only Q25 contract

The `Q25SourceRequest.v1` preview can only be made from this strictly
typed synthetic candidate; it records:

- Source commit, Spine/context identity and the candidate's accepted
  story text SHA (as a **preview**, not an admitted source).
- Null English Master seal artifact ID.
- `admission_status=DENIED_NOT_A_REAL_SEAL`.
- `q25_extraction_authorized=false`,
  `paid_provider_dispatch_authorized=false`,
  `canonical_state_commit_authorized=false`.

A tampered or elevated preview is rejected. The real Q25 builder
rejects all inputs because no real registered seal/Q25 trust roots
exist in this frozen cohort.

## Future real-positive English Master eligibility

A new separately versioned evidence cohort is required; P4.1 cannot
turn its test fixtures into this proof. It must have:

1. A real, bounded-quality `ACCEPT` from the latest actual story
   material (including the entire immutable v21 audit, repair if any,
   and targeted final audit response and ledger). The source story,
   approved Spine, reader/age and ContextPack must match exactly.
2. Cryptographically or independently authenticated reviewer evidence
   that explicitly validates causal/physical, spatial/temporal/epistemic
   continuity, response/closure, canon/spine obligations, age and
   narrative quality. Self-declared `reviewer_verified=true` does
   not constitute authentication.
3. A separately reviewed original English story byte snapshot, source
   and accepted text SHA-256, strict immutable quality decision trace,
   token/usage/cost/latency ledger, and an individually registered
   English Master seal artifact ID/hash.
4. A separately approved *read-only* Q25 source admission registry
   entry referring to that real seal and accepted story SHA. Neither
   quality ACCEPT nor seal preview can call Q25 automatically.
5. An explicit user-approved paid execution authorization **before**
   any new provider dispatch. Model slots may be swapped in separate
   versioned profiles; quality stages and limits remain bounded. The
   post-usage cost ceiling does **not** guarantee a provider hard cap.

P4.1 only validates *schema mechanics and fail-closed gating*. It does
**not** implement or claim authenticated real-positive seal issuance.
That needs external trust-root enrollment and dedicated review.

## Deterministic result and reproduction

```text
synthetic_positive_case_count = 2
original_runtime = SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.4
clean_call_count = 1
repaired_call_count = 3
synthetic_contract_shape_valid = true
real_english_master_seal_emitted = false
q25_source_request_produced = false
stop_reason = REAL_ENGLISH_MASTER_EVIDENCE_UNAVAILABLE
state = STOPPED_REAL_SEAL_AND_Q25_NOT_QUALIFIED
provider_calls = 0
provider_cost_usd = "0"
```

```sh
git worktree add --detach /tmp/lumi-p41-pinned 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' 'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P41_ROOT=/tmp/lumi-p41-pinned
python -m unittest discover -s tests -p 'test_story_harness_p41.py' -v
python -m src.story_harness_p41 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P41_ROOT" \
  --verify-report evidence/story_harness_p41/pinned-synthetic-seal-contract-receipt.json
```

The negative tests reject tampered source/spine/context, false provider
or reviewer authentication, fake real seal, forged ACCEPT from the
original historical provider failure, extra calls, altered costs/usage,
full-story final audit, changed repair, fabricated Q25 admitted status,
and altered stored receipts. No provider credentials leave the environment.

