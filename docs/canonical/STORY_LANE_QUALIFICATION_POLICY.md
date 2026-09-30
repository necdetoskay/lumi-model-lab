# Story Lane Qualification Policy

Status: CANONICAL — Model Lab

## Principle

LUMI does not require one universal story-production pipeline for every exact age, narrative family, session type, or complexity class.

A pipeline is production authority only for the cohort that its evidence actually qualifies.

Examples:

- an exact-age-12 lane may use one architect / writer / QA arrangement;
- an exact-age-18 lane may use another;
- adult or senior lanes may use different models, prompts, deterministic guards, repair policies, or translation controls.

A successful lane MUST NOT be automatically promoted to neighboring ages.

## Shared platform versus lane-specific policy

The following remain platform-level and reusable:

- workflow execution;
- workflow/task/model profile resolution;
- token / cost / latency lineage;
- budget and retry policy;
- authority-packet primitives;
- deterministic evidence storage;
- publication evidence format.

The following MAY be lane-specific:

- Spine Architect model and prompt;
- Writer model and prompt;
- exact-age maturity profile;
- story-length authority;
- deterministic authority guards;
- judge or adjudicator model;
- repair model and repair policy;
- translation model;
- translation semantic guards;
- fidelity model and escalation rules.

## Qualification levels

### SINGLE_CASE_QUALIFIED

One end-to-end case reached publication-ready with complete evidence.

This proves that the lane can work for that case. It does NOT prove broad production stability.

### COHORT_QUALIFIED

Multiple independent cases inside the same declared cohort pass without unbounded special handling.

The evidence must vary premise/state/branch mechanics enough to show the lane is not overfit to one story.

### PRODUCTION_STABLE

The lane passes the cohort threshold, has bounded failure/escalation behavior, full cost/latency lineage, and no hidden human repair dependency in the normal path.

## Age18 current authority

The current age18 lane profile is:

data/specifications/story_lab/age18_story_lane_profile_v1.json

Current status:

SINGLE_CASE_QUALIFIED

Qualified evidence:

- exact age: 18
- narrative family: ADVENTURE
- EN master -> TR delivery
- 1,600–2,500 word STANDARD session
- final publication-ready artifact:
  data/specifications/story_lab/age18_cross_age_final_delivery_v1.json

The current evidence MUST NOT be interpreted as:

- all age18 stories are qualified;
- all narrative families at age18 are qualified;
- ages 17/19/25/40/60 may reuse this lane without qualification;
- the age12 lane must be replaced by the age18 lane.

## Hard invariant ownership

Whenever a rule can be expressed deterministically and safely, code owns it instead of an LLM judge.

Current examples:

- formal reviewed-record ordering;
- raw notes versus formal-record state;
- hard setup/instrument inference overclaim;
- protected EN->TR semantic distinctions such as title modality and recurrence versus repeatability.

LLM judges remain for semantic gray areas, not as sole publication authority.

## Promotion discipline

A lane may move from SINGLE_CASE_QUALIFIED to PRODUCTION_STABLE only after additional independent cases prove:

1. publication-ready output;
2. no serious authority defects at final delivery;
3. zero hard translation semantic guard findings;
4. bounded repair/escalation behavior;
5. complete token/cost/latency lineage;
6. no unbounded judge/repair loops;
7. no manual hidden rewrite dependency in the normal path.

The qualified cohort and the exact lane manifest SHA must be recorded with every promotion decision.


## Frozen runtime / no-code-change qualification

A lane intended for production-stability qualification MUST support fresh cases without story-specific runtime code changes.

For a frozen qualification revision:

- character/world/origin/Saga/state/premise remain data;
- model feedback after REPLAN may be recorded as data;
- human approval may be recorded as data;
- paid stage triggers and evidence records may change as data;
- runtime Python, runtime prompts, model profile configuration and generic workflow logic are frozen.

The frozen lane profile MUST record SHA-256 hashes for its runtime files. Every paid stage MUST verify those hashes before inference.

If any frozen runtime hash changes during an active case:
- that active case is invalidated for the old runtime revision;
- the change creates a new lane revision;
- qualification must restart from the controlled premise;
- the old case must not be reported as a successful no-code-change production proof.

A scenario-specific Python module, prompt or workflow written after a case starts counts as a failure of that case's frozen-runtime qualification.

A model REPLAN is not itself a runtime failure when the frozen system can consume revision feedback through its existing generic data contract without code modification.

Bounded model repair is permitted only when it was already part of the frozen lane policy before the case began.
