# LUMI Story Harness — Frozen 10-Story Cohort V1 / $20 Aggregate Authorization

**2026-10-14 · Draft PR #275 · MODEL LAB ONLY · Canon and production unchanged.**

The user approved an increase of the **aggregate** LUMI Story Harness test ceiling from $10 to **$20**, inclusive of prior spent/unknown/reserved exposure. **Budget authorization is not automatic paid-run authorization.** Existing P4.15/P4.17/P4.37/P4.57/P4.58 historical $10 assertions, recorded receipts, grants and evidence remain immutable. A new cohort executor must be separately implemented and admitted before any paid batch. This V1 policy and CI perform zero provider model calls.

## Fixed cohort: no story-by-story fixes

1. First establish a genuinely operable, end-to-end harness (canonical input → SpineForge → Writer → independent full-story quality → immutable English Master → original Q25 → read-only Final StoryState), pinned model/profile, all prompts, quality gates, repair limits and stage-specific cost policy.
2. **Before B01 starts**, seal one baseline harness commit and SHA-256 digests of all eleven logical components plus a SHA of each of the ten frozen synthetic input cases. Status remains `PREPARED_NOT_FROZEN` until that separate freeze is proven.
3. Run B01–B10, two per age 4/10/12/25/40, with **identical baseline harness**, regardless of how many REJECT. Do not patch prompts, models, code or quality thresholds, selectively retry failures, or edit story prose. An already-frozen stage-local bounded repair remains permissible exactly as implemented.
4. Preserve **all ten attempt outcomes**, including failures, and only then run the cross-cohort root-cause analysis. Distinguish quality failures from provider/CI/unknown-charge stops; no fake ACCEPT or QC self-attestation. An operational or safety STOP can suspend the batch: never break fail-closed protection merely to finish ten. A suspended/incomplete cohort cannot be presented as a finished ten-story quality experiment.
5. Rank common defect families across the cohort by prevalence, severity, root-cause stage, and regression risk (causal, spatial, temporal, response, closure, epistemic, age, spine, narrative, Canon/state, provider). Record multiple findings per story and trace source spans; no single-story patches.
6. Implement the smallest shared corrections as **Harness V1.1**. Freeze V1.1 separately; **re-run the exact same ten input states/topics/ages** from scratch. New real model generations and independent blinded reviews must be recorded; prior story text is not a fresh run.
7. After paired comparison, test ten **unseen** preregistered cases without further tailoring. Keep the published ten-case pilot and independent holdout distinct. A 9/10 sample is not proof of 90% reliability; the original >=27/30 unseen release benchmark still stands.
8. Every actual sample SUCCESS needs genuine producer and independent auditor evidence, reader score >=4/5, same-story English Master, real Q25 and evidence-grounded read-only Final State. An offline green is not a successful story.

## Budget (planning bound, not live reconciled invoice)

- Aggregate user-approved upper ceiling: **$20.00** (not $20 additional).
- Last documented conservative prior reservation after P4.58 approval: **$3.249558**; this may be stale and is NOT a verified OpenRouter invoice or available credit.
- Indicative full new trial maximum: SpineForge + Writer **$0.350**; independent quality **$0.040**; Q25 **$0.050** = **$0.440**. Actual stricter stage limits still apply.
- Fresh baseline 10 plus paired regression 10 maximum reservation: **$8.800**.
- Ten unseen holdout trials: **$4.400**.
- Historical documented reservation plus 30 planned trials: **$16.449558**, illustrative headroom **$3.550442** ONLY if historic ledger remains reconciled and no other spending/unknown charges exist.
- Before the first baseline paid attempt: reconcile **all** provider receipts, unknown-charge holds, previously committed budget, provider credit availability, and full ten-case future reservation. If full batch cannot be reserved, **do not start**. No automatic retries or unapproved fallback.
- Earlier source code and grants still enforce $10. **They are not silently upgraded by this document**; a separate reviewed V1.x executor and grant policy must enforce the $20 aggregate ceiling safely before any billable batch.

## Evidence and contract

- `configs/story_harness_frozen_cohort_v1.json`: prepared freeze protocol and budget bound, not an inference grant.
- `src/story_harness_frozen_cohort_v1.py`: validates unchanged original ten-case matrix, budget envelope, freeze rules and future per-attempt lock; counts claims without certifying them.
- `tests/test_story_harness_frozen_cohort_v1.py`: anti-tamper, forbidden mid-cohort changes, ten-of-ten completion, no fake ACCEPT and no silent over-budget.
- `.github/workflows/story-harness-frozen-cohort-v1-offline.yml`: deterministic offline-only CI.

**Next exit gate:** independently seal a complete real production-path-equivalent Harness V1.0, pin code and input SHA, reconcile real ledger, then authorize ten distinct paid attempts through a separately reviewed runner; no new model calls in this phase.

## Previously consumed grant hygiene

The original B07 P4.58 genuine quality call already returned ACCEPT in CI #38613825422. Its old PR-synchronize workflow was archived as `workflow_dispatch` with `if: ${{ false }}`, since GitHub PR path matching can retrigger old consumed grants when later commits modify unrelated files. The follow-on run #38617164730 failed **at the exact-file grant gate**; all quality/provider POST steps were skipped and this run did not create a second model call. Future cohort workflows must never inherit one-shot grants from historical branches.

## Unified producer/admission adapter (offline integration)

`src/story_harness_cohort_source_v1.py` provides **one source-verification path for B01–B10**, independent of the B07-specific historical admission code. It requires all four producer artifact byte hashes from a separately sealed registry, checks canonical input/Spine/Writer identity, original provider generation IDs and token/cost records, and explicitly refuses to grant initial quality, English Master or Q25 acceptance. The suite checks the same shared SpineForge input/compiler for all ten cases and replays authentic B07 archived model outputs through the generic reader and original independent audit request construction without a provider call. Quality, Master, Q25 and read-only State are **not yet generalized as a complete batch executor**; a full cohort freeze is still blocked.

## Post-cohort cross-story failure clustering (offline diagnostic)

`src/story_harness_cohort_analysis_v1.py` only runs when **all ten distinct attempt records** have been supplied. It separates provider/CI/unknown-charge STOP from genuine story REJECT, requires one traceable PRIMARY blocker per REJECT, preserves secondary findings and clusters recurring (root-cause stage, failure family) pairs with affected-case counts. A cluster of fewer than two cases is reported as a unique finding, **not** an automatic reason for a story-specific patch. It cannot independently authenticate the receipts: it marks all ACCEPT claims as unverified, never estimates a certified success rate, and never authorizes a Harness patch or production change. Future evidence verification must occur BEFORE treating clusters as established causal conclusions.

## Owner's explicit zero-fix rule — absolute, including microscopic defects

When the first genuine B01 baseline attempt begins, there are **zero changes of any kind** to the frozen Harness until all ten B01–B10 attempt outcomes are recorded. This includes tiny typos, JSON schema adjustments, bugs, provider request parameters, prompts, model profile, CI, quality thresholds or run-order changes. Do not retry an individual failed story and do not rerun after a claimed failure. Record it; proceed to the next case under the same frozen commit. After all ten attempt outcomes, identify common root causes and make the first fixes only in a NEW Harness V1.1, then regenerate and independently review the same ten case inputs.

If global budget/inference key exposure, integrity or safety preconditions become unknown, STOP FAIL-CLOSED and leave the cohort visibly incomplete. Never manufacture missing outcomes or hotfix to reach ten. If a run crashes after an attempt intent is recorded, preserve it as interrupted rather than sending another potentially chargeable request.

The new offline-only runner at src/story_harness_frozen_round_v1.py simulates a locked batch, checks actual git HEAD plus 13 pinned input/prompt/gate files before and after every individual attempt, writes O_EXCL one-shot intents and outcomes, and proves that ten rejections and even tiny exceptions do not cause edits or retries. The simulator cannot call a model and is NOT yet an approved paid-batch executor.

## Generalized downstream stage validators (offline)

The new src/story_harness_cohort_stages_v1.py reuses the original source-bound P4.22 audit request/verifier, the generic portion of P4.23 English Master qualification, P4.24 Q25 request/response verifier and a case-independent evidence-only Final State projection. Historic B07 immutable genuine producer bytes are replayed through the full common stage interface, while QUALITY and Q25 responses are explicitly MOCKED in unit tests. None of these offline mocks counts as a genuine independent ACCEPT. The wrappers do not themselves authorize provider calls or attest external provider origin. Sealed, original quality/provider response bytes and a generic paid orchestration grant remain separate exit gates before freezing the first paid cohort.

## Uniform complete-message payload limit before freeze

Historical quality limits (20,000 bytes default; exact original B07 22,000-byte exception) and historical Q25 24,000-byte default are retained. A NEW explicit 40,000-byte serialized request allowance applies uniformly to all ten frozen-cohort cases, provided the caller opts into cohort_explicit=True. This is a single preregistered harness rule, not a mid-test adjustment. The original complete manuscript, Canon and Spine stay in the request; no truncation or omission. All per-stage output/cost constraints remain unchanged. Negative tests ensure legacy callers cannot borrow the extended size without the cohort protocol.

## Unified all-age end-to-end adapter (mock/verification only)

src/story_harness_cohort_pipeline_v1.py now chains the original P4.17 bounded state/topic SpineForge+Writer and the shared genuine-response validators for independent initial quality, byte-identical English Master, real Q25 contract, and noncanonical Final StoryState. The adapter is ONE per-case codepath for B01–B10; it persists claims/intent/provenance/output with exclusive file writes, has maximum four model-call envelopes (two generation, one QA, one Q25), accounts reported costs even if content validation fails, forbids provider routing fallback, and never automatically retries. Mock-only tests exercise **all 10** distinct original inputs, plus REJECT, invalid Writer, duplicated case and ambiguous transport; reports explicitly refuse to certify provider origin or genuine literary ACCEPT. A distinct sealed and externally authorized provider runner is required to actually dispatch model POSTs; this code has no provider CLI or active paid workflow.

## Mandatory full Harness: Memory · Tools · Models · Prompts · State · Quality · Finance · Evidence

Owner explicitly requires all genuine cohort tests to be run INSIDE one version-pinned Story Harness, not through a loose collection of old case-specific scripts. `configs/story_harness_runtime_v1.json` is a strict, dedicated exact runtime profile containing nine typed sections (Memory, Tools, Models, Prompts, Quality, State, Finance, Evidence, Lifecycle); `src/story_harness_runtime_v1.py` validates all settings fail-closed, constructs a per-case immutable Canon/topic/age/obligation memory snapshot, denies shared/cross-story/vector retrieval and new Canon facts, allows only predeclared deterministic and paid-stage tools, and binds all four model stages to the **exact** Anthropic Sonnet 5.5 OpenRouter route (not the unrelated global registry fallback). All model and prompt settings, token and stage cost bounds are fixed. The runtime validates source identity in each exact provider wire, independent auditor source, and immutable runtime/tool/prompt bytes before every stage. The generic full pipeline now requires a correctly case-bound RuntimeHarness parameter and writes a harness receipt; bypass is forbidden even for offline tests. Cross-case memory, dynamic model, foreign tool, prompt/schema changes and paid grants are denied in negative tests. Payment authorization remains FALSE; live provider identity and entire global $20 ledger must still be separately verified BEFORE baseline freeze. No 10-story genuine test has started.


## Mandatory all-ten end-to-end OFFLINE freeze rehearsal and readiness packet

`src/story_harness_readiness_v1.py` inspects ALL TEN ages and cases through the SAME RuntimeHarness (Memory / Tools / Models / Prompts / Quality / State / Finance / Evidence / Lifecycle), per-case Canon SHA, request model route, exact pinned source manifest and unchanged commit; it emits a deterministic readiness packet and explicitly states `BLOCKED_NOT_SEALED` for paid execution. New mock-driven tests chain the actual common stage adapter under the offline frozen 10-attempt controller; one failed quality case or tiny invalid Writer result does not change the Harness or skip any remaining cases.

A safety defect was closed **before** the real 10-case cohort began: an escaped `ProviderCostUnknown` or Harness integrity failure must count as a GLOBAL fail-closed stop, **not** a harmless per-story error. This prevents hidden overbilling. Ordinary stage-local formatting/quality failures still record a case failure, and the remaining cases continue under the exact same frozen SHA. Both these separate behaviors are covered by offline negative tests. `READY_FOR_OFFLINE_REHEARSAL` does **not** grant a real model call; the owner-approved $20 aggregate ceiling never overrides key isolation, real cost ledger, authorization or external provenance requirements.


## Authentic source-content component freeze

The 11 logical Harness components now have explicit versioned source/config file sets, including input, SpineForge, Writer, quality, Master, Q25, final-state, prompts, model profiles and budget/retry policy. Each component SHA-256 hashes canonicalized identity plus the real SHA-256 values of its source bytes. The individual source file hashes and all 11 component hashes are verified before and after each story. A changed component hash fails closed even if the commit identifier is unchanged. Prior simulated name+commit component digests are retired before any genuine ten-story cohort; prior evidence remains untouched. This new seal still authorizes zero paid calls.


## Aggregate $20 cohort preflight and cryptographic intent (offline, no POST)

`src/story_harness_cohort_launch_gate_v1.py` creates a **new** cohort-scoped, externally signable Ed25519 intent (not the historically consumed B07 or v21 single-story grant). The signed payload pins the exact ten B01–B10 input fingerprints, sealed Harness commit and component/file digest, no-mid-cohort-change rule, no model retries, immutable Canon/Tools/Models and the user's $20 aggregate ceiling. The public signing key MUST be independently provisioned out of band; model-generated or fixture keys never impersonate human consent. Prior OpenRouter settled, held and unknown charges must be reconciled under a fresh independently authenticated 15-minute financial evidence snapshot. Previous P4.58 conservative exposure is a lower bound, not treated as a fresh invoice. Baseline pre-reservation is $4.40 and the full baseline+repeat+holdout conditional planning envelope is $13.20, both counted against $20 inclusive of prior exposure. Snapshot arithmetic is **not** external attestation; all offline reports and signed-fixture tests categorically set `paid_dispatch_authorized=false` and zero real provider calls. Key isolation, genuine signed grant, provider route and actual paid run orchestration must still be independently established before baseline freeze.


## Dedicated $4.40 inference key: read-only OpenRouter verification

`src/story_harness_cohort_provider_observe_v1.py` verifies an independent baseline key using a single authenticated `GET /api/v1/key` plus a public model catalog GET; it makes **zero POST** requests. The expected key is a new, unused, no-reset non-management OpenRouter inference key with key limit **exactly $4.40**, 100% remaining credit, BYOK counted, and no other consumers. Historical application/shared `OPENROUTER_API_KEY` is **not** accepted for the baseline key. The dedicated env var is `LUMI_STORY_COHORT_ISOLATED_OPENROUTER_KEY`. It also verifies exactly one qualifying Sonnet 5.5/Anthropic strict-schema model endpoint, compatible output cap and public prices. Only sanitized fields (not raw provider/key JSON, key labels, key hashes, secrets) may be reported. The standalone script defaults to OFFLINE status; real free metadata GETs require an explicit `--live-get-only` and a properly provisioned external secret. Even a successful GET does not prove exclusivity or account-global budget reconciliation; `provider_dispatch_authorized` stays FALSE. Deliberately **no workflow with a PR-accessible secret has been added**.


## Current Anthropic Sonnet 5.5 public route compatibility (2026-10-14)

Live public OpenRouter endpoint catalogue at `https://openrouter.ai/api/v1/models/anthropic/claude-sonnet-5.5/endpoints` advertises one Anthropic route with model ID `anthropic/claude-sonnet-5.5`, strict structured output support, price $2/$10 per million in/out tokens, and maximum output 128000 tokens. Its supported parameters list does **not** advertise `temperature`. The cohort's original P4.17 request omits `temperature`; the old P4.12 initial quality logic requiring temperature belonged to a different historical wire. New cohort-only model observation validates actual required parameters (`max_tokens`, `response_format`, `structured_outputs`) without rewriting or weakening older P4.12 audits. Model availability is current public metadata, not guarantee that a billable request will be admitted; run-time checks remain mandatory.
