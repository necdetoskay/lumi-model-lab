# Luna v3 — MIDDLE_CHILD Puzzle Diagnostic Fixture B Result

Date: 2026-09-24
Status: **CLEAN CROSS-FIXTURE DIAGNOSTIC — NO TARGETED INTERVENTION**

## Question

The canonical MIDDLE_CHILD × `puzzle_problem_solving` fixture produced three
accepted v3 runs at `10/4`, `6/0`, and `10/4` scene attempts / semantic
repairs. Two heavy runs on the same spec fingerprint triggered the canonical
fixture-diversity guard.

Fixture B was frozen and merged before execution. No generator profile,
production policy, prompt threshold, continuity threshold, semantic-judge
threshold, or acceptance rule changed.

## Governed cell

- generator: `openai/gpt-5.6-luna`
- generation protocol: `english-story-production.v3`
- age tier: `MIDDLE_CHILD` / exact age 10
- reading mode: `INDEPENDENT_READER`
- narrative family: `puzzle_problem_solving`
- relative length: `STANDARD`
- target: 2,800 words
- continuity evaluator role: `continuity_evaluator`
- semantic judge role: `semantic_judge`

## Cross-fixture evidence

| Run | Fixture fingerprint | Accepted | Words | Scene attempts | Semantic repairs | Judge avg | Judge min |
|---|---|---:|---:|---:|---:|---:|---:|
| `35985914923-middle-child--puzzle-problem-solving` | `8cc1f5fe...` | yes | 2,758 | 10 | 4 | 4.000 | 4 |
| `35987414041-middle-child--puzzle-problem-solving` | `8cc1f5fe...` | yes | 2,724 | 6 | 0 | 4.000 | 4 |
| `35991944331-middle-child--puzzle-problem-solving` | `8cc1f5fe...` | yes | 2,698 | 10 | 4 | 4.000 | 4 |
| `35993713600` | `b2b742a7...` | yes | 2,697 | 6 | 0 | 4.000 | 4 |

Base fixture SHA-256:

`8cc1f5fe01d70f77b7c40052da1126edd78fc110c9696d315c2948ae36bf220b`

Fixture B SHA-256:

`b2b742a750a51f0db164a54111bc52df9cb4d30aef28478a9bec617af415eb44`

Fixture B completed with no semantic repair, no critical failure and no final
repair target.

## Pre-registered decision

Fixture B is **not anomalous** under the frozen diagnostic definition:

- accepted: yes;
- final semantic-judge minimum: 4 (> 3);
- semantic repairs: 0 (< 2).

The heavy burden exists on only one of two distinct fixture fingerprints.
Therefore:

- `DIAGNOSTIC_FIXTURE_REQUIRED = false`;
- `TARGETED_INTERVENTION_CANDIDATE = false`.

## Decision

Do **not** add a Luna-specific MIDDLE_CHILD/puzzle prompt, reasoning,
runtime-policy or threshold override.

The evidence supports fixture-specific difficulty/variance rather than a
reproducible age-family weakness. Preserve all runs in the Capability Cube and
continue normal evidence-density expansion.
