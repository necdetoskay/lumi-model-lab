# SpineForge v4 — Normalizer Integrity

Status: FROZEN QUALIFICATION CANDIDATE

Runtime revision:

SPINEFORGE-CONTEXTPACK-FROZEN-v4

Implementation source commit:

d95da673b91f8e3caa83f6ab773e99fa184e3b68

## Why v4 exists

SpineForge v3 correctly changed the contract so reversal evidence may first appear on the REVERSAL beat. Its frozen runtime, however, still depended on the v2 safe normalizer. That normalizer treated reversal-beat references as removable self references when another earlier reference existed.

Offline replay of the exact archived Aion payload showed the mismatch:

Raw support:
- [reversal_private_mark]
- [reversal_private_mark, escalation_map_discrepancy]

Frozen v3 normalized support:
- [reversal_private_mark]
- [escalation_map_discrepancy]

The second claim concerns the private mark's weathering and placement, so deleting reversal_private_mark weakens evidence lineage to a beat that did not establish that fact.

The v3 paid boundary had already been crossed by run 36666428511. That run was cancelled during the runtime step, so v3 is not patched or reclassified. A new runtime revision is required.

## What v4 changes

Only the generic normalization/runtime boundary changes.

v4 preserves:
- SpineContextPack.v1;
- Aion Creative Architect;
- Sonnet Structural Hardener;
- Luna Product Gate;
- spineforge-revision-feedback.v3;
- spineforge-product.v3;
- all ContextPack stale-state protections;
- explicit authorization per paid attempt;
- human STOP before Writer.

v4 safe normalization:
- keeps evidence references established before the reversal;
- keeps evidence references established on the reversal beat itself;
- treats only future-beat references as invalid;
- may remove future references only when at least one valid at-or-before-reversal support reference remains;
- does not invent replacement evidence.

Application-owned model identity and beat-derived logistics projection from v3 remain unchanged.

## Zero-cost proof

The exact Aion raw payload from v2 run 36663676934 is replayed through v4 without inference.

Expected result:
- creative contract PASS;
- ContextPack authority PASS;
- full reversal evidence support preserved;
- deterministic normalization limited to application-owned model identity and logistics projection.

## Historical qualification state

v2:
- real paid Attempt 1;
- run 36663676934;
- creative_contract_rejected;
- 1 Aion call;
- 22,146 tokens;
- $0.0240562;
- Sonnet/Luna/Writer not called.

v3:
- trigger commit 155a5ab5d2786b0d80299a3825881c17dee3e16c;
- run 36666428511;
- workflow cancelled during runtime;
- ContextPack evidence archived;
- no result.json or stage envelope;
- zero completed model calls/tokens/cost recorded by repository evidence;
- provider-side billing for an interrupted in-flight request is not verified.

Neither prior revision is reclassified as v4 success.

## First v4 qualification case

spineforge.v4.age18.forbidden-cartographer.fantasy.01

ContextPack id:

mock.character.leyra:mock.world.veiled-marches.primary:forbidden_passage_reappears:5

Context fingerprint:

05a84e09aed48fb7e5f2d177647d7bf1aa50d293e561cfc9c54726ff3e8564b2

v4 spend before paid qualification:

0 calls / 0 tokens / $0

No v4 paid trigger exists at freeze time.

## Frozen-runtime rule

26 runtime dependencies are SHA-256 locked.

After the first paid v4 attempt starts:
- no runtime/prompt/workflow/model-profile patch;
- context-bound feedback remains data;
- case data may change only through explicit state/revision inputs;
- any frozen hash change invalidates v4;
- scenario-specific recovery code is a qualification failure;
- a ContextPack fingerprint change invalidates old feedback/product/human approval.

Paid topology remains:

Aion -> if valid Sonnet -> if eligible Luna -> STOP / human review

Writer is not callable from SpineForge.

Next paid boundary:

SPINEFORGE_V4_ATTEMPT_1_AION_THEN_SONNET_THEN_LUNA_IF_ELIGIBLE

## Qualification result — v4 Attempt 1

Trigger commit: `870ec0e2fd62cdd870a08add64cfed8687c16036`  
Run: `36679347817`

Result: **creative_contract_rejected**

The frozen ContextPack authority remained unchanged and the runtime stopped before Sonnet/Luna/Writer.

Calls:
- Aion 3.5 Mini: 1
- Sonnet 5.5: 0
- GPT-5.6 Luna: 0
- Writer: 0

Usage:
- input tokens: 10,064
- output tokens: 13,775
- reasoning tokens: 11,342
- total tokens: 23,839
- cost: $0.0263298
- model latency: 197.997 s
- pipeline latency: 198.049 s

The v4 generic safe normalizer correctly applied only:
- application-owned model identity stamping;
- deterministic logistics location projection.

The remaining rejection is a schema-shape defect in Aion output:

`episode_spine.logistics_plan.movement_constraints`

The frozen contract requires a list; Aion emitted a single string.

No runtime, contract, prompt, workflow, model profile or ContextPack builder patch is applied.

The runtime-generated `spineforge-revision-feedback.v3` candidate is recorded as:

`data/specifications/story_lab/spineforge_v4_attempt1_revision_feedback.json`

It is bound to the unchanged ContextPack id/fingerprint and targets Attempt 2.

**Attempt 2 is not authorized automatically.** A separate explicit paid authorization is required.

## Qualification result — v4 Attempt 2

Trigger commit: `44319dccad182f8d9dd5196fb2d3f87841291df9`  
Run: `36693522927`

Result: **creative_contract_rejected**

The Attempt 1 revision feedback produced a real correction:
- `episode_spine.logistics_plan.movement_constraints` is now a list;
- no parse failure occurred;
- the generic safe normalizer changed no semantic field.

The next deterministic rejection is:

`Episode Spine missing required phases: COMPLICATION`

Calls:
- Aion 3.5 Mini: 1
- Sonnet 5.5: 0
- GPT-5.6 Luna: 0
- Writer: 0

Usage:
- input tokens: 13,237
- output tokens: 7,958
- reasoning tokens: 4,841
- total tokens: 21,195
- cost: $0.0204071
- model latency: 142.789 s
- pipeline latency: 142.843 s

No runtime, contract, prompt, workflow, model profile or ContextPack builder patch is applied.

The runtime-generated `spineforge-revision-feedback.v3` candidate is recorded as:

`data/specifications/story_lab/spineforge_v4_attempt2_revision_feedback.json`

It is bound to the unchanged ContextPack id/fingerprint and targets Attempt 3.

**Attempt 3 is not authorized automatically.**

## Attempt 3 zero-cost preflight

Verification branch:

`verification/spineforge-v4-attempt3-preflight-20260930`

Workflow commit:

`f81cfee5c18ff2297523311ff8f1424ce2018b32`

Run:

`36694111835`

Result: **GREEN**

Verified without paid inference:
- 26/26 frozen runtime dependencies;
- unchanged ContextPack id/fingerprint;
- Attempt 2 feedback schema and context binding;
- `source_attempt=2`;
- `next_attempt=3`;
- `max_attempts=3`;
- focused active-runtime regression PASS.

Paid calls in this preflight: **0**.

Next boundary remains separately authorized:

`SPINEFORGE_V4_ATTEMPT_3_AION_THEN_SONNET_THEN_LUNA_IF_ELIGIBLE`

Attempt 3 is the final allowed attempt in v4. Writer remains blocked.

## Qualification result — v4 Attempt 3 / terminal

Trigger commit: `eb259ea24435160407db33639db02f0e3e7a4b82`  
Run: `36696423052`

Result: **creative_contract_rejected**

Attempt 2 feedback successfully corrected the previous missing-phase defect:
- required `COMPLICATION` phase is present;
- no JSON parse failure occurred;
- safe normalization changed no semantic field.

The terminal deterministic rejection is:

`episode_spine.beats.6.new_information` — required field missing on `decision_window`.

Calls:
- Aion 3.5 Mini: 1
- Sonnet 5.5: 0
- GPT-5.6 Luna: 0
- Writer: 0

Attempt 3 usage:
- input tokens: 13,433
- output tokens: 19,473
- reasoning tokens: 16,519
- cached tokens: 7,571
- total tokens: 32,906
- cost: $0.03272838
- model latency: 282.414 s
- pipeline latency: 282.467 s

v4 cumulative paid qualification:
- API calls: 3
- input tokens: 36,734
- output tokens: 41,206
- reasoning tokens: 32,702
- total tokens: 77,940
- cost: $0.07946528
- cumulative pipeline latency: 623.359 s

### Terminal verdict

**SPINEFORGE-CONTEXTPACK-FROZEN-v4 qualification FAILED after 3/3 authorized attempts.**

No Sonnet, Luna or Writer call was reached in v4 qualification.

The runtime produced a feedback candidate with `next_attempt=4`, but the frozen case has `max_attempts=3`. That candidate is evidence only and is **not eligible for execution**.

There is no Attempt 4 boundary.

v4 remains immutable historical evidence. Any generic recovery requires a new SpineForge runtime revision.

## Qualification result — v4 Attempt 3 / FINAL

Trigger commit: `eb259ea24435160407db33639db02f0e3e7a4b82`  
Run: `36696423052`

Result: **creative_contract_rejected**

Attempt 2 feedback produced a real correction:
- the required `COMPLICATION` phase is now present.

New deterministic rejection:
- beat `decision_window` omitted required field `new_information`.

Calls:
- Aion 3.5 Mini: 1
- Sonnet 5.5: 0
- GPT-5.6 Luna: 0
- Writer: 0

Attempt 3 usage:
- input tokens: 13,433
- output tokens: 19,473
- reasoning tokens: 16,519
- cached tokens: 7,571
- total tokens: 32,906
- cost: $0.03272838
- model latency: 282.414 s
- pipeline latency: 282.467 s

v4 cumulative:
- API calls: 3
- total tokens: 77,940
- confirmed cost: $0.07946528
- cumulative pipeline latency: 623.359 s

### v4 qualification verdict

**FAIL — MAX ATTEMPTS EXHAUSTED**

Across the three attempts, context-bound feedback corrected the immediately preceding defect, but raw Aion output remained unreliable against the full strict Episode Spine contract:
1. Attempt 1: scalar/list shape defect.
2. Attempt 2: required `COMPLICATION` phase omitted.
3. Attempt 3: required beat field `new_information` omitted.

No Attempt 4 is permitted. No Sonnet/Luna/Writer call occurred in v4 qualification.

v4 remains frozen and is not patched or reclassified. Next work must use a new SpineForge runtime revision.

