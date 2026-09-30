# LUMI SpineContextPack v1

Status: PRE-FREEZE ARCHITECTURE

## Purpose

SpineForge must not consume ad-hoc prompts, database dumps, or different authority views per model.

The single model-facing canonical authority is:

SpineContextPack.v1

The same immutable pack is provided to:
- Aion Creative Architect;
- Sonnet Structural Hardener;
- Luna Spine Product Gate.

## Production boundary

Production source:

LUMI canonical state

Account/User -> Universe  
Profile -> World/Timeline  
Character -> CharacterStoryState  
Origin / Foundation  
Saga  
World Canon  
Knowledge State  
Relationships  
Inventory / Resources  
Memories  
Opportunities  
Recent Story History  
Reader Profile  
Approved Premise

Application-owned deterministic builder:

LUMI canonical state -> SpineContextPack.v1

SpineForge never reads the production database directly.

## Qualification boundary

Until production integration exists, Model Lab uses:

MockCanonicalState.v1 -> deterministic builder -> SpineContextPack.v1

The mock source is test data only.

The output contract is intended to remain the same when the source changes from mock to production.

## Pack contents

### Lineage

Every pack contains:
- Universe revision;
- World revision;
- Timeline revision;
- Profile revision;
- Character revision;
- CharacterStoryState revision;
- Saga revision;
- Premise revision;
- Reader Profile revision;
- context_pack_id;
- context_fingerprint.

### Character authority

- identity / age / archetype;
- traits and interests;
- Origin facts;
- formative events;
- current role;
- immediate desires / avoidances;
- current pressures.

### Stateful authority

- relationship state;
- inventory/resources and their authorized capabilities;
- memories and whether they may establish external facts;
- active opportunities;
- recent durable outcomes / recent story shapes when available.

### World authority

- world type;
- era / habitat;
- technology and magic rules;
- known world facts;
- social context and current pressures;
- accessible locations;
- rumored locations;
- locked/limited locations.

### Saga authority

Only reveal-safe Saga state enters the pack:
- public goal/stakes/mystery/themes;
- eligible milestones;
- intended milestone keys;
- completed milestones;
- active side sagas;
- public long-term questions.

Hidden truth statements/answers are deliberately excluded.

### Premise authority

The approved premise enters unchanged:
- objective;
- inciting event;
- central problem;
- wonder/discovery;
- stakes;
- constraints;
- meaningful choice pressure;
- forward mystery;
- local payoff ceiling;
- possible persistent outcomes.

### Creative permission envelope

The pack carries the application-owned rules for what new entities or transient details may be invented.

## Fingerprint

The context_fingerprint is SHA-256 of canonical JSON for the entire pack except the fingerprint field itself.

Same canonical state => same fingerprint.

Any material state/context change => different fingerprint.

## Stale-state protection

Every SpineForge attempt records:
- context_pack_id;
- context_fingerprint.

Revision feedback is bound to that same pair.

Human approval is also bound to that pair.

If the current canonical state materializes a different fingerprint:
- old revision feedback is rejected before inference;
- old human approval is rejected;
- the stale Spine Product cannot silently continue to Writer.

## Model parity

Aion, Sonnet and Luna receive the exact same SpineContextPack.

No model receives a broader hidden authority graph than another.

This prevents:
- Aion writing from one reality;
- Sonnet hardening against another;
- Luna judging with secret information unavailable to the architect.

## Qualification rule

The first paid ContextPack-first SpineForge case will begin only after:
- v2 runtime is complete;
- v2 prompts are complete;
- mock canonical state is complete;
- ContextPack builder is complete;
- generic revision loop is context-bound;
- human approval is context-bound;
- runtime/prompt/workflow files are SHA-256 frozen.

After that point, active cases are data-only.

Any runtime or prompt modification invalidates the active qualification revision.
