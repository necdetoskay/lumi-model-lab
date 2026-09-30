# SpineForge v3 — Generic Contract Recovery

## Why v3 exists

SpineForge v2 qualification run `36663676934` stopped after the Aion Creative Architect call with `creative_contract_rejected`.

The creative payload itself contained a coherent 10-beat story spine, but v2 exposed four generic contract/runtime design problems:

1. model-authored `creative_model` was compared against application runtime identity;
2. `logistics_plan.location_sequence` duplicated ordered beat geography and could drift;
3. free-text anti-repetition metadata was incorrectly parsed as structural location cardinality;
4. reversal evidence was forbidden from citing the REVERSAL beat where the evidence can legitimately first appear.

v2 remains a real failed qualification revision. It is not reclassified.

## v3 corrections

### Application-owned lineage
Provider/model identity is stamped by the runtime. Model text is not trusted as lineage authority.

### Deterministic projection
`logistics_plan.location_sequence` is derived from ordered beat `location_ref` values. It is redundant data and does not justify a paid retry.

### Contract semantics
`anti_repetition_signature.main_location_pattern` remains descriptive metadata. Structural location truth comes from beats.

Reversal evidence may reference beats established before or at the REVERSAL beat, but never future beats.

### Generic contract recovery
If a creative draft still fails deterministic contract or authority validation after safe normalization:

- downstream Sonnet/Luna calls do not run;
- the paid attempt stops;
- a `spineforge-revision-feedback.v3` candidate is generated;
- the candidate is bound to the exact `context_pack_id` and `context_fingerprint`;
- validation errors become data-driven revision requirements;
- the next Aion attempt requires separate explicit paid authorization;
- stale feedback stops before inference.

No scenario-specific runtime patch is allowed once v3 is frozen.

## Zero-cost replay proof

The exact Aion raw payload from v2 run `36663676934` was replayed locally through v3 with no model calls.

Result: PASS through creative contract + authority validation.

Deterministic adjustments:
- application-owned Aion model identity stamped;
- redundant logistics location sequence derived from beat order;
- existing syntax normalizer retained only safe reversal support cleanup.

Resulting route: `ashen_gate → greyfen → vellum_hall`.

The original creative structure was not rewritten.

## Paid boundary

v3 qualification starts at zero new spend.

One authorized attempt is at most:
- 1× Aion Creative Architect
- if valid: 1× Sonnet Structural Hardener
- if eligible: 1× Luna Product Gate
- STOP for human approval

No automatic paid retry.
No Writer call.

## Freeze evidence

Runtime ID: `spineforge.contextpack.v3`

Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v3`

Runtime source commit: `19e34642e45bccd81fce7633805af83586425797`

Frozen dependency hashes: 26/26 verified.

Historical v2 freeze: 26/26 verified.

Focused combined regression: 33/33 PASS.

Qualification case:
`spineforge.v3.age18.forbidden-cartographer.fantasy.01`

Context fingerprint:
`05a84e09aed48fb7e5f2d177647d7bf1aa50d293e561cfc9c54726ff3e8564b2`

Current v3 spend:
0 API calls / 0 tokens / $0.

No `experiments/triggers/spineforge-v3.json` exists at freeze time.
