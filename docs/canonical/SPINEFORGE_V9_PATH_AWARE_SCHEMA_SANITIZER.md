# SpineForge v9 — Path-Aware Strict Schema Sanitizer

Status: ZERO-COST QUALIFICATION

## Why v9 exists

v8 paid Attempt 1 proved that partitioned provider-strict Sonnet transport reaches inference and that durable evidence survives GitHub artifact-quota failure. It also exposed a generic transport defect: the sanitizer recursively removed every mapping key named `title`, including the legitimate application field `properties.title`, while leaving `title` in the schema's `required` array.

That made the provider schema internally inconsistent. Sonnet therefore could not be required to emit the field that local Pydantic validation still required.

v9 does not change the Creative Blueprint, structural contracts, prompts, ContextPack, model selection, stage ownership, Luna gate, or human-review boundary.

## v9 change

Provider-schema sanitization becomes path-aware:

- JSON Schema annotations such as `title`, `description`, `default`, pattern/range/list constraints, enum/const can be removed where they are schema keywords.
- Keys inside schema name maps such as `properties`, `$defs`, `definitions`, `patternProperties`, and `dependentSchemas` are preserved as application/schema member names.
- Before any strict provider call, every object schema must satisfy `required ⊆ properties`; otherwise execution stops before inference.
- Sonnet schema-size budget remains enforced.
- No parse retry is introduced.
- Writer remains unreachable before explicit human approval.

## Qualification rule

No paid v9 call is allowed until:
1. v9 sanitizer tests are GREEN;
2. inherited v8 evidence behavior remains GREEN;
3. historical frozen regressions remain GREEN;
4. v9 runtime is SHA-256 frozen and freeze verification is GREEN.

## Frozen zero-cost qualification

Runtime ID: `spineforge.contextpack.v9`  
Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v9`  
Runtime source commit: `a15feb24ce310b753690fdc068e874c0bb49625b`  
Frozen dependencies: **29 SHA-256 locked files**

Final frozen verification run: `36736910932`

Result:
- v9 sanitizer/runtime/stage/frozen tests: **19 PASS**
- v8 durable-evidence regression: **4 PASS**
- historical v1→v8 regression: **91 PASS**
- historical snapshots deselected by design: **3**
- frozen files modified after runtime source commit: **0/29**
- paid v9 calls: **0**
- v9 spend: **$0**

The exact v8 defect is covered by frozen tests:
- `StructuralFrameV1.title` exists in both provider `required` and `properties`.
- path-aware sanitization preserves legitimate property names that collide with JSON Schema annotation keywords.
- malformed `required`/ `properties` relationships stop before provider inference.

Current state: `READY_FOR_ATTEMPT_1`.

No `experiments/triggers/spineforge-v9.json` exists.

Next paid scope:

`SPINEFORGE_V9_ATTEMPT_1_AION_THEN_PARTITIONED_STRICT_SONNET_THEN_STRICT_LUNA_IF_ELIGIBLE`

A separate explicit authorization is required before trigger creation.

## Paid Attempt 1 — terminal v9 result

Run: `36738179384`

Runtime result: `structural_assembly_contract_rejected`.

Execution reached farther than prior revisions:
- Aion Creative Blueprint: completed
- Sonnet Structural Frame: completed
- Sonnet Structural Beats: completed
- Sonnet Structural Resolution: completed
- deterministic final assembly: rejected
- Luna Product Gate: not called
- Writer: not called

Exact accounting:
- API calls: **4**
- total tokens: **90,770**
- cost: **$0.2296431**
- summed model latency: **244.623 s**

Root cause is a generic contract-parity defect:
`ReversalEvidenceDraftV1.certainty` in `StructuralResolutionV1` is typed as arbitrary `str`, while final `ReversalEvidenceV2.certainty` only accepts `OBSERVED | INFERRED | HYPOTHESIS`.

The section contract therefore accepted a value the final assembly contract deterministically rejects.

v9 Attempt 2 is forbidden. A successor must make section contracts at least as strict as the corresponding final assembly fields and add zero-cost parity regression.

Terminal status:

`QUALIFICATION_FAILED_SECTION_TO_FINAL_CONTRACT_PARITY_GAP`

