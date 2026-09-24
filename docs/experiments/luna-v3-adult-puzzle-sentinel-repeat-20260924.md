# Luna v3 Sentinel Repeat — ADULT × puzzle_problem_solving

Date: 2026-09-24  
Status: **PERSISTENT REPAIR BURDEN ON ONE FIXTURE — diagnostic fixture required**

## Cell

- generator: `openai/gpt-5.6-luna`
- generation protocol: `english-story-production.v3`
- age tier: `ADULT`
- narrative family: `puzzle_problem_solving`
- relative length: `STANDARD`
- target: 4,200 words
- continuity evaluator role: `continuity_evaluator`
- semantic judge role: `semantic_judge`

## Runs

| Run | Accepted | Words | Scene attempts | Semantic repairs | Judge avg | Judge min |
|---|---:|---:|---:|---:|---:|---:|
| `35984545658-adult--puzzle-problem-solving` | yes | 3,649 | 9 | 2 | 4.000 | 4 |
| `35988206603-adult--puzzle-problem-solving` | yes | 3,822 | 8 | 2 | 4.000 | 4 |

Both runs passed the final quality gate, but both required two semantic repairs.

The first run concentrated repair on Scene 6 around
`no_contradiction=0.77`. The second run required one Scene 3 repair for
`no_unexplained_dependency=0.78` and one Scene 5 repair for
`no_contradiction=0.79`.

The exact scene differs, but the repeated burden is in the same broader
puzzle-logic / continuity family.

## Decision

Do **not** weaken continuity thresholds and do **not** introduce a production
override yet.

Two stochastic repeats of one benchmark fixture establish persistent burden on
that fixture, but they do not prove that the entire ADULT × puzzle cell is weak.

The next diagnostic must use a second frozen premise with the same governed
axes and a different spec fingerprint. Only if the repair pattern generalizes
across fixtures should a targeted intervention be designed.

Repeatedly sampling the same fixture after this point would increase benchmark
overfit risk and waste qualification budget.
