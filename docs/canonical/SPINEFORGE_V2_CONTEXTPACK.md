# LUMI SpineForge v2 — ContextPack-first

Status: FROZEN QUALIFICATION CANDIDATE

Runtime revision:

SPINEFORGE-CONTEXTPACK-FROZEN-v2

## Why v2 exists

SpineForge v1 proved the role split:

Aion Creative Architect -> Sonnet Structural Hardener -> Luna Product Gate -> Human approval.

v2 adds the production authority boundary required by LUMI.

No model receives ad-hoc state fragments.

All three models receive one identical immutable application-owned object:

SpineContextPack.v1

## Source architecture

Qualification:

MockCanonicalState.v1
-> deterministic SpineContextPack builder
-> SpineContextPack.v1
-> SpineForge

Production target:

LUMI Canonical State
-> deterministic SpineContextPack builder
-> SpineContextPack.v1
-> the same SpineForge runtime

The model-facing contract stays stable when mock state is replaced by production state.

## Context contents

The pack includes reveal-safe:
- revision lineage and fingerprints;
- reader profile/session;
- character identity/current role;
- Origin facts/formative events;
- current situation/pressures/desires;
- relationships;
- inventory/resources and capabilities;
- memories with fact-usage policy;
- world rules and known facts;
- location access/rumor/locked state;
- public Saga state and eligible milestones;
- active opportunities;
- recent episode anti-repetition data;
- approved premise;
- creative permission envelope;
- hard freezes and authority rules.

Hidden truth answers are not present.

## Same reality for every model

Aion, Sonnet and Luna receive the same:
- context_pack_id;
- context_fingerprint;
- complete SpineContextPack payload.

Aion cannot be judged using secret context it never saw.
Sonnet cannot harden using hidden truth unavailable to Aion.
Luna cannot penalize a plan for information outside the application-owned pack.

## Attempt boundary

Before every paid attempt:

1. Generic stage verifies frozen runtime hashes.
2. Canonical source is read fresh.
3. SpineContextPack is deterministically materialized.
4. Pack id and fingerprint are compared to the case authority.
5. Context-bound revision feedback is verified if this is attempt 2 or 3.
6. Only then may paid inference begin.

If canonical state changed:
STOP before inference.

The old revision feedback/product/human approval is stale.

## Paid topology

One authorized attempt means at most:

1. Aion Creative Architect
2. if strict-valid: Sonnet Structural Hardener
3. if Sonnet does not REPLAN and patch is valid: Luna Product Gate
4. STOP

No automatic paid retry.
No Story Writer call.

## Revision

REPLAN is data, not code.

Sonnet/Luna/human revision feedback is bound to:
- context_pack_id;
- context_fingerprint.

A changed ContextPack cannot consume old revision feedback.

Maximum 3 attempts.

## Human approval

Even Luna ACCEPT creates only:

AWAITING_HUMAN_REVIEW

Human approval is also fingerprint-bound.

If the current ContextPack fingerprint changes before approval or StoryForge handoff, the approval is rejected as stale.

## Frozen runtime rule

Once the first paid case begins:
- canonical/mock state may change only as explicit case data;
- revision feedback may be added as data;
- evidence and cost ledger may be added as data.

Runtime code, prompts, workflow and model profile configuration are frozen.

Any hash change invalidates the active case for this revision.

A scenario-specific code/prompt/workflow patch is a qualification failure, not a recovery.

## First qualification case

spineforge.v2.age18.forbidden-cartographer.fantasy.01

Context:
- exact age: 18
- narrative family: HIGH_FANTASY_MYSTERY
- source: mock canonical state
- ContextPack schema: spine-context-pack.v1

Initial spend:
0 calls / 0 tokens / $0

No paid trigger exists until explicit authorization.
