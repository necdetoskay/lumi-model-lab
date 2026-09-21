# Long-Horizon Saga Lab — Canonical Experiment Contract

Status: **PROPOSED / LAB-ONLY**  
Canonical owner: **LUMI Model Lab**  
Risk class: **AEGIS L2 for lab qualification**  
Production integration: **Not authorized by this document**

## 1. Purpose

This track evaluates whether a premium/strong model can create a durable character narrative architecture that improves downstream story generation without pre-writing the character's future.

The system under test is:

```text
Character + World bootstrap
        ↓
Premium Narrative Architect
        ↓
Origin + Present Situation + Narrative Core + Saga Blueprint
        ↓
Deterministic validation
        ↓
Runtime simulation
        ↓
Opportunity + eligible Saga context
        ↓
Mid-tier Story Model
        ↓
Story / Outcome / state transition
        ↓
Repeat across multiple story cycles
```

The primary question is not "Can the strong model write an impressive Saga document?"

The primary question is:

> Does the generated blueprint create durable, optional, world-integrated narrative value across many later stories while preserving character agency, canon integrity and story diversity?

## 2. Core hypotheses

### H1 — Strong-model leverage
A stronger model can create substantially better long-horizon narrative architecture than the current mid-tier character-creation path.

### H2 — Downstream value
A high-quality Saga Blueprint materially improves later story continuity, depth and meaningful callbacks when compared with equivalent stories generated without Saga context.

### H3 — Optionality
The character can ignore Saga threads for many stories without breaking continuity or requiring forced re-entry.

### H4 — Runtime economy
The expensive model can remain sparse: creation-time architecture and rare reweave events, while normal stories continue to use the mid-tier model.

### H5 — Bounded semantic judging
A fast decision model such as JEV may help rank eligible Saga breadcrumbs and judge narrow compatibility dimensions, but must not own deterministic canon/eligibility authority.

## 3. Non-goals

This lab does not:

- integrate the new Saga architecture into Project_LUMI production;
- replace current production Origin/Saga persistence;
- authorize JEV as a production judge;
- pre-write a fixed sequence of future stories;
- force every story to contain Saga content;
- treat high Saga utilization as inherently good;
- allow model output to mutate canonical state without deterministic validation;
- use production user data as an uncontrolled experiment corpus.

## 4. Canonical responsibility split

| Responsibility | Authority under test |
|---|---|
| Origin/Saga blueprint proposal | premium model |
| JSON/schema validity | deterministic code |
| Canon/world hard constraints | deterministic code |
| Seed eligibility | deterministic code |
| Candidate seed relevance ranking | optional JEV / reference judge experiment |
| Story generation | mid-tier model |
| Reveal ceiling enforcement | deterministic checks + semantic judge |
| Story/Saga naturalness | semantic judge |
| Canon commit | out of scope for this lab |
| Reweave proposal | premium model, future phase |
| Production authority | Project_LUMI only, outside this repo |

Deterministic rules always outrank probabilistic recommendations.

## 5. Experiment arms

The minimum comparative design is:

### Arm A — Current baseline
Current/mid-tier character narrative setup and current downstream story behavior.

### Arm B — Premium Blueprint + Saga-enabled runtime
Premium model generates `character-narrative-blueprint.v1`; eligible Saga context may be supplied to the mid-tier story model.

### Arm C — Premium Blueprint generated but withheld from story generation
The premium blueprint exists, but later story generation receives no Saga breadcrumb context.

This arm isolates whether the blueprint itself creates downstream value.

### Arm D — Optional JEV-assisted selection
Same as Arm B, but an experimentally qualified JEV workload ranks already-eligible candidate seeds before story generation.

Arm D is not required to prove the blueprint concept and cannot bypass deterministic eligibility.

## 6. Required test fixtures

The frozen suite must cover multiple age bands and story modes. At minimum include:

- young child;
- older child;
- teenager;
- young adult;
- mature adult;
- exploration-heavy character;
- relationship-heavy character;
- mystery-heavy character;
- low-magic/realistic setting;
- high-fantasy setting;
- science-fiction/space setting;
- character whose initial Saga remains dormant for several cycles.

Fixtures must be model-independent, versioned and hashed.

## 7. Blueprint qualification dimensions

A generated blueprint is not accepted merely because it parses.

Required dimensions include:

- origin coherence;
- origin/world compatibility;
- identity depth;
- thread diversity;
- seed diversity;
- branch optionality;
- non-linearity;
- absence of future-choice precommitment;
- world integration quality;
- reuse-first compatibility;
- reveal-ceiling clarity;
- recovery after dormancy;
- cross-thread coherence;
- long-horizon potential;
- duplicate/redundant seed rate;
- impossible dependency rate.

## 8. Long-horizon simulation

The core proof is multi-cycle, not single-story.

Each frozen case should support a simulation such as:

```text
initial state
  → opportunity
  → optional eligible Saga context
  → story
  → synthetic/structured outcome
  → state transition
  → next opportunity
  → ...
```

Recommended qualification horizon: **10–20 story cycles per case** during the first full experiment.

The sequence must intentionally include:

- Saga-linked opportunities;
- non-Saga world opportunities;
- exploration;
- relationship events;
- long Saga dormancy;
- delayed re-entry;
- branch divergence;
- at least one case where an originally plausible future milestone becomes invalid.

The simulator must not force a predetermined Saga completion path.

## 9. Primary downstream metrics

### 9.1 Useful Saga Integration Rate

Measures how often Saga material is used **when it is contextually appropriate** and the use is judged natural and valid.

High raw utilization is not a goal.

### 9.2 Forced Saga Intrusion Rate

Measures Saga insertion into stories where Saga context is unnecessary or unnatural.

Target direction: as close to zero as practical.

### 9.3 Premature Revelation Rate

Any disclosure beyond the allowed reveal ceiling.

Hard safety target for promotion: **0 protected reveal violations**.

### 9.4 Canon/State Violation Rate

Contradiction with frozen Origin, Character State, World State, knowledge boundaries or prior committed simulation outcomes.

Target: **0 critical violations**.

### 9.5 Agency Violation Rate

Measures whether the generated story assumes a future decision, relationship, travel choice or Saga commitment not chosen by the simulated character/user.

Target: **0 critical agency violations**.

### 9.6 Dormancy Recovery Quality

Measures whether a thread can remain unused for multiple cycles and later reconnect naturally without exposition dumps or retcon.

### 9.7 Story Diversity Preservation

Saga-enabled stories must not collapse into repetitive quest-chain behavior.

### 9.8 Downstream Narrative Lift

Blind evaluation comparing Arm B against A/C for:

- continuity;
- meaningful callbacks;
- character depth;
- world/story integration;
- long-term coherence;
- narrative naturalness.

## 10. JEV boundary

JEV is an optional workload within this track.

Permitted lab questions include:

- Which already-eligible seed is most relevant to this opportunity?
- Does the draft naturally integrate the selected breadcrumb?
- Did the draft exceed the reveal ceiling?
- Does the draft preserve character agency?
- Is Saga progression semantically plausible?

JEV must not decide:

- whether a deterministically ineligible seed becomes eligible;
- whether hidden canon may be revealed;
- whether a world fact exists;
- whether a commit is valid;
- whether production data is mutated.

Any JEV result in this track requires its own workload profile, frozen fixtures, calibration, evidence and verdict. A GO from JEV Judge Lab #27 does not automatically qualify this workload.

## 11. Strong-model economy

The intended architecture under test is:

```text
Character creation / rare reweave  → premium model
Normal story generation            → mid-tier model
Hard validation                     → deterministic code
Narrow semantic selection/judging   → optional JEV
Deep reference evaluation           → strong LLM judge / blind human sample
```

The lab must record provider/model, token usage, latency and cost for all paid calls.

## 12. Evidence contract

Each run must preserve:

- fixture id/version/hash;
- model/provider identity;
- prompt/contract versions;
- full raw blueprint;
- validated normalized blueprint;
- validation errors;
- selected experiment arm;
- per-cycle inputs and outputs;
- seed eligibility state;
- seed selection rationale;
- story draft;
- semantic judgments;
- synthetic/structured outcome;
- next-state snapshot;
- token/latency/cost;
- experiment fingerprint.

Intentional reruns create new evidence; previous runs are never overwritten.

## 13. Falsification cases

The suite must try to prove the design wrong with at least:

- attractive but linear quest chains;
- premature secret disclosure;
- Saga inserted into unrelated stories;
- duplicated seeds with different wording;
- a missed NPC route followed by successful alternate re-entry;
- long dormancy;
- character moving to another region/world;
- relationship state reversing an expected milestone;
- a seed becoming impossible;
- a branch invalidating another branch;
- contradictory model-created future facts;
- hidden knowledge leak;
- irrelevant-context flooding;
- the same story opportunity with and without Saga context.

## 14. Promotion decision

The lab verdict is **GO / HOLD / REJECT** for a future Project_LUMI design handoff.

GO requires evidence that:

- premium blueprints create measurable downstream lift;
- benefit persists across multi-cycle tests;
- forced intrusion remains low;
- protected canon/reveal/agency violations are zero;
- normal story generation remains mid-tier viable;
- cost is justified by downstream value;
- the blueprint remains usable after dormant and divergent paths.

GO does **not** authorize production integration. It authorizes creation of a separate Project_LUMI AEGIS L3 integration epic.

## 15. Change control

Material changes to experiment arms, protected metrics, blueprint semantics, authority boundaries or promotion gates must update this document before final evaluation.


## 16. Issue map / execution order

Epic: **#55 — Long-Horizon Saga Lab — Premium Narrative Blueprint Qualification**

- **#56 P0** — freeze canon, exact SHA and experiment boundaries
- **#57 P1** — role profile, strict JSON Schema and frozen fixtures
- **#58 P2** — premium Narrative Architect generator + immutable evidence ledger
- **#59 P3** — deterministic Blueprint Validator + static falsification
- **#60 P4** — current baseline vs premium Blueprint quality/economics
- **#61 P5** — Saga runtime simulator, eligibility and bounded Story projection
- **#62 P6** — A/B/C downstream story experiment
- **#63 P7** — 10–20 cycle long-horizon dormancy/divergence/recovery qualification
- **#64 P8** — optional JEV Saga workload qualification
- **#65 P9** — independent AEGIS/MUR review and GO/HOLD/REJECT

Core critical path:

```text
#56 → #57 → #58/#59 → #60 → #61 → #62 → #63 → #65
```

#64 is optional/non-blocking for the core Saga verdict and may run once #61 provides deterministic eligibility and bounded Saga projections.
