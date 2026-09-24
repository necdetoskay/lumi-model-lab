# ADULT Puzzle Diagnostic Fixture B v1

Date: 2026-09-24  
Status: **FROZEN DIAGNOSTIC FIXTURE**  
Scope: `ADULT × puzzle_problem_solving × STANDARD`

## Purpose

Two independent v3 runs of the canonical ADULT puzzle fixture both passed the
final semantic-judge gate but each required two semantic repairs. Repeating
that same fixture again would increase benchmark-overfit risk.

Fixture B provides a second controlled premise for cross-fixture diagnosis.

## Controlled variables

Fixture B preserves the base fixture's:

- exact age: 32;
- NarrativeAgeTier: ADULT;
- language: English;
- STANDARD target: 4,200 words;
- reading mode: INDEPENDENT_READER;
- narrative family: puzzle_problem_solving;
- protagonist;
- theme;
- complete constraint list.

Only these story-content variables differ:

- title hint;
- setting;
- premise.

No anti-contradiction hint, evaluator-specific wording, easier clue structure,
or threshold-oriented instruction was added.

## Files

Base fixture:

`data/specifications/waves/age-relative-standard-v2/adult--puzzle-problem-solving.yaml`

Diagnostic fixture B:

`data/specifications/diagnostics/adult-puzzle-problem-solving-variant-b-v1.yaml`

## Interpretation

Run Fixture B unchanged through the same Luna runtime/profile, v3 generation
protocol, continuity evaluator and semantic judge.

If Fixture B also meets the anomaly definition (failure, final minimum <= 3,
or at least two semantic repairs), the capability planner may mark the cell
`TARGETED_INTERVENTION_CANDIDATE`.

If Fixture B is clean, the existing repair burden remains fixture-specific
evidence and does not justify model-specific production tuning.
