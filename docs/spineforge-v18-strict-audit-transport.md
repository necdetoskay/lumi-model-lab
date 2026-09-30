# SpineForge v18 — Strict Audit Transport

v18 keeps the validated v16 repaired Spine unchanged and changes only the final audit transport.

Source:
`experiments/results/spineforge-v16/36760550050/result.json`

## Why

v17 used `json_object` transport. Sonnet returned valid JSON but only 10/18 dimensions and moved two dimension objects to the wrong level. Local validation correctly rejected it.

v18 uses provider-level strict JSON Schema with a compact transport-specific contract:
- all 18 dimension names are required object keys;
- no extra dimension keys are allowed;
- decision, defects, targets, preserve and decision_reason are required;
- transport is converted deterministically into the existing `SpineAuditV11` contract.

The strict transport schema must remain below **4096 bytes**, matching the previously qualified Sonnet strict-schema budget.

## Topology

validated v16 repaired Spine
→ one Sonnet provider-strict audit
→ deterministic transport-to-SpineAuditV11 conversion
→ ACCEPT/REPAIR
→ STOP

No Architect. No Repair. No Writer. No automatic retry.

## Initial zero-cost qualification

Run `36765441611` — **SUCCESS**

- v18 strict transport/runtime: **6 PASS**
- v17 audit-only regressions: **4 PASS**
- paid v18 calls: **0**
- v18 spend: **$0**
