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
