# LSF Context Builder V0.1 — Qualification Result — 2026-09-26

Status: **SMOKE QUALIFIED / LAB-ONLY**

Profile: `LSF-A4-W500-context-builder-v0.1`

## Goal

Build the smallest safe Story Context Packet from Canon + CharacterStoryState + StoryIntent without sending the full world/state snapshot to the planner.

## Final architecture

```
Full Canon + State
      ↓
Deterministic extraction / isolation
      ↓
ALWAYS_REQUIRED
+ StoryIntent direct references
+ hard guards
      ↓
JEV soft-enrichment scoring
      ↓
Deterministic risk policy
      ↓
Minimal Story Context Packet
```

Authority split:

- ALWAYS_REQUIRED: deterministic
- StoryIntent direct fact references: deterministic
- hard guards / knowledge boundaries: deterministic
- cross-world / private / internal metadata exclusions: deterministic before JEV
- soft enrichment: `typesafe/jev-1.13`
- new relationship/entity expansion: never auto-added by soft JEV unless that relationship entity is already directly referenced
- REVIEW facts: evidence only; not sent to planner by default

## Evidence

Raw hybrid JEV run:
- run `36264952721`
- 3 intents
- each intent evaluated twice
- raw JEV enrichment set stable across repeats

Deterministic post-policy proof:
- run `36265297130`
- model calls: 0
- result: **3/3 PASS**
- packets differentiated by StoryIntent
- no forbidden leak
- no required direct fact missing
- final auto-enrichment sets stable across repeats

### Intent 1 — problem solving / truck

Deterministic core includes:
- Deniz identity / exact age
- active world / current location / state revision
- toy truck
- low platform
- truck intact state
- normal-physics guard

JEV auto-enrichment after policy:
- sturdy cardboard
- small wooden block

Nearby Ada relationship was proposed by JEV but deterministically demoted to REVIEW because the StoryIntent did not reference Ada.

### Intent 2 — friendship / chalk

Deterministic core includes:
- Deniz identity / exact age
- active world / current location / state revision
- Ada relationship
- red chalk box
- normal-physics guard

JEV auto-enrichment:
- blue chalk
- yellow chalk
- recent Ada relationship context

The Ada relationship is already directly referenced, so same-relationship enrichment is allowed.

### Intent 3 — garden-gate mystery

Deterministic core includes:
- Deniz identity / exact age
- active world / current location / state revision
- GARDEN_GATE knowledge boundary
- gate-not-crossed state
- normal-physics guard

JEV auto-enrichment after policy:
- active explorer saga thread

Nearby Ada relationship was proposed but deterministically demoted to REVIEW.

## Decision

JEV is **not** the authority for what the planner must know.

JEV is qualified in this smoke only as a **soft-enrichment adviser inside a deterministic Context Builder**.

The safe rule is:

```
FinalContext =
ALWAYS_REQUIRED
+ DIRECT_REFERENCES
+ HARD_GUARDS
+ POLICY_ALLOWED(JEV_SOFT_ENRICHMENT)
- FORBIDDEN
```

This preserves deterministic canon/state isolation while still allowing intent-specific semantic enrichment.

## Next step

Use one frozen qualified Story Context Packet as input to a Spine Planner smoke.

The Spine Planner must produce:
- premise/logline,
- ordered 8-beat spine,
- explicit assumptions,
- canon/state facts used,
- expected StoryOutcome proposal.

The planner does not receive a prewritten solution or spine.

Its output must pass a separate deterministic + semantic Spine Validator before the existing Aion Mini writer pipeline is allowed to run.
