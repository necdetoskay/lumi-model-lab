# SERA v0.30 — Authenticated Read-only Provider Receipt Reconciliation

**Scope: experiment branch only.** SERA story/source-state stage integration
with a documented OpenRouter provider API, under opt-in authenticated
application scope. No real billable generation call, production worker
deployment, manual review, LUMI WorldState/EventGraph commit or frozen
Mara Spine mutation occurred in v0.30.

## What OpenRouter currently supports — and what it DOES NOT

As documented by OpenRouter:
- \`GET /api/v1/generation?id=<GENERATION_ID>\` returns usage/cost,
  model, finish reason and provider generation metadata.
- \`GET /api/v1/generation/content?id=<GENERATION_ID>\` can return
  preserved original prompt messages and completion text. Access or
  content persistence is not guaranteed on every generation.

Official references:
- https://openrouter.ai/docs/api/api-reference/generations/get-generation
- https://openrouter.ai/docs/api/api-reference/generations/list-generation-content

**Neither endpoint is a proven request-SHA-to-generation-ID lookup.**
When a response is lost *before its generation ID is captured*, local
SHA, HTTP timeout, request_id or a guessed session reference is NOT
sufficient to locate its completion reliably. The worker must then
remain \`V030_GENERATION_ID_UNAVAILABLE_NO_RESEND\` — no blind retry,
no fabricated receipt, no human rescue step. Provider caching should
not be mistaken for guaranteed billing idempotency/recovery.

## v0.30 implementation

[openrouter_reconciliation_v030.py](./openrouter_reconciliation_v030.py)
performs exact request-signature and provider-record verification:
- Application-owned \`binding_lookup(model, request_sha256)\` must return
  an ID/sha/model association originating from authenticated provider
  evidence; separate \`verify_binding\` must affirm authenticity.
- Provider GET is authenticated, read-only, single-attempt, with bounded
  response size and allowlisted endpoint/method; neither path sends
  another model-completion POST. No token output ceilings are sent.
- Metadata \`id\`, model and completed finish reason must match, and
  stored original \`input.messages\` must exactly equal the frozen
  system/user messages that were submitted. Any difference is HOLD.
- Successful recovery of the stored completion and nonnegative finite
  provider cost yields a reconstructed source/provider envelope with
  explicit \`read_only_recovery\` provenance. It remains NONCANONICAL;
  original source/event and world validation still have to run.

**Important limit:** stored \`input.messages\` alone does not attest
all provider generation settings. The *separately authenticated*
generation-to-exact-request fingerprint binding is therefore mandatory.
A purely user-supplied model output or generation ID is not accepted as
proof. A provider-generated token that never reached a trusted durable
system cannot be auto-recovered with the documented endpoints.

### Durable stage and crash-resume integration

- [v0.21 paid writer receipt archive](./openrouter_scene_writer_v021.py)
  now permits an authenticated read-only \`reconciler\` only for a
  previously STARTED request missing its receipt. It first checks
  if the full response was already archived. When reconciled, the
  complete normalized provider envelope is journaled atomically and
  never queried/rebilled again. With no ID it stays fail-safe.
- [v0.22 independent evidence worker](./fresh_scene_evidence_worker_v022.py)
  uses the same reader for source sentence batches and typed facets.
- [v0.18 independent semantic stage](./semantic_recovery_v018.py)
  can reconcile its own STARTED paid task and preserve its old
  receipt digest; it cannot approve a claim as world truth.
- Only a *previously started orphaned paid request* can reopen a
  corresponding durable failed-safe evidence/semantic journal.
  Previous failure is retained in
  \`pre_reconciliation_safe_stop.json\` for audit. Ordinary semantic,
  source, schema and other failure reasons remain terminal.
- [v0.20 scene loop](./unattended_scene_rewrite_v020.py)
  can automatically re-evaluate a prior
  \`V022_EVIDENCE_GENERATION_FAILED_SAFE\` ONLY after the same exact
  archived evidence has become READY through a trusted reader.
- [composed runner](./composed_scene_runner_v023.py) and the
  [StoryForge v0.28 bridge](./storyforge_bridge_v028.py)
  opt-in explicitly via a versioned \`reconciliation_policy_id\`
  bound to the immutable job contract. Dry-run remains zero-provider
  calls, a billable live run still requires the app's signed paid
  grant, and all successful scene results remain NONCANONICAL.

## Self-hosted adversarial evidence

- [Known-generation resolver tests](./tests/test_openrouter_reconciliation_v030.py):
  exact model/prompts/source cost, forged binding, missing GEN ID,
  wrong registered model, unavailable stored content, invalid cost,
  one crashed writer rehydrated using two GET-style mocked provider
  reads and *zero additional completion POSTs*, then durable replay.
- [Automatic controller restart tests](./tests/test_reconciled_scene_resume_v030.py):
  fully unknown request HOLD, a previously charged source extraction
  rehydrated and qualified after an unattended restart, and no
  unsafe continuation when the id remains unavailable.
- [v0.28 job contract test](./tests/test_storyforge_bridge_v028.py):
  changed reconciliation policy must not reuse the previous source,
  world, model or billing contract.

**These tests use synthetic transport and mocked provider records.**
No real GET to user-owned OpenRouter history and no paid POST is claimed.

## Remaining release blockers

1. Actual authenticated app-level source of
   \`generation_id ↔ original request sha ↔ model\` evidence, populated
   before process failure; otherwise the unknown-ID branch rightly
   cannot recover. A provider-side idempotency mechanism may be
   necessary for truly opaque lost replies.
2. Recovering a **partially returned writer response** in the v0.20
   in-flight *rewrite* branch, not merely independent extraction and
   already receipted writer results. Do not bypass the v0.20 rewrite
   STARTED checkpoint without an authenticated GET-only recovery path.
3. Production LUMI Story worker with durable per-job storage, signed
   profile/world/character/route/fact snapshots, controlled spend,
   real live integration, machine-only transactional canonical
   WorldState/EventGraph writes and safe rollback.
4. Final full-story and frozen Mara S1 real-model qualification;
   semantic truth cannot be inferred merely from source or model
   agreement.

No configured output token ceilings. No required operator step. A
safe terminal HOLD is legitimate if the provider cannot prove a
replayable generation. Epic #306 is the canonical backlog.

[Track SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
