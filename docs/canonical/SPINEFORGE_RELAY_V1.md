# SpineForge Relay v1 — Stateful Scene Relay Architecture

Status: Q0 qualification baseline  
Short name: SFR-v1  
Branch: `experiment/spineforge-relay-v1`

## 1. Decision

SpineForge remains responsible for producing and freezing the global story spine. SFR-v1 changes the downstream story-writing boundary.

The story is no longer generated as one mutable long-form artifact and then repeatedly audited/repaired. Instead, the frozen global spine is compiled into scene plans, scenes are generated sequentially, each accepted scene is frozen, and only a structured story state is relayed forward.

Canonical invariant:

> Global Spine defines the future. Story State defines the accepted past. Scene Contract defines the current step.

## 2. Scope

SFR-v1 solves this problem:

> Given an approved/frozen spine, turn it into a coherent story without losing physical, causal, spatial, epistemic, inventory, or character-state continuity.

It does not repair a weak global spine and it does not change production LUMI until qualification passes.

## 3. Pipeline

~~~text
LUMI Canonical State
        |
        v
Story Context / Story Intent
        |
        v
Frozen Global Spine
        |
        v
Scene Planner
        |
        v
ScenePlan.v1[]
        |
        v
+----------------------------------+
|         SCENE RELAY LOOP         |
|                                  |
| Current StoryState.v1            |
| + ScenePlan.v1                   |
| + Story Intent                   |
| + Relevant Canon                 |
|          |                       |
|          v                       |
| SceneContract.v1                 |
|          |                       |
|          v                       |
| Scene Writer                     |
|          |                       |
|          v                       |
| Local Validation                 |
|      |            |              |
|    PASS         FAIL             |
|      |            |              |
|      |       one rewrite         |
|      |            |              |
|      |       PASS / STOP         |
|      v                           |
| SceneArtifact.v1 FREEZE          |
|      |                           |
|      v                           |
| SceneDelta.v1                    |
|      |                           |
|      v                           |
| deterministic reducer            |
|      |                           |
|      v                           |
| next StoryState.v1               |
+------|---------------------------+
       |
       v
Final deterministic assembly
       |
       v
Final structural verification
       |
       v
Story Artifact
~~~

## 4. Authoritative order

When information conflicts, authority is:

1. LUMI Canonical State
2. Frozen Global Spine
3. Current StoryState.v1
4. SceneContract.v1
5. Accepted scene prose
6. Small prose continuity window

Natural-language scene summaries are never authoritative state.

## 5. Required contracts

### StoryState.v1
Carries accepted truth across scene boundaries: character locations, conditions, inventory, knowledge, relationships, world state, objects, open/resolved threads, completed spine beats, next beat, and narrative obligations.

### ScenePlan.v1
Maps one or more frozen spine beats into one concrete prose unit. One spine beat is not required to equal one scene.

### SceneContract.v1
The only authoritative working contract for the writer. It binds the scene to exact upstream fingerprints and declares entry state, required events, required exit state, immutable facts, forbidden transitions, emotional transition, and word budget.

### SceneDelta.v1
Describes only validated state mutations caused by an accepted scene. A delta never directly overwrites the prior state.

### SceneValidation.v1
Records deterministic and optional semantic validation findings and yields ACCEPT, REWRITE, or REJECT_NON_CONVERGENT.

### SceneArtifact.v1
Stores prose, attempt number, contract/state bindings, validation binding and accepted post-state fingerprint. ACCEPTED artifacts are immutable.

## 6. Scene lifecycle

1. Compile SceneContract.v1 from frozen inputs.
2. Generate one scene only.
3. Run deterministic validation first.
4. Run semantic guard only when required by risk or unresolved deterministic ambiguity.
5. On PASS, freeze the scene.
6. Derive/validate SceneDelta.v1.
7. Apply the delta with a deterministic reducer.
8. Produce the next StoryState.v1.
9. Compile the next scene contract.

A previously accepted scene is never rewritten because a later scene fails.

## 7. Repair policy

Per scene maximum:

- one initial generation;
- one targeted rewrite;
- no second rewrite;
- no full-story repair;
- no automatic retry.

Second failure ends that scene as REJECT_NON_CONVERGENT.

## 8. State rules

- State updates use absolute JSON-pointer-like paths.
- State mutations must be explicit and traceable.
- Scene entry/exit state keys are absolute JSON pointers and are verified against the bound StoryState.
- A persistent mutation path is legal only when the Scene Contract pre-authorizes it through required_exit_state or allowed_state_paths.
- Unplanned object reappearance, ownership changes, and character location jumps therefore fail closed instead of becoming new story truth.
- Open and resolved thread sets cannot overlap.
- A state revision increments only after an accepted scene.
- Upstream fingerprint drift invalidates downstream artifacts before inference.
- Writer output cannot directly mutate canonical state.
- Contract-declared exit state is preferred over semantic extraction where the transition is already known.
- Model-based extraction may propose additional allowed facts, but deterministic validation owns application.

## 9. Global narrative quality

Local correctness alone is insufficient. Story Intent and narrative obligations remain present across the relay.

Examples of obligations:

- character arc targets;
- promises/payoffs;
- foreshadowing;
- climax obligations;
- ending state requirements.

These are stateful obligations, not repeated free-text summaries.

## 10. Cost and latency policy

SFR-v1 may use more writer calls than a one-shot story writer, but each call has smaller context and failures remain local.

The optimization target is total cost per accepted story, not raw API-call count.

Paid inference is forbidden during Q0–Q4. Architecture, contracts, state reducer, stale-input protection and historical failure fixtures must be GREEN first.

## 11. Qualification phases

### Q0 — Architecture baseline
This document exists on the isolated Relay branch. No paid calls.

### Q1 — Contracts
Implement StoryState.v1, ScenePlan.v1, SceneContract.v1, SceneDelta.v1, SceneValidation.v1 and SceneArtifact.v1 with fail-closed validation.

### Q2 — Deterministic state engine
Implement reducer, transition checks, fingerprint binding and immutable-scene semantics.

### Q3 — Historical failure fixtures
Encode previously observed failures, including character-location continuity and object/cordon continuity.

### Q4 — Saved-prose relay simulation
Run Scene -> Delta -> State -> Next Contract using saved artifacts only. Zero API cost.

### Q5 — Single-scene paid qualification
Exactly one scene writer call after explicit paid authorization.

### Q6 — Three-scene sequential relay
Prove state persistence across three generated scenes.

### Q7 — Full-story qualification
Generate one 6–10 scene story end to end with bounded repair.

### Q8 — Repeatability
Run unrelated story inputs without code or prompt patches specific to one story.

## 12. Production acceptance

The candidate cannot approach production until all are true:

- no unlimited retries;
- maximum one rewrite per scene;
- accepted scenes are immutable;
- every scene has entry/exit state bindings;
- every state mutation is traceable;
- stale state fails closed before inference;
- global spine cannot be changed by a writer;
- no full-story rewrite;
- cost/token/latency ledger exists per inference;
- failure identifies exact scene and reason;
- historical continuity fixtures pass;
- multiple unrelated inputs complete without story-specific code/prompt changes.

## 13. Initial success target

First-attempt scene acceptance >= 80%  
Acceptance after at most one rewrite >= 95%  
Non-convergent scenes <= 5%  
Unlimited retries = 0  
Full-story rewrites = 0  
Untracked state mutations = 0

These are qualification targets, not claims of current performance.

## 14. First proof

The first implementation proof is deliberately small:

~~~text
SC01: protagonist enters location carrying object
  -> freeze
  -> state preserves location + object ownership

SC02: protagonist changes floor/location
  -> freeze
  -> state preserves object ownership and updates location

SC03: protagonist meets second character
  -> freeze
  -> both locations + knowledge state are explicit
~~~

If this three-scene chain cannot be represented and validated deterministically, no paid story generation is authorized.

## 15. One-sentence definition

SpineForge Relay v1 is a stateful story-generation pipeline that turns a frozen global spine into a story scene by scene using structured state relay, immutable accepted scenes, explicit scene contracts and bounded local repair.


## 16. Qualification implementation status — 2026-10-06

- Q0 Architecture baseline: GREEN.
- Q1 Contracts: GREEN.
- Q2 Deterministic state engine: GREEN.
- Q3 Historical failure fixtures: GREEN for compass-cord reappearance and Duru location-transition regressions.
- Q4 Three-scene saved-data relay simulation: GREEN.
- Q0-Q4 direct qualification proof: 25/25 pytest PASS on isolated ci-runner clone at tested head 3dfb42068b347b4ece2d88230c7d75dc38997ba7.
- Frozen Q0-Q4 evidence: evidence/spineforge-relay/SFR-V1-Q0-Q4-20261006/result.json.
- Q5 offline preflight + authorization/failure-evidence gate suite: GREEN; total SFR-v1 zero-cost suite 40/40 pytest PASS on isolated ci-runner clone.
- Q5 model: aion-labs/aion-3.5-mini; request class: spineforge_relay_v1_scene_writer; max_tokens: 1600; reasoning: low; max writer calls: 1; automatic retry: false.
- Q5 conservative planned uncached cost: USD 0.006566; authorization ceiling: USD 0.01.
- Q5 authorization cannot enable retries, multiple calls, StoryState application, or production writes.
- Paid failure responses are retained as raw/provider evidence before validation; there is no automatic second call.
- Frozen Q5 preflight SHA256: cc7245e49a5290d1375522bf71069fbf99242e6dc3d73e73a6603d1a4122006d.
- Frozen Q5 artifacts: evidence/spineforge-relay/SFR-V1-Q5-PREFLIGHT-20261006/.
- Q5 generated prose, when eventually authorized, remains WRITER_GENERATED_PENDING_SCENE_REVIEW and cannot mutate StoryState automatically.
- GitHub Actions jobs were still queued at evidence time and are not counted as qualification proof.
- Q5 Single-scene paid qualification: PREPARED, NOT AUTHORIZED, NOT RUN.
- Paid inference calls used by SFR-v1 so far: 0.


## 17. Q5 qualification status — 2026-10-07

The original Aion writer lane is closed for the SC01 qualification run.

- Q5B Aion initial writer produced SC01 but required rewrite: USD 0.00301654.
- Q5G Sonnet semantic guard correctly detected the expected epistemic leaks and word-budget violation: USD 0.019744.
- Q5R Aion bounded rewrite exhausted the output/reasoning budget before usable prose and stopped without retry: USD 0.0084973.
- The Aion SC01 run is therefore REJECT_NON_CONVERGENT. No second rewrite is permitted.
- Frozen StoryState, ScenePlan, FrozenSpineRoute and SceneContract remain unchanged.
- A fresh writer-model qualification lane, Q5S, uses openai/gpt-5.6-sol for the initial SC01 writer only.
- Q5S zero-cost qualification: 65/65 pytest PASS on isolated ci-runner clone.
- Q5S preflight SHA256: 0d4f05380cc8be8a7e5955fdcd57967ace1713ffc950ddf7f7b33a5a7a999d03.
- Q5S conservative planned uncached cost: USD 0.047486; maximum authorized cost: USD 0.05.
- Q5S maximum writer calls: 1; automatic retry: false; state application: false; semantic guard mandatory.
- Q5S paid authorization: AUTHORIZED, not yet consumed at this status checkpoint.
- Production LUMI remains unchanged.
