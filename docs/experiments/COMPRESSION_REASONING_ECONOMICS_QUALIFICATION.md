# Compression, Long-Context and Reasoning Economics Qualification Track

Status: **Planned Model Lab qualification track**  
Origin: Technology Opportunity Radar analysis of Quasar 438B / CompactifAI, 2026-09-03.

## 1. Goal

Determine whether a compressed, quantized, distilled or reasoning-heavy model provides a real LUMI advantage after accounting for:

- story/continuity quality;
- long-context reliability;
- reasoning volume;
- latency;
- VRAM/memory;
- retries and repair;
- final qualified-task cost.

This track is not a benchmark leaderboard exercise. It is a production-role qualification system.

## 2. Core research questions

1. Can a context-grounded reasoner outperform a stronger generalist on LUMI continuity/review tasks when authoritative state is supplied?
2. Does model compression preserve the exact capability required for the intended LUMI role?
3. Does lower nominal token price remain cheaper after reasoning tokens, validation, repair and retries?
4. What is the smallest reasoning budget that preserves the required success rate for each task class?
5. At what context size does quality or latency degrade materially?
6. Can a compressed/local candidate provide enough quality per VRAM to justify an additional deployment artifact?

## 3. Candidate classes

The track should support comparison across:

- untouched/base models;
- provider-hosted frontier/reference models;
- reasoning-tuned models;
- tensor-network compressed models;
- quantized deployments;
- pruned deployments;
- distilled models;
- QLoRA/LoRA specialists;
- local GGUF/other memory-constrained variants where appropriate.

Every material deployment variant is treated as a distinct candidate even when it shares the same base lineage.

## 4. Initial candidate: Quasar 438B

Quasar 438B is an **ASSESS** candidate only.

Reasons to test:

- reported strong long-context reasoning;
- reported fast generation;
- low nominal token pricing;
- reported strong agentic/coding behavior relative to some peers;
- unusual profile of strong supplied-context reasoning with weaker closed-book knowledge;
- tensor-network compression lineage makes it useful for compression qualification research.

Reasons not to promote directly:

- public benchmark evidence is not LUMI qualification;
- original lineage is undisclosed in the cited material;
- reasoning-token volume may erase nominal price advantage;
- knowledge capability appears uneven;
- provider/runtime characteristics must be tested directly.

## 5. Qualification roles

### Track A — Long-Horizon Continuity Reviewer

Input envelope:

- Canon revision/fingerprint;
- Character DNA;
- Saga state;
- world/region state;
- NPC relationships;
- inventory;
- scene/timeline history;
- proposed next scene or mutation.

Output:

- contradiction set;
- missing prerequisite set;
- unsupported claim set;
- severity;
- evidence pointers to supplied state;
- accept / repair / reject recommendation.

Primary metrics:

- contradiction recall;
- false-positive rate;
- exact evidence grounding;
- unsupported-world-knowledge rate;
- latency;
- total tokens/task;
- reasoning tokens/task where available;
- CPST.

### Track B — Story Architect

Input:

- story premise;
- foundation Canon;
- active Saga/milestones;
- characters/world constraints;
- target length/scene count;
- product/age/safety constraints.

Output:

- story skeleton;
- scene goals;
- causal dependencies;
- branch/rejoin points where applicable;
- continuity obligations handed to downstream scene generation.

Primary metrics:

- global coherence;
- future-scene compatibility;
- Canon adherence;
- character consistency;
- downstream repair count;
- final CPQS contribution.

### Track C — Context-Grounded Reasoning

Construct fixtures where all required truth is present in supplied context and closed-book world knowledge should not be needed.

Measure:

- correct utilization of supplied facts;
- contradictory-fact handling;
- stale-context detection;
- abstention when evidence is missing;
- hallucinated external knowledge;
- context-size degradation.

### Track D — Reasoning Budget Sweep

For representative tasks, run multiple bounded reasoning profiles.

Conceptual sweep:

- R1 economical;
- R2 bounded;
- R3 deep;
- R4 frontier/reference.

Measure quality-versus-cost curves and identify the smallest qualified budget.

## 6. Compression comparison matrix

For every base/compressed pair, record:

| Dimension | Base | Compressed | Delta |
|---|---:|---:|---:|
| role-specific success rate | | | |
| deterministic pass rate | | | |
| judge score | | | |
| human preference | | | |
| contradiction recall | | | |
| long-context score | | | |
| hallucination/unsupported rate | | | |
| abstention rate | | | |
| p50 latency | | | |
| p95 latency | | | |
| throughput | | | |
| peak VRAM/RAM | | | |
| input tokens/task | | | |
| answer tokens/task | | | |
| reasoning tokens/task | | | |
| retries/task | | | |
| repair passes/task | | | |
| cost/task | | | |
| CPST | | | |

Do not collapse this table into one aggregate percentage.

## 7. Economics contract

### Cost Per Successful Task — CPST

```text
CPST =
  total input/context cost
+ reasoning cost
+ answer cost
+ verifier/judge cost
+ retry cost
+ repair cost
+ escalation cost
--------------------------------
successfully qualified tasks
```

### Cost Per Qualified Story — CPQS

For full story-production experiments:

```text
CPQS =
  story architect
+ scene generation
+ continuity review
+ validators/judges
+ targeted repairs
+ retries
+ escalations
--------------------------------
qualified stories
```

Nominal $/1M-token pricing remains recorded but is not the primary economics decision metric.

## 8. Long-context qualification

Advertised context window is not a qualification result.

Run at multiple context bands, for example:

- 8K;
- 16K;
- 32K;
- 64K;
- 100K;
- 200K+ where supported and economically reasonable.

At each band record:

- time to first token;
- total latency;
- exact retrieval/utilization accuracy;
- contradiction detection;
- omitted required facts;
- token usage;
- cost;
- failure/timeout behavior.

The production ceiling should be the largest qualified context band, not the provider-advertised maximum.

## 9. Reasoning-budget qualification

Each candidate should be tested under bounded reasoning profiles where the API/runtime permits it.

Required cases:

1. easy task stays cheap and succeeds;
2. hard task fails under insufficient budget in a detectable way;
3. validator-triggered escalation improves the outcome;
4. over-escalation does not become the default;
5. budget exhaustion is controlled;
6. retry/repair loops remain bounded;
7. total task cost is reconstructed exactly enough for comparison.

## 10. Golden fixture families

Recommended fixtures:

- scene chronology contradictions;
- inventory impossible transfer;
- NPC relationship mismatch;
- Character DNA trait drift;
- Saga prerequisite missing/present;
- world/region continuity;
- weather/clothing/environment consistency;
- object persistence;
- branch/rejoin continuity;
- stale Canon revision;
- missing evidence requiring abstention;
- large-context needle plus cross-reference tasks;
- false friend: plausible general-world knowledge contradicting supplied LUMI Canon.

## 11. Promotion gates

A candidate may be recommended for a LUMI role only when:

- deterministic hard checks pass;
- role-specific quality threshold is met;
- long-context behavior is qualified for the intended band;
- abstention/fail-closed behavior is acceptable;
- no protected mutation authority is inferred from model strength;
- cost/task and CPST/CPQS are measured;
- p95 latency is within role budget;
- compressed variants prove their own capability rather than inheriting base-model status;
- at least one simpler/cheaper baseline is included in the comparison.

## 12. Rejection conditions

Reject or keep research-only when:

- aggregate score hides a critical role regression;
- long-context performance collapses before the intended production band;
- reasoning-token volume makes CPST materially worse than simpler candidates;
- the model hallucinates instead of grounding on supplied Canon/state;
- compression causes severe capability-shape loss;
- the candidate requires unacceptable VRAM/latency for the intended deployment;
- qualification cannot be reproduced.

## 13. Required experiment record additions

Every run in this track should record:

- candidate deployment/artifact id;
- base lineage when known;
- compression/quantization/distillation method;
- parameter/precision information when known;
- role under test;
- context-band id;
- reasoning-budget profile id;
- benchmark/golden dataset version;
- prompt/schema version;
- judge version;
- seed/reproducibility data;
- runtime/hardware;
- peak VRAM/RAM;
- p50/p95 latency;
- token breakdown;
- cost breakdown;
- retry/repair/escalation count;
- deterministic metrics;
- judge metrics;
- human-review outcome where required;
- CPST/CPQS contribution;
- final qualification state.

## 14. Implementation order

1. add schema/record fields for task-level economics and context bands;
2. build golden long-horizon continuity fixtures;
3. establish current LUMI/reference baseline;
4. add one economical non-reasoning/small-model baseline;
5. add Quasar 438B when API access is available;
6. add compressed/local variants as available;
7. run reasoning-budget sweeps;
8. publish capability-specific qualification cards;
9. feed only qualified role profiles into Project_LUMI routing decisions.

## 15. Decision rule

> **A compressed or reasoning-heavy model wins only when it reduces the cost or resource footprint of a qualified LUMI outcome without violating the role's capability, latency, grounding or safety contract.**
