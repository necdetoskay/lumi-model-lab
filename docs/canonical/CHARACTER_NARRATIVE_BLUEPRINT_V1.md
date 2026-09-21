# Character Narrative Blueprint v1 — Canonical Generation Contract

Status: **PROPOSED / LAB-ONLY**  
Contract id: `character_narrative_blueprint_generation@1`  
Schema id: `character-narrative-blueprint.v1`  
Producer under test: premium/strong narrative model

## 1. Purpose

The model produces a **long-horizon narrative possibility space**, not a future story sequence.

The output represents:

```text
Origin
+ Present Situation
+ Narrative Core
+ Saga Blueprint
+ Proposed World Integration
+ Reweave Policy
```

It does not represent committed future events.

## 2. Top-level contract

Only these top-level fields are allowed:

```json
{
  "schema": "character-narrative-blueprint.v1",
  "origin": {},
  "present_situation": {},
  "narrative_core": {},
  "saga_blueprint": {},
  "world_integration": {},
  "reweave_policy": {},
  "safety_and_constraints": {}
}
```

## 3. Origin

`origin` contains committed-past proposals and unresolved historical questions.

Required conceptual fields:

- `summary`;
- `origin_facts[]`;
- `formative_events[]`;
- `origin_relationships[]`;
- `unresolved_origin_questions[]`.

Each origin fact must declare:

- stable key;
- fact text;
- importance;
- mutability: `IMMUTABLE | REINTERPRETABLE`;
- whether the character knows it;
- whether it is publicly/world known.

An unresolved question is not automatically a predefined secret answer. The model must explicitly distinguish:

```text
question exists
≠
answer already canonically fixed
```

## 4. Present Situation

`present_situation` describes the character at story-start time.

It may contain:

- current role;
- location context;
- current relationships;
- current resources;
- current pressures;
- open questions;
- immediate desires;
- immediate avoidances.

This layer answers: **What is the character's life like now?**

It must not duplicate Origin or predict future outcomes.

## 5. Narrative Core

`narrative_core` captures durable narrative forces:

- identity anchors;
- core drives;
- fears;
- internal tensions;
- long-term questions;
- themes.

A drive or tension may shape opportunities but must never be encoded as a mandatory future choice.

## 6. Saga Blueprint

`saga_blueprint.design_intent` must enforce:

```json
{
  "horizon": "LONG",
  "breadth": "EXPANSIVE",
  "linear_story_plan": false,
  "mandatory_story_order": false,
  "user_may_ignore_saga": true
}
```

### 6.1 Threads

A thread is a long-lived narrative possibility.

Each thread needs:

- stable key;
- title;
- premise;
- importance: `MAJOR | SUPPORTING | LATENT`;
- themes;
- links to Origin/Narrative Core;
- why it matters to the character;
- activation conditions;
- seeds;
- milestones;
- optional branches;
- possible payoffs;
- dormancy policy;
- recovery policy.

### 6.2 Seeds

A seed is a reusable breadcrumb, not a story.

Allowed seed kinds:

`RUMOR | NPC | LOCATION | ITEM | DOCUMENT | SYMBOL | MEMORY | EVENT | DREAM | RELATIONSHIP | WORLD_PHENOMENON`

Allowed narrative functions:

`FORESHADOW | QUESTION | DISCOVERY | CONNECTION | WARNING | TEMPTATION | REVELATION_PRECURSOR`

Every seed must include:

- stable key;
- short summary;
- kind;
- narrative function;
- world-binding hint;
- visibility policy;
- eligibility conditions;
- possible unlocks;
- `must_not_force_followup: true`.

### 6.3 Visibility and reveal ceiling

Every seed must declare one initial visibility:

`HIDDEN | FORESHADOW_ONLY | DISCOVERABLE`

It must also define:

- allowed usage;
- forbidden usage;
- reveal ceiling.

Example:

```json
{
  "initial_visibility": "FORESHADOW_ONLY",
  "allowed_usage": [
    "The symbol may appear on an old expedition object."
  ],
  "forbidden_usage": [
    "Do not reveal who created the symbol.",
    "Do not reveal its connection to the missing parent."
  ],
  "reveal_ceiling": "Only the symbol's existence and unusual age may be established."
}
```

The downstream story model must never receive hidden future information beyond the runtime-allowed projection.

### 6.4 Milestones

A milestone is a **possible** meaningful development.

Allowed milestone types:

`DISCOVERY | REVELATION | DECISION | RELATIONSHIP_SHIFT | CONSEQUENCE | CONVERGENCE | TRANSFORMATION`

Every milestone must declare:

- stable key;
- summary;
- required = false by default;
- preconditions;
- possible entry points;
- possible consequences;
- unlocks;
- terminal flag.

A milestone is not canon until an actual story/outcome causes it.

### 6.5 Branches

Branches describe multiple valid future directions.

Every branch must preserve:

`all_paths_valid: true`

No branch may imply that one user choice is the canonical/default future.

### 6.6 Possible payoffs

Payoffs are possibilities, never promises.

Required semantics:

```json
{
  "certainty": "POSSIBLE",
  "required": false
}
```

## 7. World integration

`world_integration.proposed_bindings[]` connects Saga seeds to world concepts such as NPCs, locations, items, rumors, documents, events, factions or phenomena.

Every proposal must encode:

```json
{
  "preferred_existing_entity": true,
  "reuse_first": true,
  "creation_allowed_if_missing": true
}
```

The premium model proposes semantic bindings. It does not allocate production IDs or directly create canonical entities.

## 8. Reweave policy

Reweave may revise only unrevealed future possibility space.

Immutable after commit/reveal:

- committed Origin facts;
- already revealed Saga facts;
- committed story outcomes.

Potentially mutable:

- future seeds;
- unrevealed milestones;
- unrevealed payoffs;
- inactive bindings.

Potential reweave triggers include:

- major character change;
- major world change;
- invalidated thread;
- long dormancy;
- major relationship change;
- cross-world transition.

## 9. Runtime state is separate

The generation contract does **not** emit authoritative Saga runtime state.

A separate runtime representation owns states such as:

`HIDDEN | DORMANT | ELIGIBLE | FORESHADOWED | DISCOVERED | ACTIVE | ADVANCED | RESOLVED | ABANDONED | INVALIDATED`

The premium model may propose blueprint semantics; deterministic runtime logic owns transitions.

## 10. Story-model projection

The normal story model must not receive the complete blueprint.

It may receive only a bounded projection such as:

```json
{
  "eligible_saga_context": [
    {
      "thread_key": "saga_thread_01",
      "seed_key": "seed_04",
      "allowed_usage": [
        "NPC may recognize the symbol."
      ],
      "forbidden_usage": [
        "Do not reveal the missing-parent connection."
      ],
      "reveal_ceiling": "Recognition only; no explanation of origin."
    }
  ]
}
```

This prevents future-canon leakage.

## 11. Forbidden outputs

The producer must not encode:

- Story 1/2/3/... sequences;
- "the character will definitely...";
- a guaranteed future romance, death, travel decision or discovery;
- future events as committed facts;
- mandatory Saga progression;
- exact production database IDs;
- canonical state mutations;
- a requirement that every story advances Saga.

## 12. Validation

Before an experiment run accepts a blueprint, it must pass:

```text
JSON parse
→ schema validation
→ cross-reference validation
→ semantic validation
→ future-choice precommit detection
→ dependency validation
→ reveal-policy validation
→ duplicate/near-duplicate inspection
→ world-binding validation
```

Fail closed on:

- unknown references;
- impossible dependencies;
- mandatory future choices;
- future events encoded as facts;
- contradictory Origin facts;
- invalid reveal ordering;
- duplicate logical seeds that materially reduce breadth.

## 13. Generation guidance, not hard DB limits

Initial lab guidance:

- Origin facts: 5–15
- Formative events: 2–8
- Core drives: 2–5
- Internal tensions: 1–4
- Saga threads: 4–8
- Seeds/thread: 3–10
- Milestones/thread: 2–8
- Possible payoffs/thread: 1–4

Quality outranks count.

## 14. Canonical principle

> Saga does not write the future. It leaves traces in the world so that future stories can become meaningful.
