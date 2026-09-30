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
