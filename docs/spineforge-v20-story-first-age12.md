# SpineForge v20 — Story-First Age-12 Qualification

Status: **FROZEN / READY_FOR_EXPLICIT_PAID_SPINE_AUTHORIZATION**

## Goal

Replace the rejected procedural age-12 Echo Span premise with a story-first qualification case while preserving the proven single-owner SpineForge architecture.

The new case is:

**The Island That Wasn't on Any Map**

## Story premise

After a storm, Arda and Nisa see a forested floating island appear in a region every current chart marks as empty sky. A temporary post-storm corridor gives them one short chance to reach it before the island disappears into a dense cloud wall.

They land, explore, and discover concrete evidence that someone reached the island long before them. The deeper discovery conflicts with the shrinking route home.

The episode must contain a real choice between going farther and turning back, and the final Spine must commit to one path rather than leaving both branches conditional.

The episode must end with one concrete, emotionally satisfying discovery about the island's prior history while its larger origin and destination remain unresolved.

## Story-first protections

The age-12 case now explicitly rejects:
- repeated measuring, testing, logging, reporting, or procedural verification as the main entertainment loop;
- training-exercise, inspection-task, engineering-worksheet, or qualification-test feeling;
- technical vocabulary or reasoning used as a substitute for excitement or maturity;
- passive protagonist behavior;
- adults solving the central problem;
- conditional post-choice branches.

The intended maturity source is:
- active exploration;
- wonder;
- uncertainty;
- social tension and trust with Nisa;
- consequential choice;
- risk;
- discovery;
- earned local payoff.

## Session authority

STANDARD:
- minimum: 1,600 words
- maximum: 2,500 words

No Writer call is part of SpineForge qualification.

## Frozen runtime

Runtime id:
`spineforge.contextpack.v20.story-first-single-owner`

Runtime revision:
`SPINEFORGE-STORY-FIRST-FROZEN-v20`

Runtime source commit:
`35f34935b7f1a90dc78cdbd8607708157c49f30b`

ContextPack:
`data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json`

Context fingerprint:
`090ae8343daa2b24e95923ee9e9dc11356664baed9a79c4ff95fd0207b834233`

Qualification case:
`spineforge.v20.age12.adventure-exploration.island.01`

Runtime profile:
`data/specifications/story_lab/spineforge_runtime_profile_v20_story_first_frozen.json`

Frozen dependency verification:
**19/19 PASS**

## Architecture

`SpineContextPack.v1`
→ exact v20 story-first obligations
→ **Sonnet 5.5 Story-First Narrative Spine Architect**
→ `NarrativeSpineV1`
→ deterministic authority/reveal/obligation validation
→ **GPT-5.6 Luna compact adversarial Product Gate**
→ human-readable preview
→ **STOP / human review**

Models remain unchanged from the proven v19.1 topology:
- Architect: `anthropic/claude-sonnet-5.5`
- Product Gate: `openai/gpt-5.6-luna`

The v19 transport, contract, deterministic validator, usage ledger, and human-review boundary are reused rather than reimplemented.

## Human review state machine

Human review supports:
- `APPROVE` → `WRITER_READY`
- `REVISE` → `HUMAN_REVISION_REQUIRED`
- `REJECT` → `HUMAN_REJECTED_PREMISE`

Writer authorization remains false unless:
1. Luna Product Gate returns `ACCEPT`;
2. the human explicitly approves the exact ContextPack fingerprint + Spine hash.

A human premise rejection closes the Spine and requires a separately authorized replan.

## Zero-cost evidence

Local:
- **13/13 PASS**
- freeze verification **19/19 PASS**

GitHub Actions:
- run `36906825966`
- conclusion: **SUCCESS**
- freeze verification: **19 files**
- tests: **13 passed**

Paid inference during v20 setup:
- Sonnet calls: **0**
- Luna calls: **0**
- Writer calls: **0**
- confirmed v20 setup spend: **$0**

## Paid boundary

Current state:

**READY_FOR_EXPLICIT_PAID_SPINE_AUTHORIZATION**

A paid v20 qualification must not execute from a generic continuation instruction.

Fresh explicit authorization is required for exactly one paid attempt, for example:

`v20 Haritalarda Olmayan Ada paid Spine denemesini başlat`

When authorized:
1. run exactly one frozen v20 attempt;
2. no automatic retry;
3. Sonnet produces one complete Spine;
4. deterministic validation runs;
5. Luna gates it;
6. REPAIR or REPLAN stops immediately;
7. ACCEPT still stops for human review;
8. show the exact Spine, gate result, ContextPack fingerprint, Spine hash, token/cost/latency;
9. Writer remains blocked until separate explicit human approval.


## v20.1 paid-evidence preflight freeze

A zero-cost paid-run harness preflight was added before any inference authorization.

Frozen revision:
`SPINEFORGE-STORY-FIRST-FROZEN-v20.1`

Runtime source commit:
`897f249a11875b0d8eeae7df070bc9df3321d4e0`

Frozen dependency verification:
**20/20 PASS**

The frozen dependency set now includes:
`src/spineforge_v20_paid_once.py`

Paid-run harness behavior:
- writes a start envelope before inference;
- executes exactly one SpineForge run;
- never authorizes Writer;
- never runs automatic retry or repair;
- persists typed result + usage evidence on normal completion;
- persists an explicit `unhandled_runtime_failure` result if the process-level run call raises;
- uploads evidence with `if-no-files-found: error`.

The paid job is guarded by the explicit marker:
`[PAID-V20-AGE12-ISLAND-ATTEMPT1]`

A normal push without that marker skips the paid job.

Latest zero-cost CI:
- run `36907534921`
- qualify: **SUCCESS**
- paid job: **SKIPPED**
- freeze: **20/20 PASS**
- tests: **15/15 PASS**

Current state remains:
**READY_FOR_EXPLICIT_PAID_SPINE_AUTHORIZATION**

No paid inference has been made for v20/v20.1.


## v20.1 first paid qualification — age12 island

Explicit paid authorization produced one frozen v20.1 qualification attempt.

GitHub Actions run:
`36908095596`

Trigger commit:
`f50f5743666aaffff9307b0108d85f299341521a`

Case:
`spineforge.v20.age12.adventure-exploration.island.01`

Result:
`repair_required`

Spine title:
`The Island That Wasn't on Any Map`

Context fingerprint:
`090ae8343daa2b24e95923ee9e9dc11356664baed9a79c4ff95fd0207b834233`

Spine hash:
`4ae3ef5af8316234999a7fc432feeab5e4169e4b440de5bab08cb86f15f74d9b`

Deterministic validation:
- authority_valid: true
- reveal_safe: true
- obligations_valid: true
- discovery_turns: 8
- real_choice_count: 2

Luna Product Gate:
- decision: `REPAIR`
- findings: 1
- dimension: `WRITER_EXECUTABILITY`
- severity: `MAJOR`
- repairability: `LOCAL`
- target: `narrative_spine.beats[2].character_action; narrative_spine.beats[6].character_action; narrative_spine.climax`

Finding: the route line is left tied to a shore tree as a return anchor in beat 3, but beat 7 later uses that same line deep in the island interior to swing Nisa across a broken root bridge and the climax depends on cutting it. No beat retrieves/carries that line inland, creating a physical continuity contradiction.

Luna otherwise accepted the adventure-exploration shape: Arda acts decisively, the island provides concrete wonder, the Arda/Nisa relationship conflict matters, discovery changes the meaning of the expedition, and the turn-back decision produces a local payoff.

No automatic repair executed. Writer remains blocked.

### Usage

Sonnet 5.5 Architect:
- input: 12,736
- output: 3,958
- total: 16,694 tokens
- cost: $0.065052
- latency: 34.700 s

GPT-5.6 Luna Product Gate:
- input: 9,356
- output: 770
- reasoning: 516
- total: 10,126 tokens
- cost: $0.00326285
- latency: 13.011 s

Pipeline total:
- API calls: 2
- input: 22,092
- output: 4,728
- reasoning: 516
- total: 26,820 tokens
- cost: $0.06831485
- model latency: 47.711 s
- cost reconciliation: PASS
- token reconciliation: PASS

Current boundary:
**STOP_FOR_HUMAN_REVIEW / LOCAL_REPAIR_NOT_AUTHORIZED**

This attempt demonstrates a materially more adventure-first Spine than the rejected Echo Span premise. The only model-gate blocker is a local prop-continuity defect. Human product judgment is still required before any repair authorization.


## v20.2 bounded LOCAL repair preflight — zero-cost

The first paid v20.1 island Spine returned one Luna LOCAL finding:
route-line physical continuity.

A bounded repair harness has now been frozen without making a repair inference.

Frozen revision:
`SPINEFORGE-STORY-FIRST-FROZEN-v20.2`

Runtime source commit:
`1f2eec63413ab15f00dcf57768e6583d8aee824b`

Source repair binding:
- source run: `36908095596`
- source Spine hash: `4ae3ef5af8316234999a7fc432feeab5e4169e4b440de5bab08cb86f15f74d9b`
- source gate: `REPAIR`
- finding count: 1
- repairability: `LOCAL`

Important gate-target normalization:
Luna correctly identified the route-line contradiction, but its `target_path` named `beats[2].character_action` while the contradictory shore-anchor statement actually appears in `beats[2].external_change`.
The repair harness therefore binds to the exact Luna evidence plus typed source inspection instead of blindly trusting the path string.

Repair strategy:
- preserve the premise, discovery chain, decision, selected turn-back path, climax purpose, payoff, hooks, and Saga boundaries;
- prefer one minimal continuity edit: the route line may steady the glider at shore, but must be explicitly unfastened, coiled, and carried inland before the later bridge rescue;
- reject any model output changing fields outside the frozen allowed-path set;
- run deterministic authority/reveal/obligation validation after repair;
- require a Luna re-gate;
- keep Writer blocked regardless of repair result until human approval.

Frozen repair files include:
- `evidence/spineforge-v20-repair/36908095596-source.json`
- `evidence/spineforge-v20-repair/36908095596-repair-spec.json`
- `prompts/spineforge_v20_local_repair.md`
- `src/spineforge_v20_local_repair.py`
- `src/spineforge_v20_paid_repair_once.py`

The repair runtime preserves repaired Spine + Sonnet usage if Luna re-gate transport fails.

Paid repair guard:
`[PAID-V20-AGE12-ISLAND-REPAIR1]`

Latest zero-cost CI:
- run `36909872966`
- qualify: **SUCCESS**
- freeze: **25/25 PASS**
- tests: **24/24 PASS**
- original paid Spine job: **SKIPPED**
- paid LOCAL repair job: **SKIPPED**

Current tracked paid totals before repair:
- API calls: 2
- confirmed cost: $0.06831485
- paid LOCAL repair authorization: false
- Writer authorization: false

Current boundary:
**READY_FOR_EXPLICIT_PAID_LOCAL_REPAIR_AUTHORIZATION**

No paid repair or re-gate has executed.
