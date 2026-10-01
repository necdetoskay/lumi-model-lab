# SpineForge v19 — NarrativeSpineV1 single-owner baseline

Status: **v19.1 FROZEN — READY FOR EXPLICIT PAID RERUN AUTHORIZATION**

## Canonical topology

`SpineContextPack.v1`
→ exact reader/story-family obligations
→ **Sonnet 5.5 single Narrative Spine Architect**
→ `NarrativeSpineV1`
→ deterministic authority / reveal / obligation validation
→ **GPT-5.6 Luna compact adversarial Product Gate**
→ human-readable preview
→ **STOP / human approval**

Writer, translation, and canonical-state commit are not callable inside the SpineForge runtime.

## Why v19 exists

v11 proved that one Sonnet owner can produce a nearly valid complete spine in one call. v12 proved that mechanically derivable metadata should not be model-owned. v14-v17 showed that a large scoring/audit surface created repair and transport churn. v19 keeps the successful single-owner direction while replacing the legacy `EpisodeSpineV3` product contract with a smaller story-first contract.

## Product ownership

Sonnet owns story promise, story-family execution, protagonist goal/pressure, central question, stakes, world-specific use, beats, decision when required, climax, payoff, unresolved hooks, reveal limits, outcome candidates, and writer rules.

The application owns ContextPack identity/fingerprint, exact age, session, word targets, authority revisions, eligible milestone ids, commit-only-if-earned, writer authorization, approval ids, and token/cost/latency lineage.

## Deterministic gate

Code rejects objective defects only: stale/mismatched authority, unknown or locked refs, hidden-Saga system markers, exact type/shape problems, duplicate beat keys, reader/story-family obligation mismatch, and a missing required real choice.

Subjective story quality belongs to the Luna Product Gate and then human review.

## Transport

Qualification uses v19-specific **one-shot** transport. There is no automatic HTTP/model retry.

- Sonnet Architect: JSON object transport + local `NarrativeSpineV1` validation.
- NarrativeSpineV1 schema size: **4,633 bytes**. It is intentionally **not** provider-strict.
- Luna Product Gate: provider-strict JSON Schema + local typed validation.
- v19.1 Luna gate schema size: **1,308 bytes**, below the **4,096-byte** strict-schema budget.
- All root properties in the Luna schema are provider-required, including `blocking_findings`.
- Maximum model calls per ordinary qualification case: **2** (Architect + Gate).
- `REPAIR` and `REPLAN` stop the run; no third call executes automatically.
- A Luna transport failure now returns preserved Sonnet Spine + deterministic validation + usage evidence rather than losing the product.

## Qualification matrix

The fixed matrix is:
`data/specifications/story_lab/spineforge_v19_qualification_cases_v1.json`.

All **6/6 ContextPack fixtures are frozen**:

1. age 4 — imaginative friendship/play
2. age 12 — adventure/exploration
3. age 12 — mystery/problem-solving
4. age 18 — Leyra fantasy/mystery control
5. age 40 — consequential adult adventure
6. age 60 — mature adventure/relationship/reflection

Every fixture validates as `SpineContextPackV1`, its canonical fingerprint is recomputed in tests, and reveal-safety checks prohibit hidden payload fields such as `hidden_statement` and `reveal_steps`.

## Original v19 freeze

Original frozen revision:
`SPINEFORGE-NARRATIVE-SPINE-FROZEN-v19`

Original runtime source commit:
`41ab5c5a43b4465207fa76c29fdcb073399c1566`

Original zero-cost GitHub Actions run:
`36887442025` — **SUCCESS**

Original evidence:
- total: **33 PASS**
- freeze verification: **23/23 files verified**
- paid model calls before qualification attempt: **0**
- confirmed spend before qualification attempt: **$0**

## First paid qualification attempt — age 12 Adventure/Exploration

User authorization was consumed for exactly one paid qualification attempt.

GitHub Actions run:
`36888737202`

Trigger commit:
`94020195712edcd2513a32932f1190f58cdcab52`

Case:
`spineforge.v19.age12.adventure-exploration.01`

Observed sequence:
1. frozen runtime verification passed **23/23**;
2. Sonnet 5.5 Architect completed and the runtime advanced past local NarrativeSpine/authority validation;
3. Luna Product Gate request was rejected before Luna inference by provider HTTP 400;
4. no automatic retry executed;
5. Writer remained blocked.

Provider error:
`blocking_findings` existed in the JSON Schema properties but was omitted from the schema root `required` array. OpenAI strict structured output rejected the request as `invalid_json_schema`.

This is classified as a **gate transport/schema defect**, not a Spine story-quality verdict.

### Attempt-1 evidence loss

The original v19 runtime kept the successful Sonnet Spine only in memory until after the Luna stage returned. Because Luna transport raised before the wrapper wrote the result artifact, the Sonnet Spine from this attempt was not persisted and cannot be truthfully reconstructed after the fact.

The produced Spine therefore must **not** be fabricated or approximated for human review.

### Attempt-1 cost evidence

A Sonnet request completed and may have incurred cost. Luna inference did not start because its request was rejected as an invalid schema.

The run did not persist the Sonnet generation id or its per-call usage before the Luna failure. A later read-only OpenRouter diagnostic could only retrieve key-level aggregate usage; those totals are not attributable to this single attempt. Therefore the exact attempt-1 Sonnet token count and cost are recorded as **not recoverable from current evidence** rather than guessed.

Diagnostic run:
`36890009121` — **SUCCESS**

Its paid job was **SKIPPED**; it performed no inference.

## v19.1 corrective freeze

Source fix commit:
`4fc9c582e0ac89b0fad24de1e1f08cfca475c9f3`

Freeze commit:
`b68bf56f82e6c31495dc0e46c7085b38b0d85055`

Frozen revision:
`SPINEFORGE-NARRATIVE-SPINE-FROZEN-v19.1`

Runtime profile:
`data/specifications/story_lab/spineforge_runtime_profile_v19_narrative_spine_frozen.json`

Frozen dependencies:
**23 SHA-256 locked files**

Corrective changes:
- `blocking_findings` is now required in the Luna strict schema;
- strict schema root `required` equals root `properties`;
- Luna gate schema is **1,308 bytes**;
- a gate transport exception is converted to typed evidence `product_gate_transport_failed`;
- the validated Sonnet `narrative_spine`, deterministic report, and Sonnet usage rollup remain recoverable on that failure path;
- no retry, repair, Writer, translation, or state commit is introduced.

Zero-cost verification after the correction:
- **35/35 PASS**
- freeze verification **23/23**
- automatic retry **OFF**
- automatic repair **OFF**
- Writer **BLOCKED**

## First paid-wave acceptance bar

The six fixed cases are intended as a falsification wave, not statistical proof of the long-term 95% product goal.

Required first-wave evidence:
- 6/6 deterministic canon/reveal integrity
- 0 hidden-truth leaks
- 0 technical contract/transport failures
- at least 5/6 human `WRITER_READY`
- age-12 must not repeat the toy-play maturity failure
- age-40 and age-60 must not become child plots with harder vocabulary
- no multi-stage structural compiler

## Paid boundary

Current state: **READY_FOR_EXPLICIT_PAID_RERUN_AUTHORIZATION**

The first paid authorization has already been consumed by run `36888737202`. v19.1 has not yet made a paid model call.

A v19.1 rerun requires a new, explicit user authorization. Do not reuse or rerun the old failed v19 job.

For the next paid case:
1. use the frozen v19.1 runtime unchanged;
2. execute only the age-12 Adventure/Exploration qualification case;
3. no automatic retry;
4. if Sonnet validation fails, stop before Luna;
5. if Luna returns REPAIR or REPLAN, stop;
6. if Luna ACCEPTs, present the exact Spine product to the human;
7. Writer remains blocked until the human explicitly approves the exact ContextPack fingerprint + Spine hash.


## v19.1 paid rerun — age 12 Adventure/Exploration

Explicit rerun authorization produced a successful technical qualification run.

GitHub Actions run:
`36890722855`

Trigger commit:
`9b83ef4135736c5e9b189672366afd03156e5e22`

Case:
`spineforge.v19.age12.adventure-exploration.01`

Result:
`repair_required`

Spine title:
`The Bridge That Pulled Sideways`

Context fingerprint:
`a8f5134f88b68aa270d32abe1ca92488474342874fdec411f1b81015489200ea`

Spine hash:
`0735c6d600ea7a28fd702221f4b6c188b1c4e28c5d962d4427c74c480f7cf8de`

Deterministic validation:
- authority_valid: true
- reveal_safe: true
- obligations_valid: true
- discovery_turns: 7
- real_choice_count: 3

Luna Product Gate:
- decision: `REPAIR`
- one blocking finding
- dimension: `DECISION_QUALITY`
- severity: `MAJOR`
- repairability: `LOCAL`
- target: `narrative_spine.beats[5].character_action`

Gate finding: the Spine presents a real consequential choice, but after the choice it leaves the chosen strategy conditional (ridge vs Echo Span repeat). The climax and final payoff also remain branch-conditional, and the immediate-report option is not staged in the beat structure. Under the breadth branch, the payoff can overclaim repeatability at Echo Span after only one Echo Span reading.

Luna explicitly characterized the premise, agency, causality, discovery, world use, and payoff as otherwise viable.

No automatic repair was executed. Writer remains blocked.

### Usage

Sonnet 5.5 Architect:
- input: 10,801
- output: 3,763
- total: 14,564 tokens
- cost: $0.059232
- latency: 30.425 s

GPT-5.6 Luna Product Gate:
- input: 8,149
- output: 997
- reasoning: 756
- total: 9,146 tokens
- cost: $0.0032335
- latency: 14.627 s

Pipeline total:
- 2 API calls
- 23,710 tokens
- $0.0624655
- 45.052 s model latency
- token and cost reconciliation: PASS

Current boundary:
**STOP_FOR_HUMAN_REVIEW / LOCAL_REPAIR_NOT_AUTHORIZED**

The existing Spine must be shown to the human before any repair or Writer action. A targeted Sonnet patch is a separate paid action and requires explicit authorization.
