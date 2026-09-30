# Age18 Frozen Lane v1

Status: FROZEN_RUNTIME_CANDIDATE

## Purpose

Prove that an age18 story can run from controlled premise to final delivery without writing or changing runtime code for that story.

The active runtime is:

AGE18-FROZEN-v1

Profile:

data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json

## Non-negotiable rule

Once a qualification case starts against this frozen revision:

- scenario/world/character/premise/state data may change;
- revision feedback may be added as data after a model REPLAN;
- human spine approval may be recorded as data;
- paid stage trigger data may change;
- result/evidence/cost-ledger data may change.

But runtime code, runtime prompts, model profiles, and the generic workflow may NOT change.

If any hashed runtime file changes:
- the active case is invalidated;
- the case is recorded as FAIL for this runtime revision;
- a new lane revision must be created;
- the qualification case restarts from the controlled premise.

No scenario-specific Python script, prompt, or workflow is allowed.

## Generic stage topology

SPINE
- Sonnet 5.5 generic architect v3
- generic semantics-preserving safe normalization
- Luna generic spine gate v3
- STOP for human review

WRITER
- Aion 3.5 Mini
- authority packet v2
- one paid attempt

ENGLISH QA
- deterministic hard authority guards first
- if hard defect exists: no Luna spend; confirmed defect goes to bounded repair
- if hard-clean: Luna semantic authority gate
- Luna findings require conditional Sol adjudication
- confirmed local defects may receive one bounded Sol repair
- authority gate must be rerun after repair
- one English paid repair attempt maximum

TRANSLATION
- Gemini 3.8 Flash EN->TR
- deterministic translation semantic guards first
- one bounded Gemini translation repair maximum

FIDELITY
- Luna only after deterministic translation guards are clean
- Luna findings require conditional Sol adjudication
- confirmed finding may use the one bounded translation repair if still available
- remaining blocker after bounds => STOP / case FAIL

FINAL
- publication_ready required
- complete product-path token/cost/latency rollup
- separate qualification/debug waste
- separate historical pre-freeze discovery waste
- final USD totals converted to TRY using the current USD/TRY rate at delivery time

## Current fresh case

age18.forbidden-cartographer.fantasy.frozen-01

This case restarts from the controlled Leyra premise.
It intentionally does NOT feed the pre-freeze F1 REPLAN feedback into the first frozen spine call.

Historical pre-freeze discovery spend remains recorded:
- 2 calls
- 30,093 tokens
- $0.09225655
- 57.531s

Frozen attempt starts at:
- 0 calls
- 0 tokens
- $0
- 0s
