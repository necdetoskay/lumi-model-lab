# LUMI SpineForge v1

Status: FROZEN QUALIFICATION CANDIDATE  
Runtime revision: SPINEFORGE-FROZEN-v1

## Product boundary

SpineForge does not produce story prose.

Input:

Character / Origin / Saga / World / State / approved Premise / Reader Profile

Output:

SPINE PRODUCT

A Spine Product must be strong enough that StoryForge Writer's job is to dramatize an already-good story rather than invent its core plot.

## Production topology

### 1. Aion 3.5 Mini — Creative Architect

Aion owns creativity:
- dramatic engine;
- protagonist desire and pressure;
- memorable scene promises;
- roleplay opportunities;
- world-specific story mechanics;
- beats;
- branch options;
- reversal idea;
- climax identity;
- local payoff;
- forward intrigue.

Aion returns:
- Creative Signature;
- strict EpisodeSpineV2.

If the creative contract or authority alignment is invalid:
STOP. Sonnet and Luna are not called.

### 2. Deterministic safe normalization / strict contract

Only semantics-preserving syntactic recovery already frozen into the runtime may run.
No scenario-specific recovery code may be added.

### 3. Sonnet 5.5 — Structural Hardener

Sonnet is not a second creative author.

It may return:
- KEEP;
- PATCH;
- STRUCTURAL_PATCH;
- REPLAN.

PATCH operations are exact deterministic path replacements and are restricted to structural/execution fields.

Sonnet may not change:
- title;
- premise;
- story promise;
- protagonist identity/role;
- immediate objective;
- central question;
- stakes;
- opening hook;
- forward hook;
- beat identity, phase, location or purpose;
- branch identity or option.

If those need redesign, Sonnet must return REPLAN.

### 4. Deterministic patch application

Every patch must:
- point to an allowed path;
- include exact expected_old;
- have creative impact NONE or LOW;
- leave the result valid under EpisodeSpineV2;
- preserve premise/state/Saga authority.

Invalid patch => STOP. Luna is not called.

### 5. GPT-5.6 Luna — Spine Product Gate

Luna independently evaluates 17 dimensions:

Creative:
- STORY_DESIRE
- ROLEPLAY_POTENTIAL
- SCENE_POTENTIAL
- CHARACTER_DRIVENNESS
- WORLD_SPECIFICITY
- WONDER_OR_INTRIGUE
- FRESHNESS

Structural:
- AGE_MATURITY
- CAUSAL_COHERENCE
- ESCALATION
- REVERSAL_QUALITY
- AGENCY
- BRANCH_EXECUTABILITY
- CLIMAX_PAYOFF
- LOCAL_SATISFACTION
- SAGA_ALIGNMENT
- WRITER_EXECUTABILITY

ACCEPT requires every protected threshold.

### 6. Human review

Even Luna ACCEPT does not authorize Writer.

Status becomes:

AWAITING_HUMAN_REVIEW

The complete Spine Product is shown to the human.
Only explicit human approval creates the Writer-compatible approved artifact.

## Revision loop

REPLAN does not permit runtime modification.

Sonnet or Luna findings are converted into:

spineforge-revision-feedback.v1

That data contains:
- previous creative signature;
- previous spine;
- must_preserve;
- must_change;
- creative feedback;
- structural feedback;
- authority freezes.

The next authorized attempt goes back to Aion.

Maximum:
3 SpineForge attempts.

Attempt 4 is rejected before inference.

## Paid-call boundary

One explicitly authorized SpineForge attempt means at most:

1. Aion Creative Architect
2. Sonnet Structural Hardener, only if Aion output is valid
3. Luna Product Gate, only if Sonnet does not REPLAN and hardening is valid
4. STOP

There is no parse/model retry inside the attempt.
A new attempt requires new explicit authorization.

## Frozen-runtime rule

The first paid qualification case starts only after runtime freeze.

Once a case begins:
- character/world/Saga/state/premise may vary as data;
- revision feedback may vary as data;
- human review may vary as data;
- trigger/evidence/cost ledger may vary as data.

But:
- runtime Python may not change;
- prompts may not change;
- model profile configuration may not change;
- generic workflow may not change.

Every paid attempt verifies SHA-256 hashes before inference.

If any frozen runtime hash changes:
- the active case fails for that runtime revision;
- it cannot later be called a successful no-code qualification;
- a new SpineForge revision must be created;
- qualification restarts from a fresh controlled case.

A scenario-specific Python module, prompt or workflow added during the case counts as failure.

## Cost accounting

Every attempt records:
- model calls;
- input/output/reasoning/cache tokens when returned by provider;
- USD cost;
- model latency.

Final SpineForge accounting separates:
- accepted attempt;
- failed/replanned attempt waste;
- actual all-attempt spend.

At final reporting, USD is also converted to TRY using the then-current USD/TRY rate.

## First frozen qualification case

spineforge.age18.forbidden-cartographer.fantasy.01

Narrative family:
HIGH_FANTASY_MYSTERY

Initial frozen spend:
0 calls / 0 tokens / $0

No paid trigger exists until explicitly authorized.
