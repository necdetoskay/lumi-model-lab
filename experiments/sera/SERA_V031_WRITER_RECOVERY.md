# SERA v0.31 — Crash-safe Replan Writer and OpenRouter ID Limitation

**Status: EXPERIMENTAL / NONCANONICAL.** No production worker,
world-store writes, paid OpenRouter calls, canonical commit, or
operator-intervention step. All experiments run on
\`experiment/sera-scene-state-v0-1-20261015\`.

## Provider capability verified — do not invent idempotency

Official OpenRouter API references:
- Chat completions (POST, model-generated response):
  https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- Generation metadata by known ID (GET):
  https://openrouter.ai/docs/api/api-reference/generations/get-generation
- Original stored input and completion by known ID (GET):
  https://openrouter.ai/docs/api/api-reference/generations/list-generation-content
- Responses (POST, separate interface):
  https://openrouter.ai/docs/api/api-reference/responses/create-responses

For the chat-completions path SERA actually uses, the reviewed public
API contract does **not establish a general provider-guaranteed
idempotency header for replaying a potentially charged request**, nor
a "find my generation ID by original request SHA" query. A mechanism
found for *other products* or endpoints cannot be assumed to work on
chat completions. The Responses API being a different interface does
not automatically solve the problem for an already billed chat call.

**Hard recovery boundary:** To resume a lost response using v0.30's
read-only provider GETs, SERA must already have a separately
authenticated and request/model-bound generation ID. If the generation
ID itself never reached a trusted durable record, the response cannot
be proven recoverable using only these documented endpoints.
The job therefore stays in \`FAILED_SAFE_FINAL\`, without duplicate
generation POST or a required human retry. A provider-side idempotent
contract or independently authenticated generation-ID capture remains
mandatory for guaranteed fully unattended recovery.

## What v0.31 actually implements

1. [v0.21 writer](./openrouter_scene_writer_v021.py) now exposes
   \`writer.recover_existing(source=..., defects=...)\` as a separately
   callable **recovery-only** capability. It reuses the original
   immutable writer-model/source/defect/context request. Its durable
   provider envelope can come only from an existing response receipt
   or a previously STARTED request resolved by a trusted v0.30
   read-only known-generation reconciler. If the request was never
   STARTED, \`V031_NO_PRIOR_BILLABLE_ATTEMPT\` prevents a new POST.
   Model fallback is also forbidden unless a fallback attempt was
   already started or receipted. No model output ceiling is set.
2. [v0.20 controller](./unattended_scene_rewrite_v020.py) can reopen
   \`V020_REWRITE_PROVIDER_FAILED_SAFE\` or
   \`V020_UNKNOWN_IN_FLIGHT_REWRITE_NO_AUTO_RESEND\` only if a
   separately wired \`recover_rewrite_scene\` succeeds. It validates
   each prior \`check_XX.json\` against the original source chain
   and WorldState, revalidates \`rewrite_XX.started\` against its
   exact source and defect hash, restores only the already billed
   result, and writes \`rewrite_XX.json\` before reopening the
   terminal scene decision.
3. The previously failed decision is preserved immutably as
   \`pre_reconciled_writer_safe_stop.json\`. On restart SERA replays
   all source/typed, semantic, causal and full-scene gates for the
   newly generated prose. Provider opinion and editorial readiness
   are not accepted as canonical world truth.
4. [Composed runner](./composed_scene_runner_v023.py) wires this
   no-POST recovery-only callback *only* when the application
   explicitly supplies a versioned \`reconciler\` and
   \`reconciliation_policy_id\`; v0.28 StoryForge already freezes
   that policy in the immutable story/job contract and still demands
   signed billing scope to start model work.

## Regression evidence

[tests/test_writer_reconciliation_v031.py](./tests/test_writer_reconciliation_v031.py)
covers: one simulated charged writer lost reply; fully unattended
restart using a trusted known-generation reader, one original POST
and zero repeated writer POSTs; recovering a provider answer already
archived but lost between writer/scene receipt checkpoints; new
recovery with no prior billable STARTED marker blocked; unknown
generation ID stays on the original fail-safe result; and unchanged
WorldState/noncanonical authorization. The broader SERA regression
suite also guards unknown-ID recovery, profile/source tamper,
all-event causality, and no output-token caps.

All recovery provider replies here are **synthetic fixtures**. Passing
tests do not mean the real OpenRouter account has an externally
authenticated generation-ID lookup installed or that real provider
content storage was tested.

## Not yet qualified for production

- A *real* provider-supported guarantee for lost generation IDs and
  charged requests, or a proven authenticated external observability
  feed that captures those IDs before failure. Do not pretend a local
  idempotency token is proof of upstream deduplication.
- Automatic integrated provider billing reconciliation and aggregate
  multi-stage spend budgets across crashes and parallel workers;
  authenticated app-issued grants still govern charge authorization.
- Production LUMI story worker/model resolver integration and durable
  job volumes; authoritative world/fact/route/character registries,
  profile isolation, full-story unseen real-model proof.
- Machine-authenticated transactional EventGraph/WorldState commit
  with CAS, rollback and concurrent publisher fencing; frozen Mara S1
  remains HOLD until the full real-story and world gates qualify.
- No manual scene patch, operator approval or required restart and no
  app-defined model output token ceiling may be introduced to bypass
  unresolved provider guarantees.

Canonical backlog: [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
