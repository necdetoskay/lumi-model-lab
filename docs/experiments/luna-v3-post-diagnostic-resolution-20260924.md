# Luna v3 Post-Diagnostic Resolution — 2026-09-24

Status: **EVIDENCE COMPLETE — NO TARGETED INTERVENTION**

Generator: `openai/gpt-5.6-luna`  
Generation protocol: `english-story-production.v3`  
Continuity evaluator role: `continuity_evaluator`  
Semantic judge role: `semantic_judge`

## Purpose

Close the remaining active sentinel and diagnostic escalations after the
adaptive STANDARD qualification program reached complete 24/24 fixture-backed
coverage.

Three independent clean runs were available on the same governed Luna runtime,
generation protocol, evaluation protocol and evaluation stack:

- MIDDLE_CHILD × emotional_development repeat;
- MIDDLE_CHILD × puzzle_problem_solving diagnostic Fixture B;
- YOUNG_ADULT × puzzle_problem_solving sentinel repeat.

No threshold, prompt, runtime profile or production policy changed.

## Results

| Run | Cell / fixture | Accepted | Words | Attempts | Semantic repairs | Judge avg | Judge min |
|---|---|---:|---:|---:|---:|---:|---:|
| `35993576016` | MIDDLE_CHILD × emotional_development | yes | 2,924 | 6 | 0 | 4.000 | 4 |
| `35993713600` | MIDDLE_CHILD × puzzle_problem_solving — Fixture B | yes | 2,697 | 6 | 0 | 4.000 | 4 |
| `35993716751` | YOUNG_ADULT × puzzle_problem_solving | yes | 3,646 | 7 | 0 | 4.000 | 4 |

## MIDDLE_CHILD puzzle diagnostic decision

The base-fixture cohort was:

- `35985914923-middle-child--puzzle-problem-solving`: 10 attempts / 4 repairs;
- `35987414041-middle-child--puzzle-problem-solving`: 6 / 0;
- `35991944331-middle-child--puzzle-problem-solving`: 10 / 4.

Two anomalous runs existed, but both were on the same frozen spec fingerprint.

Fixture B was frozen before execution and changed only title hint, setting and
premise while preserving the governed capability axes and constraint set.

Fixture B result `35993713600` completed at 6 attempts / 0 semantic repairs,
with final semantic judge 4/4.

Current cell state:

- run count: 4;
- distinct spec fingerprints: 2;
- anomalous runs: 2;
- anomalous spec fingerprints: 1;
- diagnostic fixture required: **false**;
- targeted intervention candidate: **false**;
- latest run anomalous: **false**;
- sentinel resolved by clean repeat: **true**.

Therefore the repair burden did **not** generalize across two independent
fixtures. Do not add a Luna-specific MIDDLE_CHILD puzzle prompt, reasoning
override, runtime-policy override or weaker continuity threshold.

## YOUNG_ADULT puzzle sentinel decision

Before the new repeat, the v3 cohort contained:

- one clean run at 6 / 0;
- one anomalous run at 11 / 4.

The new repeat `35993716751` completed at 7 / 0.

Current aggregate:

- 3 runs;
- 1 anomalous run;
- semantic repairs/run: 1.3333;
- scene attempts/run: 8.0;
- latest run anomalous: false;
- sentinel resolved by clean repeat: true.

No further sentinel repeat is currently required.

## MIDDLE_CHILD emotional-development decision

The original adaptive run required 9 attempts / 3 semantic repairs. The first
sentinel repeat completed at 6 / 0. The new density repeat `35993576016`
also completed at 6 / 0.

Current aggregate:

- 3 runs;
- semantic repairs/run: 1.0;
- scene attempts/run: 7.0;
- latest run anomalous: false;
- sentinel resolved by clean repeat: true.

The original burden remains non-reproducible.

## Planner state after resolution

For the 24 fixture-backed STANDARD cells:

- observed: 24;
- UNKNOWN: 0;
- THIN: 9;
- PROVISIONAL: 15;
- ESTABLISHED: 0;
- diagnostic fixture required: 0;
- targeted intervention candidates: 0;
- active sentinel repeat: none.

The next planner batch is ordinary evidence-density expansion. No current cell
qualifies for targeted model-specific intervention.

## Decision

Continue building evidence density under the unchanged shared pipeline.

Do not introduce a Luna-specific age/family override from the current evidence.

The capability system has done what it was designed to do: it separated
repeatable model weakness from single-fixture or stochastic repair burden
without weakening acceptance gates.
