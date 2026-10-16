# SERA v0.17 — Unattended Scene Identity Recovery (Experimental)

**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Owner contract:** No production manual review, approval, JSON patching, retry click, per-story rules table, or operator rescue commands. No application-defined model output token ceilings.

## Implemented in the laboratory

`scene_recovery_v017.execute` automatically drives the existing v0.16 identity stage and records a source/World/mention-census fingerprint, policy, every attempt's provider receipt, stage result, observed spend, checkpoint trail and terminal disposition in a dedicated output directory.

- First attempt: complete 16-ref (or arbitrary supported ref count) source-bound identity extraction and per-ref targeted self-repair through v0.16.
- If fully receipted but incomplete, automatically perform a new **whole-source** identity extraction with explicit unresolved-ref diagnostics and **all** original references required. Prior model opinions are not facts; every new answer goes through v0.16's original full source/enum/parent checks.
- Automatic deterministic completion: `IDENTITY_CANDIDATES_READY_NONCANONICAL` only when every requested identity ref has a source-bound, nonabstaining model proposal. **This is not an event, entity, WorldState or final story approval.**
- Automatically terminal failure: `FAILED_SAFE_FINAL`, with a specific reason and zero canonical writes. Repeatedly unresolved, invalid, ungrounded or expensive results are **not** handed to a reviewer.
- If an attempt was dispatched but the provider response is absent from durable receipts, **do not duplicate an unknown possibly billed call**. Stop safely. A future idempotent provider request-key/poll/reconciliation adapter is required for fully automatic recovery across this network uncertainty; it is **not** implemented or implied here.
- Re-entering a completed directory verifies original input + policy fingerprints, returns the existing result without any provider call, and can reconstruct a missing final result from completed stored attempts. An interrupted stage with durable, complete paid primary **and targeted** response receipts is automatically reconstructed locally by replaying the strict binder with those same saved model replies; **zero new provider calls**. If the provider request lacks a verified durable reply, the attempt is not resent blindly.
- The additional provider-call limit and observed spend guard are operational, **not token/output-length limits**. The outgoing payload undergoes the existing `enforce_no_output_token_limit` policy check.
- No production DB access, no object/alias creation, no LUMI service changes, no original Sonnet Spine changes, and no paid calls from these unit tests.

## Scope / release boundary

This stage **does not yet**:
1. Cover every sentence, action, causal edge, object and physical/epistemic mutation of the prose.
2. Guarantee correct semantic identity merely because model proposals are source-bound.
3. Qualify all 25 Mara events or issue an authenticated application/world authorization.
4. Execute persistent story-worker replan/rewrite/validate/commit/rollback end to end.
5. Reconcile unknown in-flight provider charges with an idempotent external provider.

These remain blocking integration tasks. **Mara S1 canon remains HOLD.** A successful lab identity-stage attempt must never be shown as a fully approved, self-healed story.

## Offline verification

`python -m unittest experiments.sera.tests.test_scene_recovery_v017 -v`

Tests inject providers with no billable network calls. They exercise healthy completion, automatic source re-extraction after a quarantined row, terminal failure after exhausted retries, no manual gate, unknown charge fail-closed, re-entry without extra provider calls, source fingerprint mismatch, spend guard and no output token ceilings. The existing repository workflow also runs all SERA Python tests and Chromium E2E.

**Next:** Wire the *full* self-healing control loop to the actual durable story worker under project-specific source and model resolver contracts; add provider idempotent reconciliation, event/state semantic coverage and machine-verifiable canon authority, then qualify on unseen end-to-end stories. Do not integrate production by merging this branch alone.
