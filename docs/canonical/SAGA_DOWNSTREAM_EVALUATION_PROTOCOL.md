# Saga Downstream Evaluation Protocol — Canonical Lab Protocol

Status: **PROPOSED / LAB-ONLY**  
Depends on: `LONG_HORIZON_SAGA_LAB.md` and `CHARACTER_NARRATIVE_BLUEPRINT_V1.md`

## 1. Purpose

This protocol tests whether a generated Saga Blueprint is useful **after creation**.

A blueprint that scores well as a standalone document but fails to improve later story behavior is considered unsuccessful.

## 2. Experimental comparison

For each frozen fixture, preserve equivalent initial Character/World inputs and compare:

| Arm | Blueprint | Saga context in stories | JEV |
|---|---:|---:|---:|
| A | current baseline | current behavior | no |
| B | premium v1 | yes, bounded eligible projection | no |
| C | premium v1 | withheld | no |
| D | premium v1 | yes | optional candidate ranking/judging |

Arm B vs C isolates the downstream effect of using Saga context.

Arm B vs A measures end-to-end improvement over the current approach.

## 3. Cycle protocol

Each case runs repeated cycles:

```text
State N
  ↓
Opportunity set
  ↓
Chosen opportunity
  ↓
Deterministic Saga eligibility
  ↓
Optional candidate ranking
  ↓
Bounded Story Contract
  ↓
Mid-tier story generation
  ↓
Compatibility evaluation
  ↓
Structured outcome
  ↓
Synthetic state mutation
  ↓
State N+1
```

The same premium architect must not secretly rewrite the blueprint every cycle.

## 4. Scenario schedule

The frozen schedule must include both Saga and non-Saga pressure.

A representative 12-cycle case may intentionally include:

1. unrelated world opportunity;
2. relationship event;
3. exploration;
4. possible foreshadow;
5. unrelated world consequence;
6. no Saga usage;
7. branch-relevant decision;
8. long-distance travel;
9. dormant-thread recovery opportunity;
10. conflicting new relationship/state;
11. eligible Saga opportunity;
12. possible milestone.

The schedule constrains **test conditions**, not story content.

## 5. Seed-selection rule

Deterministic eligibility runs first.

Only eligible seeds may enter semantic ranking.

Candidate ranking may return zero selected seeds.

```text
No Saga seed
```

is a valid and often desirable answer.

The system must never maximize seed utilization for its own sake.

## 6. Pre-generation semantic questions

Optional JEV/reference evaluation may score:

- relevance to selected opportunity;
- naturalness if inserted;
- risk of forced intrusion;
- relationship fit;
- knowledge fit.

These are ranking signals only.

## 7. Post-generation semantic questions

The story draft is evaluated on bounded dimensions:

- breadcrumb relevance;
- natural integration;
- reveal-ceiling compliance;
- canon/state compatibility;
- character agency preservation;
- Saga progression validity;
- unnecessary Saga intrusion.

These dimensions must remain separate rather than collapsing into one opaque Saga score.

## 8. Protected failures

The following are hard failures in protected cases:

- hidden secret revealed before eligibility;
- story uses an ineligible seed;
- story gives the character knowledge they do not have;
- story assumes an unchosen future action;
- story contradicts committed Origin;
- story contradicts current Character/World state;
- story forces immediate follow-up;
- dormant Saga cannot recover without retcon;
- blueprint requires a specific missed route to continue.

## 9. Useful Saga Integration

A Saga integration is useful only if all are true:

1. the seed was eligible;
2. it was relevant to the selected opportunity;
3. its presence improves or meaningfully deepens the story;
4. it obeys reveal limits;
5. it preserves agency;
6. it does not create canon/state contradiction.

Raw "seed appeared in story" counts are not sufficient evidence.

## 10. Forced Saga Intrusion

Count an intrusion when Saga content is inserted even though:

- no seed was meaningfully relevant;
- the story was naturally complete without Saga;
- the insertion reads like exposition or quest prompting;
- the story bends world/character behavior to service Saga.

A system with high integration and high intrusion is not considered successful.

## 11. Dormancy test

At least one case per major test set must keep a thread dormant for several story cycles.

Pass behavior:

```text
thread remains dormant
→ no periodic forced reminders required
→ world continues normally
→ later state makes a seed eligible
→ re-entry is natural and canon-safe
```

Fail behavior includes exposition dumps, retcon or fabricated memories used to reconnect the thread.

## 12. Divergence test

The simulator must create at least one unexpected state that invalidates an initially plausible milestone.

The system must:

- preserve past canon;
- mark the future path invalid or irrelevant;
- continue through another valid path or dormancy;
- not force the original milestone.

## 13. Counterfactual tests

For selected cycles generate controlled variants:

- same opportunity, Saga context removed;
- same opportunity, one irrelevant seed added;
- same opportunity, one relevant state fact changed;
- entity names changed while relationships are preserved;
- context ordering changed;
- hidden reveal ceiling tightened.

Expected behavior must change only where causally relevant.

## 14. Reference evaluation

Final experiment conclusions should not rely only on JEV.

Use a reference stack such as:

```text
deterministic protected checks
+ strong LLM judge
+ blind human sample for calibration/edge cases
```

If JEV is evaluated, compare it against this reference evidence.

## 15. Minimum report

Every model/fixture report should include:

- blueprint validity;
- blueprint depth summary;
- thread/seed counts;
- cycle completion rate;
- useful Saga integration rate;
- forced Saga intrusion rate;
- premature reveal count;
- canon/state violation count;
- agency violation count;
- dormancy recovery result;
- divergence recovery result;
- narrative-lift comparison;
- premium generation cost;
- mid-tier story cost;
- judge cost;
- total latency;
- notable failure inventory.

## 16. Interpretation rules

Do not declare success because:

- the JSON is large;
- the blueprint sounds literary;
- the model created many threads;
- Saga appears in most stories;
- one demo story contains an impressive callback.

Success requires **repeatable downstream lift with low intrusion and zero protected integrity failures**.

## 17. Exit from Model Lab

A successful final verdict creates a design handoff only.

Production integration requires a new Project_LUMI AEGIS L3 epic covering persistence, migrations, runtime state transitions, world bindings, StoryContract projection, commit semantics, observability and rollback.
