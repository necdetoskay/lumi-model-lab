# SpineForge v7 — Partitioned Strict Structural Compiler

Status: FROZEN QUALIFICATION CANDIDATE — READY FOR EXPLICIT ATTEMPT 1 AUTHORIZATION

## Why v7 exists

v6 proved that moving strict EpisodeSpine ownership from Aion to Sonnet was directionally correct, but its single monolithic Sonnet JSON Schema was rejected by every attempted Sonnet provider route before structural inference because the compiled grammar was too large.

v7 does not patch frozen v6. It keeps the Creative Blueprint boundary and partitions structural compilation into provider-safe strict sections.

## Topology

`SpineContextPack.v1`
→ Aion 3.5 Mini — Creative Blueprint
→ Sonnet 5.5 — strict Structural Frame
→ Sonnet 5.5 — strict Structural Beats
→ Sonnet 5.5 — strict Structural Resolution
→ deterministic application assembly into full `EpisodeSpineV3`
→ full Pydantic + authority/cross-field validation
→ GPT-5.6 Luna — strict Product Gate
→ STOP / human review.

Writer is unreachable inside SpineForge.

## Strict transport boundary

Each Sonnet section uses `response_format.type=json_schema`, `strict=true`, and `provider.require_parameters=true`.

The provider schema intentionally enforces structural shape: required fields, object/array/scalar structure, references, and `additionalProperties`. Semantic constraints such as literal/enum, regex and numeric/list bounds are applied by full local Pydantic validation on the exact same response. This keeps provider grammar small without weakening the application contract.

Zero-cost measured transport schema sizes:
- Structural Frame: 1431 bytes
- Structural Beats: 856 bytes
- Structural Resolution: 2891 bytes
- hard Sonnet budget: 4096 bytes
- v6 monolithic structural schema: 8675 bytes

## Application-owned deterministic fields

The model does not need to echo facts the application already owns. Final assembly stamps or derives ContextPack-bound premise key, exact age, session, target word range, Sonnet model identity, Saga intended milestone keys, `outcome_uncommitted=true`, `commit_only_if_earned=true`, and logistics location sequence.

## Crash-safe accounting

Every successful model call is checkpointed immediately with stage/model/provider, input/output/total/reasoning/cache tokens, cost, and latency. A later provider failure must persist earlier completed call usage rather than losing it.

## Evidence archive

Paid workflow evidence is uploaded as a GitHub Actions artifact. v7 does not create/push an evidence branch, avoiding the workflow-scope failure exposed by v6.

## Paid boundary

No paid v7 trigger exists. Paid Attempt 1 is forbidden until zero-cost qualification, historical regressions, runtime freeze and freeze verification are all GREEN.


## Frozen zero-cost qualification evidence

Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v7`  
Runtime source commit: `870b83224fd732e66a01266c73bf5f492ed4bd1c`  
Frozen dependencies: **28 SHA-256 locked files**

Final freeze verification run: `36706662527`

Result:
- v7 partitioned-strict + frozen-profile tests: **22/22 PASS**
- v1→v6 historical freeze/regression: **84 PASS**
- historical snapshot exclusion: **1 deselected by design**
- paid v7 calls: **0**
- v7 spend: **$0**
- paid trigger: **absent**
- writer: **blocked**

Qualification case:
`spineforge.v7.age18.forbidden-cartographer.fantasy.01`

State:
`READY_FOR_ATTEMPT_1`

Next paid boundary:
`SPINEFORGE_V7_ATTEMPT_1_AION_THEN_PARTITIONED_STRICT_SONNET_THEN_STRICT_LUNA_IF_ELIGIBLE`

A separate explicit authorization is required before creating `experiments/triggers/spineforge-v7.json`.
