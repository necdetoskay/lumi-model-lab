# SpineForge v8 — Durable Evidence Hardening

Status: ZERO-COST IMPLEMENTATION CANDIDATE

## Purpose

v8 does not change the v7 generation topology, models, prompts, contracts, ContextPack authority, strict transport, or retry semantics.

v7 Attempt 1 reached Sonnet Structural Frame and returned `structural_frame_contract_rejected`, but the exact result/revision feedback/usage checkpoint was lost when GitHub Actions artifact storage quota rejected the upload.

v8 exists only to remove artifact quota as a single point of evidence loss.

## Inherited generation topology

`SpineContextPack.v1`
→ Aion Creative Blueprint
→ Sonnet strict Structural Frame
→ Sonnet strict Structural Beats
→ Sonnet strict Structural Resolution
→ deterministic EpisodeSpine assembly
→ local Pydantic + ContextPack validation
→ Luna strict Product Gate
→ STOP / human review.

The implementation is inherited directly from `src/spineforge_v7.py`.

## Evidence channels

1. Runtime result.json remains checkpointed after every completed model call.
2. A compact sanitized summary prints exact failure, usage totals, stage coverage and retry target to immutable Actions logs. Preserved creative payloads are represented only by SHA-256 in logs.
3. Full run evidence will be persisted into a repository result path by the paid workflow.
4. Actions artifact upload is best-effort only and cannot turn a completed qualification into an evidence-loss failure.

No paid v8 inference is authorized before zero-cost tests and a new freeze are GREEN.

## Frozen zero-cost qualification

Runtime ID: `spineforge.contextpack.v8`  
Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v8`  
Runtime source commit: `98987cac80e963f22cbf590f092a7cbc6e2a01ca`  
Frozen dependencies: **29 SHA-256 locked files**

Zero-cost evidence:
- evidence-hardening tests: **4/4 PASS**
- inherited v7 generation topology: **16/16 PASS**
- historical v1→v7 regression: **89 PASS, 2 historical snapshots deselected**
- paid v8 calls: **0**
- v8 spend: **$0**

Current state: `READY_FOR_ATTEMPT_1`.

There is no v8 paid trigger.

Next paid scope:

`SPINEFORGE_V8_ATTEMPT_1_AION_THEN_PARTITIONED_STRICT_SONNET_THEN_STRICT_LUNA_IF_ELIGIBLE`

A separate explicit authorization is required before trigger creation.

## Paid Attempt 1 — terminal v8 result

Run: `36734797000`  
Trigger commit: `24c48aa884fc18e7332bdf33226c1e2c6edd7e22`

Runtime status: `structural_frame_contract_rejected`.

Exact failure: `StructuralFrameV1.title: Field required`.

Root cause is generic and deterministic. The provider transport schema kept `title` in the root `required` list but omitted `properties.title`. The sanitizer recursively dropped every key named `title`, so it removed both JSON Schema annotation keys and the legitimate application property named `title`.

Execution:
- Aion Creative Blueprint: completed
- Sonnet strict Structural Frame: completed provider inference
- local StructuralFrameV1 validation: rejected
- Structural Beats / Resolution / Luna / Writer: not called

Exact accounting:
- API calls: **2**
- input tokens: **25,601**
- output tokens: **12,469**
- reasoning tokens: **8,116**
- cached tokens: **7,845**
- total tokens: **38,070**
- cost: **$0.0730685**
- summed model latency: **182.353 s**
- Aion: **$0.0158265**, 18,141 tokens, 164.921 s
- Sonnet Frame: **$0.057242**, 19,929 tokens, 17.432 s

Evidence hardening succeeded despite artifact quota failure:
- compact Actions-log evidence persisted
- full evidence persisted under `experiments/results/spineforge-v8/36734797000`
- fingerprint-bound Creative Blueprint and revision feedback were recovered
- artifact upload failed, but primary evidence was not lost

The consumed trigger is disarmed. **v8 Attempt 2 is forbidden** because the frozen provider transport is generically defective.

A successor revision must use path-aware schema sanitization and prove, before any provider call, that every item in each object schema's `required` list exists in that object's `properties` mapping.

Terminal status:

`QUALIFICATION_FAILED_PROVIDER_SCHEMA_SANITIZER_PROPERTY_COLLISION`

