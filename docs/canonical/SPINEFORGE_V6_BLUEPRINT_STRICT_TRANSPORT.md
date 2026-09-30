# SpineForge v6 — Creative Blueprint + Strict Structural Transport

Status: FROZEN QUALIFICATION CANDIDATE — READY FOR EXPLICIT ATTEMPT 1 AUTHORIZATION

## Why v6 exists

v4 proved that Aion's creative core can improve while deep strict EpisodeSpine serialization repeatedly fails before Sonnet.

v5 corrected ownership by moving strict EpisodeSpine compilation to Sonnet and passed its zero-cost qualification. Before any v5 paid call, a transport audit found a remaining generic weakness: Sonnet and Luna still used the shared `json_object` transport. Their endpoints advertise structured output support, so leaving the strict contract unenforced at provider level would knowingly preserve an avoidable serialization risk.

v5 is not patched after freeze. It is retained as zero-cost frozen evidence and superseded before any paid inference.

## v6 topology

`SpineContextPack.v1`
→ Aion 3.5 Mini — Creative Blueprint (`json_object`, locally validated)
→ Sonnet 5.5 — Structural Compiler (**provider strict JSON Schema** + local Pydantic)
→ strict `EpisodeSpineV3` authority validation
→ GPT-5.6 Luna — Product Gate (**provider strict JSON Schema** + local Pydantic)
→ STOP / human review

Writer remains unreachable inside SpineForge.

## Contract ownership

Aion owns creative identity, dramatic engine, roleplay, creative beat intentions, decision/climax/payoff ideas.

Sonnet owns rigid EpisodeSpine phase completeness, required beat fields, logistics, reversal evidence, branch structure, persistence shape, and writer executability.

Luna owns independent product gating.

The application owns ContextPack authority, model lineage, stale-state protection, provider request contract, local validation, attempt limits, cost/latency lineage, and human approval.

## Strict transport rule

Aion remains on its verified `json_object` path because Aion 3.5 Mini does not advertise provider strict JSON-schema enforcement.

For Sonnet and Luna:
- the exact application `output_contract` becomes `response_format.type=json_schema`;
- `strict=true`;
- `provider.require_parameters=true`;
- no parse retry is allowed;
- the response is still parsed and validated locally with Pydantic;
- ContextPack authority validation still runs after provider enforcement.

Provider enforcement complements application validation; it does not replace it.

## Recovery

If the structural stage fails/replans, the fingerprint-bound Creative Blueprint is preserved and the next separately authorized attempt may resume at Sonnet without paying Aion again.

If the problem is creative, feedback targets Aion.

Any ContextPack fingerprint change invalidates feedback/product/human approval before inference or Writer handoff.

## Zero-cost evidence

Run `36701961819`:
- v6 strict-transport + inherited blueprint behavior: **18 PASS**
- v1→v5 historical freeze/regression: **79 PASS, 1 historical snapshot deselected**
- paid calls: **0**
- cost: **$0**

No paid v6 trigger is authorized by this document.


## Frozen qualification authority

Runtime ID: `spineforge.contextpack.v6`  
Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v6`  
Freeze commit: `f2e20689834663207dc106ac030c9a48d64f71f7`  
Runtime source commit: `e4686d0af774c95f5bf0756152eafe53988ac963`  
Frozen dependencies: **28 SHA-256 locked files**

Final freeze verification run:

`36702505341`

Result:
- v6 strict-transport/frozen tests: **23/23 PASS**
- v1→v5 historical freeze/regression: **79 PASS**
- historical zero-spend snapshot: **1 deselected by design**
- paid calls: **0**
- v6 spend: **$0**

Current qualification case:

`spineforge.v6.age18.forbidden-cartographer.fantasy.01`

Current state:

`READY_FOR_ATTEMPT_1`

There is no `experiments/triggers/spineforge-v6.json`.

Next paid boundary:

`SPINEFORGE_V6_ATTEMPT_1_AION_BLUEPRINT_THEN_STRICT_SONNET_THEN_STRICT_LUNA_IF_ELIGIBLE`

A separate explicit authorization is required before the trigger can be created.

Writer remains blocked.


## Paid Attempt 1 result — qualification failed

Run: `36702946557`  
Trigger commit: `6b73cce653a7c47a88765748686fff50e3bd7df9`

Result: `QUALIFICATION_FAILED_STRICT_PROVIDER_GRAMMAR_TOO_LARGE`.

Observed sequence:

1. Frozen v6 runtime verification passed and Attempt 1 entered the model pipeline.
2. Aion Creative Architect completed its inference.
3. The first Sonnet strict structural-compiler request was rejected with HTTP 400 before structural inference.
4. Azure, Anthropic, and Google Sonnet routes all returned the same provider error: the compiled strict grammar was too large.
5. Luna Product Gate was never called.
6. No automatic retry or Attempt 2 was started.
7. Writer remained blocked.

The failure is a generic provider-transport/schema-complexity defect, not a case-specific story defect. Therefore v6 remains frozen and is not patched.

### Accounting defect exposed by Attempt 1

Aion completed before the Sonnet provider rejection, but v6 only persisted final evidence after downstream stage completion. The unhandled Sonnet transport exception therefore prevented Aion usage/cost from being durably written. Exact Aion tokens/cost for this attempt are recorded as unknown rather than guessed.

Any successor revision must checkpoint usage/cost/latency immediately after every completed model call and preserve partial evidence when a later provider call fails.

### Evidence archive defect exposed by Attempt 1

The Actions job created local evidence files, but the evidence-branch push was rejected by GitHub workflow-scope handling. A successor revision must archive evidence without requiring a new branch push that carries workflow files.

### v6 closure

The consumed v6 trigger is disarmed with `paid_authorized=false`. No further v6 paid attempt is authorized.

A successor revision must solve all three generic defects before any new paid call:

- provider-safe strict structural transport;
- durable per-stage accounting/checkpointing;
- reliable evidence archival independent of workflow-branch push permissions.
