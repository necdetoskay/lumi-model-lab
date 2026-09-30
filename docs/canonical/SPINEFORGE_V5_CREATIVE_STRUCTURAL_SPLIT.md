# SpineForge v5 — Creative Intent / Strict Structural Compilation Split

Status: IMPLEMENTATION CANDIDATE — ZERO-COST QUALIFICATION ONLY

Parent Epic: #253  
Implementation issue: #254

## Why v5 exists

v4 exhausted 3/3 paid attempts before Sonnet was reached.

- Attempt 1: `movement_constraints` had the wrong shape.
- Attempt 2: that defect was fixed; required `COMPLICATION` was missing.
- Attempt 3: that defect was fixed; one DECISION beat omitted
  `new_information`.

Across all three attempts the creative core remained coherent and revision
feedback repaired the previous defect. The repeated failure class is therefore
the Aion -> deep strict EpisodeSpine serialization boundary.

## Architectural correction

v5 separates two responsibilities that v4 combined.

`SpineContextPack.v1`
→ Aion **Creative Intent Architect**
→ deterministic outer-envelope/context binding
→ Sonnet **Strict Structural Compiler + Hardener**
→ deterministic EpisodeSpineV3 + authority validation
→ Luna **Product Gate**
→ STOP / human review

Writer is unreachable from SpineForge.

### Aion boundary

Aion owns creative invention.

Its application contract validates:
- outer schema;
- application-owned model identity;
- Creative Signature;
- episode_spine is a JSON object.

The nested episode_spine proposal is intentionally not validated as
EpisodeSpineV3 before Sonnet.

No deterministic layer invents missing semantic content.

### Sonnet boundary

Sonnet owns strict structural compilation.

It receives:
- the identical immutable ContextPack;
- Aion Creative Intent;
- the full EpisodeSpineV3 schema.

The provider request must use JSON Schema structured output with
`strict=true` and `provider.require_parameters=true`.

The application then validates the returned compiled spine again with Pydantic
and ContextPack authority rules. Provider enforcement never replaces
application validation.

### Luna boundary

Luna remains the product gate and sees:
- identical ContextPack;
- Creative Signature;
- compiled/hardened spine;
- deterministic checks and lineage.

Luna does not authorize Writer. ACCEPT means STOP / human review.

## Frozen-qualification rule

No paid v5 call is permitted until:
1. archived v4 Aion payloads replay through Creative Intent;
2. replay changes no nested creative semantics;
3. strict Sonnet request construction is proven offline;
4. compiled-spine fixtures pass deterministic validation;
5. stale-state and human-approval guards regress;
6. v1-v5 regression is green;
7. dependencies are SHA-256 frozen.

After v5 freeze, runtime/prompt/model-profile changes require v6.
