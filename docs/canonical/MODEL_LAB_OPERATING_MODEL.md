# LUMI Model Lab — Canonical Operating Model

Status: **PROPOSED / CANONICAL AFTER MERGE**  
Date: **2026-09-20**  
Repository: **necdetoskay/lumi-model-lab**  
Baseline SHA: `5f6827d0868a16f22976cf2b1aa4520778fa6678`  
Change type: **AEGIS + MUR Retrofit / no rewrite**  
Scope: **Model Lab operating model, experiment routing, qualification authority and fast-path UX**

## 1. Purpose Baseline

LUMI Model Lab exists to answer practical model and agent questions quickly, reproducibly and with enough evidence to avoid false technical conclusions.

Its primary purpose is **not** to reproduce the governance weight of Project_LUMI production.

The lab must optimize for:

1. fast falsification of newly discovered models, providers, runtimes and bounded decision systems;
2. reproducible evidence rather than ad-hoc impressions;
3. role-specific comparison against the current qualified baseline/champion;
4. controlled escalation from cheap screening to rigorous qualification;
5. preservation of historical evidence without allowing historical experiment paths to remain active authorities;
6. clean handoff to Project_LUMI only after a role-specific Model Lab qualification has earned that handoff.

The default user question is therefore not:

> Is model X good?

It is:

> Is model X promising or qualified for LUMI role Y relative to the current evidence-backed baseline for that role?

## 2. MUR Retrofit Decision

The repository contains valuable, working primitives and must **not** be rewritten.

Preserve and reuse where applicable:

- frozen fixtures and benchmark specifications;
- deterministic technical validation;
- semantic judge adapters;
- experiment fingerprints and duplicate protection;
- model registry evidence;
- cost/token ledgers;
- retry/failure provenance;
- local endpoint and training utilities;
- existing `runs/` artifacts and historical experiment records;
- special high-risk qualifications such as the JEV Judge Lab.

The retrofit changes the **operating surface and authority model**, not the historical evidence.

### 2.1 Problems being repaired

The current repository has accumulated multiple experiment-specific runners/configurations and mixes several different intents:

- quick model discovery;
- production-role generator qualification;
- teacher/data generation qualification;
- local student training;
- decision/judge-system qualification;
- historical calibration experiments.

This creates four architectural problems:

1. no single daily entry point;
2. generic model qualification can continue into training-data construction even when the user only wants role quality evidence;
3. registry/leaderboard semantics are not sufficiently role-aware;
4. historical experiment runners can be mistaken for current operating authorities.

This retrofit establishes a role-centric, progressive-gate model.

## 3. Canonical User Flow

The canonical Model Lab flow is:

```text
NEW MODEL / AGENT / RUNTIME
          |
          v
     L1 QUICK SCREEN
          |
     +----+----+
     |         |
 NOT PROMISING  PROMISING
     |         |
    STOP       v
          L2 QUALIFICATION
                |
        +-------+-------+
        |       |       |
      REJECT   HOLD   QUALIFIED
                        |
                        v
              ROLE CHAMPION COMPARISON
                        |
                +-------+-------+
                |               |
          preserve evidence   material gain
                                |
                                v
                         NEW ROLE CHAMPION
                                |
                                v
                   optional Project_LUMI L3
```

No experiment may skip directly from an informal test to production integration.

## 4. AEGIS Progressive Risk Model

AEGIS remains mandatory, but its visible ceremony scales with risk.

### L1 — Quick Experiment

Purpose:

> Decide whether the candidate deserves more time, money or rigorous testing.

Characteristics:

- usually 2–3 representative fixtures;
- deterministic technical validation first;
- small semantic judge sample only when needed;
- basic latency/token/cost capture;
- comparison with the current role baseline when evidence is available;
- no production authority;
- no champion mutation;
- no dataset/training side effect;
- no epic required for an ordinary model screen.

Allowed outcomes:

- `PROMISING`
- `NOT_PROMISING`
- `INCONCLUSIVE`

L1 results are evidence, not qualification.

### L2 — Role Qualification

Purpose:

> Determine whether the candidate is qualified for one named LUMI role.

Characteristics:

- frozen role profile;
- versioned fixtures;
- deterministic gates;
- repeated runs where variance matters;
- semantic/task-specific evaluation;
- reliability/failure taxonomy;
- latency and total governed cost;
- repair/retry burden;
- protected/adversarial fixtures when justified by role risk;
- exact fingerprint and immutable evidence artifacts;
- direct comparison with the current champion/baseline.

Allowed outcomes:

- `QUALIFIED`
- `HOLD`
- `REJECT`

A `QUALIFIED` result does not automatically become champion.

### L3 — Project_LUMI Integration

L3 is outside ordinary Model Lab execution.

Purpose:

> Determine whether a qualified Model Lab candidate may become a Project_LUMI production dependency or authority.

Project_LUMI owns:

- shadow integration;
- runtime contracts;
- production data/state authority;
- rollback/disable strategy;
- cutover;
- migration;
- security/integrity verification.

Model Lab may produce an L3 handoff packet but must not silently mutate Project_LUMI runtime.

## 5. Role-Centric Architecture

Qualification identity is role-specific.

A model can be qualified for one role and rejected for another.

Initial canonical role identifiers:

- `story-generator`
- `story-judge`
- `story-architect`
- `continuity-reviewer`
- `teacher-data-generator`
- `structured-extractor`
- `decision-router`
- `opportunity-ranker`
- `npc-reaction-selector`
- `local-student`

New roles may be added only with a versioned role profile.

### 5.1 Role profile contract

Every active role profile must define at minimum:

- `role_id`
- `profile_version`
- `risk_class`
- intended workload and explicit non-goals;
- fixture set / dataset partition;
- deterministic preconditions and hard gates;
- semantic/task metrics;
- default quick-screen subset;
- full qualification matrix;
- repeat policy;
- judge/reference policy;
- failure taxonomy;
- cost/latency metrics;
- champion comparison policy;
- promotion/material-gain policy;
- fingerprint inputs.

Role profiles are configuration and policy, not model-specific code.

## 6. Canonical CLI Surface

The daily operating surface must converge on one command module:

```bash
python -m src.lab quick --model "<provider/model>" --role <role>
python -m src.lab qualify --model "<provider/model>" --role <role>
python -m src.lab status --role <role>
```

Additional explicit commands may include:

```bash
python -m src.lab compare --role <role> --challenger "<provider/model>"
python -m src.lab dataset-build --model "<provider/model>" --role teacher-data-generator
python -m src.lab train --profile <training-profile>
```

The first three commands are the canonical daily Model Lab path.

Experiment-specific scripts may continue to exist internally while the retrofit is being completed, but they must not remain parallel user-facing authorities.

## 7. Quick Screen Contract

A quick screen must:

1. resolve the requested role profile;
2. resolve the candidate/provider identity;
3. resolve the current comparable baseline/champion when available;
4. compute an experiment fingerprint;
5. refuse accidental duplicate paid execution when exact evidence already exists;
6. run the profile's quick deterministic fixtures;
7. stop before semantic judge cost if deterministic hard gates fail;
8. run only the profile's quick semantic subset when eligible;
9. record cost, latency, tokens and failures;
10. emit one normalized result card.

A quick screen must **not**:

- generate training datasets;
- mutate champion state;
- promote to Project_LUMI;
- silently trigger a full qualification;
- inherit qualification from another role.

## 8. Full Qualification Contract

A full qualification must reuse exact quick-screen evidence when the fingerprint and protocol are identical.

It must then execute only the remaining role-defined qualification matrix.

A full qualification must not automatically enter data-generation/training workflows unless the selected role explicitly owns that work.

This rule repairs the current coupling between generic model qualification and teacher/data pipeline construction.

## 9. Training and Dataset Boundary

Training-data generation is a separate explicit workflow.

Only roles such as `teacher-data-generator` may authorize:

- source-story generation;
- supervised extraction;
- deterministic curation;
- frozen dataset construction.

A successful `story-generator` or `story-judge` qualification must never create a training dataset as a side effect.

Likewise, local student training is an explicit training workflow, not a hidden extension of generic model qualification.

## 10. Registry v2

The canonical registry identity becomes role-aware.

Minimum identity:

```text
candidate/model identity
+ role_id
+ profile_version
+ protocol fingerprint
+ runtime/provider identity
```

Each registry record must contain:

- candidate identity;
- role;
- profile version;
- experiment fingerprint;
- execution mode: `quick | qualification | training | auxiliary`;
- status/verdict;
- exact evidence location;
- technical metrics;
- semantic/task metrics;
- reliability metrics;
- latency;
- tokens;
- governed cost;
- failure/repair counts;
- comparison baseline identity;
- delta versus baseline when comparable;
- timestamps;
- code/config provenance.

Historical registry entries remain immutable evidence and may be imported/projected into Registry v2 without changing their original artifacts.

## 11. Champion Model

Champion is a **role-scoped pointer**, not a global model ranking.

A role may have:

- one current qualified champion;
- zero or more qualified challengers;
- historical champions preserved as evidence.

A challenger may replace a champion only when:

1. both are comparable under the same role contract or a documented evidence-compatibility rule;
2. the challenger passes all hard gates;
3. material gain is demonstrated on the role's declared objectives;
4. no unacceptable regression appears in protected dimensions.

Lower price alone does not automatically replace a higher-quality champion unless the role profile explicitly permits cost-first selection.

Champion change must be an explicit decision record, never an automatic leaderboard sort side effect.

## 12. Normalized Result Card

Every L1/L2 execution must emit a common result summary.

Minimum fields:

```text
Candidate
Role
Profile version
Mode
Technical pass
Primary semantic/task score
Reliability
Critical failures
Latency p50/p95 where applicable
Total governed cost
Cost per successful task where applicable
Retry/repair burden
Current baseline/champion
Comparable delta
Verdict
Evidence fingerprint
Evidence path
Recommended next action
```

The result card is a human entry point; raw evidence remains the authority.

## 13. Historical Experiment Policy

Historical experiment-specific scripts/configs and `runs/` artifacts are evidence and must not be deleted merely to simplify the active interface.

However:

- historical runners are not canonical entry points;
- superseded configs must be marked historical/exploratory or moved to a clearly historical namespace;
- no obsolete multi-model search matrix may remain the apparent active config after a canonical decision freezes a different matrix;
- active README/docs must point to the unified CLI and role profiles;
- no permanent dual authority is allowed between `src.lab` and older ad-hoc runners.

Retirement may be staged, but authority must be singular.

## 14. Relationship to Existing JEV Judge Lab

The JEV Judge Lab remains valid and intentionally more rigorous.

JEV is a candidate decision authority, so its existing gold-label, false-PASS, calibration, counterfactual, red-team and cascade-economics work must not be weakened by this retrofit.

JEV may reuse the unified typed workload/evidence harness, but:

- its Judge qualification remains independent;
- its extension tracks remain independent;
- no GO verdict transfers across workload roles;
- the Fast Path must not collapse JEV's L2 evidence requirements into an ordinary quick model screen.

## 15. Retrofit Migration Rules

This is a retrofit, not a rewrite.

Order of implementation:

1. freeze this operating contract;
2. introduce role-profile schema;
3. introduce unified CLI facade over existing trusted runners;
4. introduce role-aware Registry v2 and projection/migration of historical evidence;
5. implement quick screen;
6. implement full role qualification;
7. separate dataset/training workflows from generic qualification;
8. normalize result cards and comparison;
9. retire active authority from superseded scripts/configs;
10. run AEGIS + MUR retrofit review before declaring the old operating surface retired.

At each step existing evidence must remain inspectable.

## 16. No-Dual-Authority Rule

After a role is migrated to the unified operating model:

- `src.lab` + the role profile are the active execution authority;
- old role-specific scripts may exist only as internal implementation modules or historical tools;
- old configs may not silently override role-profile policy;
- two registries may not independently claim current champion authority;
- two different promotion paths may not exist.

Temporary migration adapters are permitted only when clearly bounded and removed before final retrofit closeout.

## 17. Failure Semantics

The lab must distinguish at least:

- provider/request failure;
- runtime/hardware failure;
- protocol/config incompatibility;
- deterministic technical failure;
- semantic/task failure;
- judge/evaluator failure;
- evidence/integrity failure.

Provider or harness failure must not be misreported as model-quality rejection.

Every retry or repair that changes total cost or latency must remain visible in evidence.

## 18. Cost Principle

Fast-path optimization means **cost-aware sequencing**, not cost-first model choice.

Default order:

1. cheap deterministic checks;
2. minimal representative generation/task execution;
3. semantic judge only when eligible;
4. full qualification only after L1 value signal;
5. expensive adversarial/human work only when role risk or decision uncertainty justifies it.

For close quality results, role-specific economics may break ties only according to the role profile.

## 19. Change Control

Material changes to any of the following require updating this document or an explicitly superseding canonical ADR/contract:

- L1/L2/L3 authority boundaries;
- role profile contract;
- registry identity;
- champion semantics;
- quick/full promotion boundaries;
- training/dataset side-effect boundary;
- no-dual-authority rule;
- Project_LUMI handoff boundary.

Experiment-specific thresholds belong in versioned role profiles and do not require editing this document unless they change the operating model itself.

## 20. Retrofit Definition of Done

The retrofit is complete only when:

- one canonical daily CLI exists;
- at least `story-generator` and one non-generator role execute through role profiles;
- quick screen produces normalized evidence without training/data side effects;
- full qualification can resume/reuse eligible quick evidence;
- Registry v2 is role-aware;
- champion is role-scoped and explicitly changed;
- generic qualification no longer implies dataset construction;
- historical evidence remains readable;
- active documentation no longer presents superseded experiment scripts as equal authorities;
- no active dual-authority path remains;
- AEGIS architecture/security/integrity review and MUR retrofit verification are green.

## 21. Immediate Product Decision

The repository will adopt **Model Lab Fast Path** as the target operating model.

The implementation must prefer thin orchestration and reuse of existing proven components over rewriting benchmark, judge, fingerprint, cost or training primitives.

The first implementation slice is:

1. role-profile contract;
2. `src.lab quick|qualify|status`;
3. Registry v2 role identity;
4. `story-generator` profile;
5. normalized result card.

All later cleanup follows evidence from that vertical slice.
