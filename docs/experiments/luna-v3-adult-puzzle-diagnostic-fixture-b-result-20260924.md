# Luna v3 — ADULT Puzzle Diagnostic Fixture B Result

Date: 2026-09-24
Status: **CLEAN CROSS-FIXTURE DIAGNOSTIC — NO TARGETED INTERVENTION**

## Question

The canonical ADULT × `puzzle_problem_solving` fixture produced two accepted
v3 runs that each required two semantic repairs. Fixture-diversity policy
required a second frozen premise before interpreting that burden as a cell-wide
model weakness.

Fixture B was frozen and merged before execution. No prompt, runtime profile,
continuity threshold, judge threshold, or story acceptance rule changed.

## Governed cell

- generator: `openai/gpt-5.6-luna`
- generation protocol: `english-story-production.v3`
- age tier: `ADULT` / exact age 32
- reading mode: `INDEPENDENT_READER`
- narrative family: `puzzle_problem_solving`
- relative length: `STANDARD`
- target: 4,200 words
- continuity evaluator role: `continuity_evaluator`
- semantic judge role: `semantic_judge`

## Cross-fixture evidence

| Run | Fixture fingerprint | Accepted | Words | Scene attempts | Semantic repairs | Judge avg | Judge min |
|---|---|---:|---:|---:|---:|---:|---:|
| `35984545658-adult--puzzle-problem-solving` | `ab7e9fce...` | yes | 3,649 | 9 | 2 | 4.000 | 4 |
| `35988206603-adult--puzzle-problem-solving` | `ab7e9fce...` | yes | 3,822 | 8 | 2 | 4.000 | 4 |
| `35991217402` | `5dbba24f...` | yes | 3,683 | 7 | 0 | 4.000 | 4 |

Fixture B's exact spec SHA-256 is
`5dbba24f40e5cf61c9f17e62cb1b1f834afc5561aef240132c1f0a7f69840a10`.
The base fixture's exact SHA-256 is
`ab7e9fce4be36a635b1c753215c32f82e2ca46942bbaf58008b13c0c25eca46b`.

Fixture B completed with no semantic repair, no critical failure and no final
repair target. One local technical word-budget repair occurred in Scene 2; it
was not a continuity anomaly.

## Pre-registered decision

Fixture B is **not anomalous** under the canonical sentinel definition:

- accepted: yes;
- final semantic-judge minimum: 4 (> 3);
- semantic repairs: 0 (< 2).

The anomaly therefore exists on only one of the two distinct spec
fingerprints. The fixture-diversity guard must resolve as:

- `DIAGNOSTIC_FIXTURE_REQUIRED = false`;
- `TARGETED_INTERVENTION_CANDIDATE = false`.

## Decision

Do **not** add a Luna-specific ADULT/puzzle prompt, reasoning, runtime-policy,
or acceptance-threshold override.

The repeated repair burden is currently fixture-specific evidence, not a
reproducible family-level weakness. Keep all three runs in the Capability Cube
and continue ordinary evidence-density expansion.

A future anomaly on another distinct ADULT puzzle fixture may reopen the
intervention question, but this clean diagnostic closes the present escalation.
