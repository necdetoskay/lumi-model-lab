# LSF Context Builder Hybrid Proof — 2026-09-26

Status: **QUALIFICATION PASS (bounded fixture)**
Profile: `LSF-A4-W500-context-builder-v0.1`
JEV: `typesafe/jev-1.13`
Evidence run: `36265275665`

## Purpose

Build a minimal Story Context Packet from Canon + CharacterStoryState + StoryIntent without sending the full state to a planner.

## Qualified responsibility split

### Deterministic core

Always included by code:
- active character identity
- exact age
- active world
- current location
- CharacterStoryState revision

Direct StoryIntent references are resolved deterministically:
- referenced inventory/object/entity facts
- referenced location facts
- referenced relationship facts
- explicit state facts

Hard guards are also deterministic:
- world/physics policy
- knowledge boundary
- cross-world isolation
- privacy/internal metadata filtering

### JEV scope

JEV does **not** decide hard invariants.

JEV only scores remaining soft candidates for enrichment.

Current bounded policy:
- probability >= 0.45 → SELECT
- probability 0.30–0.45 → REVIEW
- probability < 0.30 → OMIT
- REVIEW is evidence only; not automatically sent to the planner
- forbidden facts are removed before JEV
- unrelated relationship expansion is demoted to REVIEW unless that relationship entity is directly referenced by StoryIntent

## Evidence

Three StoryIntents were evaluated twice each against the same frozen Canon+State fixture.

### Problem-solving / truck

Deterministic core includes:
- Deniz identity / age / world / current location / state revision
- toy truck
- low platform
- truck intact
- normal-physics guard

JEV auto enrichment:
- sturdy cardboard
- small wooden block

Unrelated Ada relationship was initially scored by JEV but deterministic relationship policy demoted it to REVIEW.

Result: PASS / repeat-selected enrichment stable.

### Friendship / chalk

Deterministic core includes:
- Deniz identity / age / world / current location / state revision
- Ada relationship
- red chalk box
- normal-physics guard

JEV auto enrichment:
- blue chalk
- yellow chalk
- recent Ada relationship context

Result: PASS / repeat-selected enrichment stable.

### Garden-gate mystery

Deterministic core includes:
- Deniz identity / age / world / current location / state revision
- GARDEN_GATE knowledge boundary
- gate-not-crossed state
- normal-physics guard

JEV auto enrichment:
- active explorer saga thread

Unrelated Ada relationship was demoted to REVIEW.

Result: PASS / repeat-selected enrichment stable.

## Overall

- intents: 3
- passes: 3
- failures: 0
- differentiated packets: yes
- forbidden leak: 0
- missing deterministic direct reference: 0
- required soft enrichment miss: 0
- selected enrichment set stable across duplicate calls: yes
- JEV probability drift observed: small (max ~0.03 in final proof)
- elapsed time for 6 JEV decisions batches: ~2.32 s

## Important interpretation

This does **not** prove JEV is deterministic in the mathematical sense.

Earlier multi-class experiments showed instability between semantically close labels such as OPTIONAL/IRRELEVANT and GENERATIVE/GUARD.

The qualified architecture therefore does not delegate final context authority to JEV.

Final packet authority is:

```
FinalContext =
  ALWAYS_REQUIRED
  + DIRECT_STORYINTENT_REFERENCES
  + HARD_GUARDS
  + POLICY_ACCEPTED(JEV_SOFT_ENRICHMENT)
  - FORBIDDEN
```

JEV is a fast semantic relevance signal inside deterministic policy.

## Next step

Use one qualified Story Context Packet as the only contextual input to a Spine Planner.

The planner must produce:
- premise/logline
- 8 ordered beats with density labels
- explicit canon/state references used
- assumptions
- expected StoryOutcome/state delta proposal

The planner must not receive a prewritten spine or solution from the test harness.

A separate validator must reject:
- canon/state contradictions
- knowledge leaks
- unavailable object use
- cross-world leakage
- impossible causal solutions
- premature state mutation

Only a validated spine may enter the already-qualified Aion Mini writer → semantic QA → Gemini translation → Luna fidelity pipeline.
