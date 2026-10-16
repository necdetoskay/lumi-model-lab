# SERA — Scene Event Registry & Assurance

Independent LUMI Model Lab scene-state experiment on `experiment/sera-scene-state-v0-1-20261015`. **Not a promoted story pipeline.**

> **Mandatory owner requirement (2026-10-16): ZERO manual intervention throughout story generation.** Any old reference below to mandatory human review, gold labels, approval clicks, manual story corrections, or manual retries is **historical laboratory context**, not a production/runtime dependency. Runtime must automatically validate → targeted repair → independent revalidation → re-extract/replan/rewrite/recheck, ending in a machine-verifiable safe result or `FAILED_SAFE_FINAL` without unauthorized world writes. No output token ceilings. See [SERA v0.16 owner policy](./SERA_V016_AUTONOMOUS_REPAIR_ARCHITECTURE.md) and [AGENTS.md](./AGENTS.md).

## Frozen source

Original Sonnet 5.5 pre-Haiku Spine: `evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json`.
Pinned Git blob SHA: `fe1dda0047000438bbfaac69022e835bf7e0a1f8`.
It is read-only. The compiler creates nine derived scene contracts without rewriting source data.

## Modules

- [ARCHITECTURE.md](./ARCHITECTURE.md) — design, authority rules, semantic caveats and milestones.
- `spine_contracts.py` — immutable-source verification and derived scene-contract compilation.
- `state_engine.py` — Python event reducer and complete state snapshots. Records non-mutating object interactions as events.
- `coverage.py` — strict dual-extraction schema, lexical known-entity scanner, event/mention reconciliation; **never** authorizes commit.
- `extractor_adapter.py` — independent/blind prompt, exact-quote span binding and opt-in one-call OpenRouter client.
- `fixtures/gold_mara_m2_v0.1.json` — six **hand-authored synthetic** adversarial scenes with expected event/entity labels (not model results).
- `gold_calibration.py` — offline precision/recall metrics against manual synthetic labels.
- `jev_verifier.py` — per-claim JEV choice-question builder and advisory-only verdict routing; a billable live call requires an explicit opt-in.
- `tests/` — deterministic unit tests; all external responses mocked.

## Offline checks (no provider cost)

From repository root:

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.spine_contracts evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json
python -m experiments.sera.gold_calibration
```

## Independent extractor (opt-in only)

Create a local JSON input containing **exactly** these fields:

```json
{
  "scene_key": "hook_empty_platform",
  "entry_revision": 0,
  "prose": "Mara examined the quiet platform.",
  "registry": {
    "mara": ["Mara"],
    "platform_clock": ["platform clock"]
  }
}
```

Dry-run displays the blind system prompt and serialized scene payload **without calling an API**:

```bash
python -m experiments.sera.extractor_adapter path/to/input.json
```

A live call is explicitly billable and is **not** part of CI:

```bash
OPENROUTER_API_KEY=... python -m experiments.sera.extractor_adapter path/to/input.json \
  --live --model EXACT_MODEL_ID --output path/to/new-evidence.json
```

The adapter makes exactly one request, with no provider fallback. Unknown/incomplete outputs fail closed. It records requested model, observed model, usage, provider cost if returned, raw extraction, hashes and typed extraction report. A quoted phrase is resolved to codepoint offsets in Python; the model is not trusted to count indices.

The independent model must never see the writer report in its input. The output alone does not establish complete extraction: both models can miss the same object. A structurally reconciled report is `RECONCILED_PENDING_SEMANTIC`, **not PASS**.

## Atomic JEV prototype (M3 groundwork)

`jev_verifier.build_atomic_questions(...)` takes the M2 coverage, source
reports, scene prose and registry, re-checks the coverage binding, and builds
one `choice` decision per entity/presence claim and typed event. The JEV
request sees an anonymized union of candidate claims, not source-model labels.
The supported decisions are `SUPPORTED`, `CONTRADICTED` and
`INSUFFICIENT_EVIDENCE`.

`adjudicate(...)` routes contradictions to local repair, ambiguous claims to
escalation, and remaining extractor mismatches to reconciliation. Even full
semantic agreement leaves `commit_authorized=false`. Empty claim sets are
escalated; agreement on nothing is not a success.

`call_live_jev(..., allow_billable=True)` uses the existing repository-pinned
`typesafe/jev-1.13` Decisions API adapter. M3 tests only simulate answers;
**no real JEV model qualification or runtime cost is claimed.**

Full production acceptance, gold holdout calibration, state commit and the
nine-scene live Mara demonstration are future separate milestones.

## Current evidence and status

M0/M1 completed. M2 offline harness and preliminary M3 JEV question/decision contract implemented; **no live independent-model benchmark or JEV qualification yet**. The gold cases are synthetic and must not be counted as evidence of real extraction accuracy. No Project LUMI database writes, provider calls, or production V4/V4.1/V4.2 modifications occur in offline tests.

## 2026-10-16 live Mara S1 diagnostic

The first real one-scene model experiment ran, and subsequent independent Gemini + JEV continuation completed against the **identical 243-word scene**, not a regenerated story.

- [Full measured evidence ledger](./evidence/MARA_S1_LIVE_DIAGNOSTIC_20261016.md).
- [Live source run](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38808450095) and [semantic continuation](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38809210994).
- M2 remained HOLD: 10 incompatible event signatures, 10 missing grounded event times, 1 uncertain modality.
- JEV handled 18 claims: 17 SUPPORTED, 1 INSUFFICIENT_EVIDENCE; ESCALATE, **no state commit**.
- Manual text inspection found physical object candidates 'bench' and 'pencil' missing in both extractor entity lists. Optional versioned noun-candidate scanning plus fail-closed JEV claims was added and covered by regression tests.
- Unresolved schema/time/epistemic hardening is tracked in [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304); persistent object history and weather is separate [#303](https://github.com/necdetoskay/lumi-model-lab/issues/303).

**Important:** A successful GitHub workflow run here means the diagnostic executed, not that the narrative or extracted state passed acceptance. A lexicon is supplementary, not proof of exhaustive entity identification.


## Object State v0.2 — Active Experimental Prototype (Issue #303)

Per the object-history backlog, SERA now includes a second, isolated, strictly typed
state/event system. **Existing v0.1 scene/extractor/JEV code and the immutable
Sonnet source remain untouched.** This is NOT a production database migration.

- [Full v0.2 architecture](./WORLD_STATE_V02_ARCHITECTURE.md).
- `world_state_v02.py`: entity identity, object color/material/dimensions,
  condition/age, ownership vs holding/wearing, character traits/knowledge,
  and environmental weather/temperature/wind/wet ground. Verified changes
  require application-owned event-fingerprint grants and explicit causes.
- `world_store_v02.py`: standard-library SQLite atomic/idempotent events,
  append-only histories, revisional/historical entity lookups, snapshot replay
  and hash-chain consistency checks.
- `tests/test_world_state_v02.py`: demonstrates **10 scenes without silent
  object/color/clothing/weather changes**, authorized repairs, ownership and
  dimension constraints, temperature jumps, SQLite historical retrieval,
  rollback, idempotency and closed-form append-only records.

Run from the repository root:

```bash
python -m unittest discover -s experiments/sera/tests -v
```

M3's actual Mara first-scene extraction is still held by typed-event/time
problems ([#304](https://github.com/necdetoskay/lumi-model-lab/issues/304)).
**No provider model or JEV response is allowed to commit the new v0.2 state
without a separately qualified evidence-to-authority adapter.**

## EventGraph v0.3 — Structural history and causal dependency graph

[Experimental architecture](./EVENTGRAPH_V03_ARCHITECTURE.md) ·
[Issue #305](https://github.com/necdetoskay/lumi-model-lab/issues/305) ·
[Real Mara S1 candidate evidence](./fixtures/mara_s1_real_eventgraph_candidates_v03.json)

- `event_graph_v03.py` now implements independent narrative event IDs,
  participant/object role relations, causal prior-event links, typed
  preconditions, prose-SHA+exact-span binding and advisory epistemic classes.
- **Only the Python world reducer** calculates the before/after entity and
  region diffs. Language-model-proposed before/after snapshots are rejected.
- `EventGraphStore` writes event relationships/effects and the v0.2 world
  transition in **the same SQLite transaction**. If an affected coat/notebook
  is missing from a movement event's related objects, both ledgers roll back.
- Append-only graph lifecycle supports accepted
  PROPOSED→VERIFIED→COMMITTED and independent REJECTED proposal records.
  A graph query can retrieve object/character history, scene timeline,
  event descendants and reducer-derived effects. Replay requires a one-to-one
  mapping of all world events to narrative events.
- The original **243-word live Mara S1 scene** is frozen as an isolated,
  read-only candidate set of nine event proposals. **All remain HOLD** and
  no world/production canon is modified: JEV had previously returned ESCALATE
  and the event-time/extractor schema is still incomplete.
- Test suite is fully offline; no model requests and no LUMI production DB
  writes. The status string `APPLICATION` and SHA equality bindings are
  NOT authentication; a trusted server-side review/capability adapter remains
  necessary before deployment.

## M3.4 typed model event / JEV / EventGraph bridge

- [Architecture and validation boundaries](./M3_EVENTGRAPH_BRIDGE_V04.md)
- `typed_event_bridge_v04.py`: strict per-event required-key/ID validation, canonical v0.2 reducer mapping, source SHA/offsets and unknown-time preservation. Empty Gemini-style arguments are HOLD, never auto-completed.
- `m3_event_graph_bridge_v04.py`: compares independently normalized proposals, revalidates JEV claim identity, produces **non-committable** EventGraph drafts and optionally shadow-replays physical invariants with zero DB writes.
- `mara_s1_v04_audit.py`: read-only recheck of the exact archived 243-word first Mara scene; **9/9 event candidates remain HOLD**, bench and pencil remain unregistered, prior live JEV ESCALATE not overturned.
- Tests are offline. No real JEV provider authentication, independent gold qualification, accepted real-world state, or production DB integration is claimed. Fingerprint equality and `authority=APPLICATION` text fields are not a security boundary.

To inspect the real scene's unresolved findings without model calls:

```bash
python -m experiments.sera.mara_s1_v04_audit
```

## M3.5 — Typed extractor contract and temporal domains (2026-10-16)

[Architecture, tests and two measured live outcomes](./M3_5_TYPED_EXTRACTION_TEMPORAL_V05.md).
The provider-facing `typed_extractor_contract_v05.py` constrains operation-specific
required keys. `temporal_domains_v05.py` solves app-reviewed causal order,
scene time windows and minimum travel without claiming invented timestamps.
The read-only `mara_s1_typed_live_v05.py` targets the **unchanged 243-word
live Mara S1 scene**, never regenerates it and never commits state.

The first real provider call hit completion length (USD 0.0183705 as reported);
a separately pinned reasoning-off retry returned HTTP 400 (cost not reported).
Both remain HOLD and the unsupported reasoning override was removed. Evidence
is preserved in the two one-use Actions runs; no JEV requalification or
production state update is implied. The artifact was examined via an offline
forensic workflow (no extra model call). Issue [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304)
remains open for provider-schema compatibility, open-world recall calibration,
trusted semantic adjudication and a complete S1 exit-state acceptance.

## SERA v0.6 — Sentence Ledger + T2 memory + Scene Contract

[Architecture and exact boundaries](./SERA_V06_SCENE_ASSURANCE_ARCHITECTURE.md) ·
[Implementation epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306)

The three outside architecture reviews motivated a **coverage-first** stage.
The new `scene_assurance_v06.audit_scene` composes an every-sentence source
ledger, model-independent T2 noun/action candidate scanner, optional
pre-Writing scene intent alignment, and original M2 reconcile reports.
A missing planned action never becomes a committed world event automatically;
writer-added actions are flagged for review.

`observation_archive_v06.ObservationArchive` can persist T2 physical object
sightings and their exact source quotes in a **separate experimental SQLite
audit archive** while WorldStore remains unchanged. Registered aspect
proposals (`openable.case_open`, `writable.entries`) and attributed
character knowledge propositions are currently **advisory, not reducer
events**. The bounded repair router suggests selective next actions but
makes no LLM calls.

```bash
python -m experiments.sera.mara_s1_v06_audit
python -m unittest discover -s experiments/sera/tests -v
```

The 243-word real Mara first scene has **28 structurally accounted-for sentence
spans**, T2 bench and pencil candidates, and action cues for closing the watch
case and writing in Mara's notebook. **These are not human gold annotations**
and the actual scene's nine events remain HOLD. No provider calls, output token
ceilings, or production DB writes were added. The user prohibition on
application-set LLM output token limits is preserved and CI-enforced.

Real event acceptance, independent semantic coverage, typed aspect reducer
mutations and first S1 exit-state qualification are still pending.

## SERA v0.7 — Real-scene reference review and extraction binding

[v0.7 source/provenance architecture](./SERA_V07_MARA_GOLD_REVIEW.md) ·
[tracked integration epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

`sentence_review_packet_v07.py` constructs the **UNREVIEWED** reference
worksheet for all 28 sentences of the exact frozen Mara S1 prose, with
original nine *analyst-proposed* events and all scanned entity/action cues.
The packet is CI-archived for external human annotation. Model/code-derived
suggestions are never silently labeled human gold.

`independent_ledger_bridge_v07.py` attaches an already completed blind M2
extractor report to the sentence ledger, preserving multiple exact sentence
evidence spans for one reported event and highlighting omitted T2 candidates.
This is an advisory `HOLD` result, not a model invocation or state commit.

`offline_benchmark_v07.py` computes sentence classification and entity
mention precision/recall on explicitly reviewed or synthetic-only fixture
labels, but refuses to report true Mara event/entity accuracy while the
reference remains unadjudicated. It never grants canonical commit authority.

```bash
python -m experiments.sera.sentence_review_packet_v07 \\
  --output /tmp/mara-s1-28-sentence-unreviewed.json
python -m unittest discover -s experiments/sera/tests -v
```

No output token ceilings were added. Live independent extraction, authenticated
human adjudication, state reducer aspect mutations and an accepted real S1
exit state remain separate qualification gates.

## SERA v0.8 — Blind human review and adjudication (no gold yet)

[Architecture and review instructions](./SERA_V08_BLIND_ADJUDICATION.md) ·
[Integration epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

Run `review_forms_cli_v08.py export --output-dir <path>` to produce two
**blinded, completely UNREVIEWED** source-bound Mara S1 annotation forms,
without revealing the original nine analyst event suggestions.

The `review_adjudication_v08.py` validator accounts for every source
sentence, every known lexical entity hint, exact event quote spans,
multi-sentence event identities, epistemic effects and review notes. After
external reviewers edit the two forms, run `review_forms_cli_v08.py compare`
to list disagreements, incomplete rows, and shared high-risk omissions.
Matching answers are advisory and cannot self-elevate to gold, and the
reviewer alias is NOT an authenticated user. All status outputs remain
`NOT_GOLD_HUMAN_ADJUDICATION_REQUIRED` and
`canonical_commit_authorized=false`.

The SERA CI workflow archives both blind JSON forms and instructions as
downloadable GitHub Actions artifacts. No models, human decisions or state
writes are simulated, and no application-defined model output token limit
is set.

## SERA v0.9 — browser-based double review for frozen Mara S1

[Workflow architecture and review guide](./SERA_V09_REVIEW_WORKSPACE.md) ·
[epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

`reviewer_ui_v09.py` exports **two standalone offline HTML pages** with
all 28 exact source-bound Mara sentences and independent lexical cues. Each
human reviewer can classify entities and events, add source-evidenced new
object candidates omitted by the scanner, navigate between sentences,
and export or resume a JSON review file without any remote network calls.

```bash
python -m experiments.sera.reviewer_ui_v09 --output-dir /tmp/mara-review
python -m experiments.sera.review_forms_cli_v08 validate \
  --review reviewer_A_unverified-NOT_GOLD.json --require-complete
```

The GitHub Actions SERA workflow archives both HTML pages, blank JSON forms
and instructions for human review; generated JavaScript passes a syntax
gate. Event evidence uses Unicode code-point offsets corresponding to
Python string indexing. New object candidates are **only annotation hints**,
not World State entity introductions.

Two actual independent human reviews and authenticated final adjudication
are still required before Mara's precision/recall and canon exit state can
be accepted. No reviewer identity, GOLD status, model calls or output token
limits are inferred/added by these forms.

## SERA v0.9 Chromium E2E qualification

[Verified real-browser test and trust boundaries](./SERA_V09_CHROMIUM_E2E_QUALIFICATION.md).
The branch CI now has a separate Playwright **Chromium browser E2E** job,
not merely JavaScript syntax tests. The test navigates the exact Mara
28-sentence offline review UI; blocks a fabricated quote; creates a genuine
source-backed *synthetic QA* event and lexicon-missed entity candidate;
downloads, Python-validates, imports and round-trips JSON; checks A/B reviewer
isolation and mobile layout. It must remain noncanonical and cannot impersonate
a real human adjudicator. Run locally:

```bash
python -m pip install playwright==1.56.0
python -m playwright install chromium
python -m experiments.sera.browser_e2e_v09
```

CI [38858676688](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38858676688)
passed **257 offline tests plus the separate actual Chromium E2E job**.
No actual Mara gold or first scene exit state has been authorized.

## SERA v0.10 — Autonomous source-bound extraction and targeted probes

[Full architecture, gates and one-shot test](./SERA_V010_AUTOMATIC_EXTRACTION.md).
The v0.10 `sentence_sweep_v010.py` replaces whole-scene giant JSON
output **for extraction trials** with seven independent four-sentence
Mara source windows, requiring one model disposition per numbered sentence,
all supported candidate events and mentions, and exact prose evidence.
The deterministic merger flags missing entities and unaccounted state-change
verbs for a separate blind targeted probe, preserving HOLD until
independent semantic verification and approval.

`mara_s1_sweep_pilot_v010.py` can run a *single* source-pinned,
preflight-protected paid diagnostic for the window containing Vane's
watch-case closure. It makes no automatic retries, generated prose,
WorldState commits or JEV calls. The user-prohibited model output token
limit is never set. A passed batch still leaves other sentences HOLD.

```bash
python -m experiments.sera.mara_s1_sweep_pilot_v010  # dry run; no provider
python -m unittest discover -s experiments/sera/tests -v
```

See the separate pinned one-shot GitHub Actions workflow for isolated
evidence and provider billing reports. Historical failed/truncated model
attempts do not establish scene truth, nor do 276 offline passing tests.

## SERA v0.10 actual provider result / six-batch resume

The first paid blind model pilot completed s009–s012 (4/28 sentences)
in [Actions 38860727745](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38860727745):
`google/gemini-3.7-flash`, **USD 0.005589** reported cost, `finish_reason=stop`,
**no model-output token limit set**. The provider detected three event
candidates, including Vane **closing the watch case**, but returned
grammatical mention-role labels outside the strict enum.

The existing paid raw response was successfully reprocessed without
another model call in [offline forensics 38861188156](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38861188156),
recovering **4 source rows, 7 candidate mentions and 3 candidate events**
while preserving the **original** request fingerprint. Whitelisted grammar
labels map only to unasserted `MENTIONED`; the watch-case and body-part
candidates are not automatically registered as world objects.

`mara_s1_remaining_sweep_v010.py` reuses that original paid batch and
handles only the **six missing source batches**, with separate immutable
provider evidence, per-batch actual reported cost, a measured dollar
spend stop and hard stop on provider or schema errors. A successful full
28-sentence run is still semantic HOLD, **not** a canonical S1 exit state.
See [v0.10 architecture](./SERA_V010_AUTOMATIC_EXTRACTION.md).

## SERA v0.11 — Semantic risk audit and independent targeted second opinion

[Architecture, actual Mara findings and provenance](./SERA_V011_SEMANTIC_REPAIR.md).

All 28 Mara S1 sentences have now been source-bound in seven v0.10 model
batches, yielding **25 Gemini event candidates** (NOT approved state).
The independent, offline `semantic_risks_v011.py` review of original
provider evidence identified three important questions: whether Mara's
turn toward the clock was actual relocation, whether the notebook
`added` sentence was wrongly classified as speech, and whether a pocket
watch open before the case closes implies a qualified `case_open` state.
It also identified two lexical probe false-positives, preserving the raw
original extraction.

`mara_s1_haiku_probes_v011.py` sends source-only questions to a different
model family, **without revealing Gemini judgments**. It is opt-in, has
a single-run provider/cost guard, does not set model output token ceilings,
and saves every raw/provider-cost result with no state commits. Passing
unit tests or source-bound model agreement does not create gold labels or
authorize the first Mara S1 canonical exit state.

Offline tests: [CI 38862839733](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38862839733),
**293/293 PASS** plus actual Chromium E2E.

## SERA v0.12 Haiku correction proposals and typed shadow aspects

[Complete implementation, real-provider evidence and remaining blockers](./SERA_V012_HAIKU_REPAIRS_AND_SHADOW_FACETS.md).

All three independent Haiku targeted opinions for Mara's completed 28-sentence
Gemini sweep are now source-bound. Whitelist-only code-fence and Unicode
quotation recovery reused the two earlier **paid** answers, instead of
repeating provider calls. Haiku supported reclassifying `MOVE` to
`OBSERVE`, `COMMUNICATE` to `WRITE`, and modeling a watch open
baseline followed by a closure. Reported new Haiku cost was **USD 0.004235**
total, with no application-set output token ceilings.

The `mara_s1_candidate_corrections_v012.py` module generated **two
source-pinned, NONCANONICAL event-correction proposals** and **three typed
shadow aspect proposals** from actual archived model evidence. The detached
`shadow_aspect_projection_v012.py` simulated `UNKNOWN → OPEN → CLOSED`
for Vane's watch case and one exact-source notebook append while retaining
`preexisting_content=UNKNOWN`. It does not modify v0.2 World State,
commit EventGraph, manufacture action time or approve semantic truth.

Real provider evidence qualification:
[corrections run 38866189103](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38866189103),
[shadow projection run 38866515258](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38866515258).
**320/320 offline tests PASS** and shadow World State hash unchanged.
Mara S1 remains **HOLD**, awaiting proper canonical facet contracts,
wider event/identity qualification and authority gating.

## SERA v0.13 — typed reducer contracts and all-source Mara gate inventory

[Complete v0.13 architecture, safety boundaries and actual results](./SERA_V013_VERSIONED_WORLD_FACETS.md).

A NEW experimental versioned WorldState snapshot
(`world_state_v013.py`) adds `OBSERVE_OPENABLE`, `SET_OPENABLE`,
and `APPEND_DOCUMENT_ENTRY` with typed CAS, exact source sentences,
strict monotonic prose offsets, simulated-only separate approval
interface, immutable snapshot updates, deterministic hashed event history
and detached revision restore. It does **not** alter the v0.2 WorldStore
schema, active worlds, SQL database or original Spine. No real canonical
authority is provided.

[Actual Mara typed reducer run 38867777726](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38867777726):
**337/337 tests PASS** and three source-verified offline facet events
simulate the watch case `UNKNOWN → OPEN → CLOSED` plus the notebook
verbatim append. Earlier notebook text stays `UNKNOWN`, no action
times are guessed, and replay reconstructs the original snapshot.

[Actual Mara event census run 38868197633](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38868197633):
all **25 Gemini event candidates** checked with per-event blockers,
two proposed reclassifications retained, **0 authorized for commit**.

[Actual Mara mention census run 38868633198](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38868633198):
all seven original paid batches yield **60 source-bound model mentions,
22 unique entity refs, 16 provisional/unregistered refs**.
`new:bench` and `new:pencil` are now visible even when no physical
state event involves them; train arrival topics and anatomical thumb
remain nonphysical/not independent inventory items. **0 automatic
new entity creations**.

Latest qualification: **345/345 offline Python tests PASS**.
First real Mara S1 canonical exit state is still **HOLD**. Next steps
are provisional identity/part-of resolution, independent semantic
event qualification, real trusted authority and transactional
production migration tests.

## SERA v0.14 — 16 provisional reference identity proposals

[Architecture and real source findings](./SERA_V014_ENTITY_IDENTITY_GATE.md).

A reusable source-bound `identity_resolution_v014.py` contract
now enforces **complete** provisional reference coverage and explicit
review-only interpretation categories. The Mara-specific
`mara_s1_identity_rules_v014.py` rulebook is a set of **hypotheses**,
not human gold and not a hardcoded global ontology. Its exact source
anchors are checked against original paid model mentions and source
sentences, and the join with 25-event source-gate results prevents
silent cross-sentence object aliasing.

[Actual v0.14 proof 38870235664](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38870235664):
**351/351 Python tests PASS**. From **60 source mentions** and
**25 original event proposals**, every one of **16 unregistered refs**
has a noncanonical review category; **9 events** depend on those
unregistered identities. Only `new:bench` and `new:pencil`
are independent physical-item candidates. `new:watch_hands` and
`new:watch_case` are potential watch parts, `new:vane_thumb`
an anatomical part, and `new:mark`/`new:strike_mark` explicit
absences rather than newly created objects. Reported trains stay
nonphysical topics. **0 entity creations, 0 relationship links,
0 canonical commits and 0 new model charges.**

The next general-purpose step is **blind model-assisted identity
proposals** (finite typed schema + abstain/repair), compared against
this source-specific diagnostic without granting it truth authority;
afterward all event and identity proposals require independent
qualified validation before any actual `WorldStore` transaction.

## SERA v0.15 — blind, reusable, model-assisted entity identities

[New v0.15 contract and operational safeguards](./SERA_V015_BLIND_IDENTITY_REVIEW.md).

The generic `blind_identity_v015.py` reviewer independently asks a
model to classify EVERY unregistered source-mentioned entity into a
strict finite taxonomy or `ABSTAIN`. It supplies original source
sentences, up to two adjacent context sentences (for pronouns), and
the original registered World entity/region IDs. It **does not
show** the older hand-authored Mara identity hypotheses or prior
Gemini event classifications.

Returned source spans, sentence IDs, complete ref coverage,
entity-parent kind, enum values, alias cycles and abstention
are checked deterministically. The live adapter
`mara_s1_blind_identity_pilot_v015.py` is **one request only** and
stores raw evidence before binding or error reporting.
The self-hosted CI one-shot grant workflow is
`.github/workflows/sera-mara-v015-blind-identity-once.yml`.

Every model result remains noncanonical, with zero world writes,
entity creations, physical-presence confirmations or relationship
attachments. Model output token ceilings remain forbidden.

## v0.15 actual blind Haiku result, self-healing forensic replay

The independent, source-only Haiku identity pilot successfully made
**one paid call** with `finish_reason=stop`, **USD 0.015781** actual
provider-reported cost, **16/16 model rows** and no output-token
ceiling. The provider incorrectly escaped three quoted evidence
fields inside fenced JSON. The strict binder **HOLD** protected world
state; no second provider call was needed.

The offline `paid_blind_identity_forensics_v015.py` and
`mara_s1_paid_identity_replay_v015.py` repair only safely verifiable
quoted JSON field syntax and unique typographic exact-source matches.
Of the **16 original model opinions**, **12** are now bound as
NONCANONICAL proposals, **4** are isolated in source/relationship
contract quarantine (bench, pencil, station alias, strike record).
[Real evidence replay 38873775587](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38873775587).

Only AFTER the independent model response was archived, the
`identity_disagreement_v015.py` report compared it with the older,
hand-authored Mara hypotheses: **15/16 category label agreement**,
**9/16 full class/relation/target agreement**. This is an
inter-hypothesis difference metric, NOT accuracy or adjudicated gold.
[Real comparison 38874297940](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38874297940)
and [full design/evidence](./SERA_V015_BLIND_IDENTITY_REVIEW.md).

**375/375 Python tests PASS**. No automatic world identities,
part links, train arrivals or canonical events were authorized.
The next boundary is independently qualifying document vs object
vs region parent aspects and relation ontology.

## SERA v0.16 — Autonomous repair is part of the generation stage

[Canonical rule and test evidence](./SERA_V016_AUTONOMOUS_REPAIR_ARCHITECTURE.md).

**No manual repairs or human prompt editing are permitted in normal story
generation.** The generation stage must diagnose, safely repair,
independently revalidate, and either return source-bound candidate events
or automatic abstentions/HOLD. Human intervention is not a prerequisite
for any individual story to finish the repair stage.

`identity_auto_repair_v016.py` processes each generated identity separately:
strict JSON recovery, unique quote normalization, schema and source
binding, conservative repair of unsupported relation metadata, and
targeted low-cost model re-review only of unresolved identities,
followed by full deterministic revalidation. A failed repair does
not discard other valid rows; automatically quarantined rows retain
their original evidence and reason. `identity_stage_v016.py`
invokes primary model and automatic targeted repair **within one stage
call**, with a durable audit trail and bounded provider-call count.
No canonical database writes or output-token ceilings are configured.

[Real archived paid response qualification](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38875977497):
16/16 candidate identities accounted for, **15 source-bound**, **3**
conservative relationship fixes in code, **1 automatically abstained**
(`new:strike_record`) during the zero-model-call forensic replay.
The model-assisted continuation is verified by independent synthetic
provider error-injection tests, not claimed as real paid response.
This SERA experimental stage is **not yet wired into LUMI production**
or given canonical WorldStore/WorldEvent commit rights.


## v0.17–v0.19 — Unattended candidate recovery and semantic continuity (2026-10-16)

- [v0.17 identity recovery](./SERA_V017_UNATTENDED_IDENTITY_RECOVERY.md): complete v0.16 identity stage runs inside an automatic scene supervisor. Paid provider replies, including targeted corrections, are archived and reusable after a crash; only confirmed, already paid evidence is safely reprocessed. Receipted failures may trigger automatic full-scene re-extraction. Unknown in-flight provider calls MUST NOT be blindly resent.
- [v0.18 semantic recovery](./semantic_recovery_v018.py): source-based semantic risk auditor drives independent model probes without a reviewer queue. Every probe has exact source context, a durable request/response/cost receipt, conservative strict JSON-fence handling and an automatic alternative-model fallback for *already receipted* invalid replies. All answers are independently source-bound, never canon-authorized; saved advisory digest guards against accidental downstream modification.
- [v0.19 event candidate projection](./event_candidate_projection_v019.py): independently rebind v0.18 advisories, narrowly propose corrections (attention vs relocation, notebook write vs dialogue, reported claim vs physical event), rerun the entire semantic risk audit and optionally check application-controlled temporal dependency/travel windows. No invented time, accepted state or entity. Unresolved aspect/chronology problems automatically produce a typed re-extraction/replan signal rather than asking a person to adjudicate.
- Regression coverage: \`tests/test_scene_recovery_v017.py\`, \`tests/test_semantic_recovery_v018.py\`, \`tests/test_event_candidate_projection_v019.py\`. All use synthetic provider injection without billable calls.

**Not yet a full autonomous story generator:** The writer/replanner has not consumed these noncanonical replan signals. Semantic source binding or inter-model agreement is not objective gold. A provider call with no recorded reply still needs external idempotency/reconciliation; final canonical EventGraph/WorldState commit authority is unimplemented. Mara S1 remains HOLD and the original frozen Sonnet Spine is unchanged. The next stage must implement and qualify unattended affected-scene rewriting with durable paid receipts, full re-extraction, causal/time/scene-state checks, transactional release and automatic terminal failure without any human gate.


## v0.19 — Real frozen Mara archived-provider replay (NO new LLM calls)

The fully automated, self-hosted workflow
[38882410488](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38882410488)
retrieved the earlier **actual paid** Gemini 28-sentence/25-event archive
(run `38861828582`) and three independent, archived Haiku 4.5 source
advisories (run `38865604842`). It ran the original-source validation
and generic v0.19 projection with **zero additional LLM/provider requests**,
zero extra model cost, zero human-edit steps, zero production DB writes and
no application-configured model output-token ceiling.

Verified automatic **noncanonical** event reclassifications:
- `batch_004:s014:e1`: `MOVE / CHARACTER_KNOWLEDGE` →
  `OBSERVE / CHARACTER_KNOWLEDGE` (attention toward a record is not travel).
- `batch_006:s021:e1`: `COMMUNICATE / NONE` →
  `WRITE / DOCUMENT` (notebook addition is not spoken dialogue).

The remaining typed transition task
`OPENABLE_BEFORE_CLOSE_NEEDS_TYPED_ASPECT:s004` correctly remains
unresolved: an open watch baseline and subsequent physical case closure
require a controlled, authorized typed aspect/state transition. A supported
*experimental* v0.13 simulated reducer exists, but the v0.19 pipeline must
not unilaterally promote model opinions or invent an aspect binding.
The result is `AUTO_REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL`,
**not** Mara S1 acceptance.

Reproducible proof: [self-hosted workflow source](../../.github/workflows/sera-v019-real-mara-archived-replay.yml),
[actual archive replay module](./mara_s1_archived_semantic_replay_v019.py), and
its structured artifact attached to the successful run. This is the next
integration target for generic type-safe aspect proposals and automatic
story-rewriter/replanner consumption, without per-story hardcoded rules or
required human approvals.


## v0.20 — Generic typed-object facets + unattended rewrite/recheck seam

[Full architecture and boundaries](./SERA_V020_AUTONOMOUS_SCENE_LOOP.md).

- `typed_aspect_recovery_v020.py` converts registered, source-supported
  openable/document aspect candidates into immutable, typed, **noncanonical**
  v0.13 CAS/replay simulations. Closing a watch case without a prior open
  baseline, writing imaginary notebook text, object/actor co-location mistakes,
  unknown object identities and fabricated action clocks do **not** mutate
  world state. Upstream v0.19 semantic HOLD still prevents scene readiness.
  The v0.13 role registry now accepts openable-only or document-only
  scenes without fabricating an object; an entirely empty registry blocks.
- `unattended_scene_rewrite_v020.py` is the new automatic, restart-aware
  scene rewrite/check **integration seam**: a deterministic offline scene
  validator delivers typed defects to an injected writer; every returned prose
  version is revalidated, a paid response must have a receipt and original
  source digest, completed replies are not re-billed during replay, uncertain
  in-flight replies are not blindly retried, and there is a bounded attempt/
  observed-USD guard (never an LLM output-token limit). No review queue,
  human button, JSON patch or manual stage rerun.
- **Crucial boundary**: production LUMI's real model resolver, event extraction,
  comprehensive semantic/causal/scene checks, idempotent provider recovery and
  authenticated canonical DB commit are **not integrated**. The writer/checker
  callbacks are now connected to actual source-bound v0.19/v0.20
  validators and the OpenRouter writer transport in v0.21 laboratory tests;
  those tests inject a synthetic provider. A lab
  `SCENE_CANDIDATE_READY_NONCANONICAL` is **NOT** story-release approval.

Mara S1 first canon exit state remains **HOLD**. WorldState and original
Sonnet Spine were not modified. See [open Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306)
for proof and remaining production integration gates.


## v0.21 — Model writer, paid receipt recovery, actual source rechecks

[Detailed v0.21 architecture and acceptance gaps](./SERA_V021_MODEL_WRITER_INTEGRATION.md).

- [OpenRouter writer adapter](./openrouter_scene_writer_v021.py) reuses
  SERA's existing cap-free model transport, verifies source SHA against
  the provider's complete JSON output and builds model/response ID/cost
  receipts independently of model claims. Optional fallback automatically
  handles a **fully receipted** malformed first answer. The adapter can
  archive full paid provider replies before JSON parsing and reuse them
  after crashes without double charging; unknown in-flight calls never
  resend blindly. A durable archive is mandatory for future paid
  production qualification.
- [Actual v0.19/v0.20 evidence checker](./artifact_scene_checker_v021.py)
  loads a world+source-hashed evidence bundle and runs source-bound
  semantic risk review and versioned typed-state simulation for the
  candidate scene, rather than trusting an injected "READY" flag.
- Nonbillable validation can resume itself after a crash; the paid
  writer's request evidence remains durable and distinct from a scene's
  old model conclusions.

**Remaining blocker:** For every **newly rewritten scene**, the worker
must generate a completely new, paid, durable independent extraction
and qualification evidence archive before v0.21 can continue. Old
extractions cannot certify new prose. The production worker and
authenticated commit pathway are still NOT connected; no canonical
state was written, no paid calls occurred in unit tests, and Mara S1
remains HOLD. Zero required human steps, zero configured token output caps.


## v0.22 — Fresh independent evidence for EVERY new scene draft

[Architecture and precise acceptance boundaries](./SERA_V022_FRESH_EVIDENCE_WORKER.md).

- [fresh_scene_evidence_worker_v022.py](./fresh_scene_evidence_worker_v022.py)
  is the missing paid-but-durable stage that automatically runs a blind,
  source-complete v0.10 sentence sweep for the **current** prose version,
  v0.18 independent semantic risk processing, and independent source-bound
  v0.13 typed aspect proposals. Its outputs form a new hashed v0.21 evidence
  bundle consumed by actual v0.19/v0.20 scene revalidation.
- [unattended_scene_rewrite_v020.py](./unattended_scene_rewrite_v020.py)
  now has an optional per-draft `prepare_evidence` hook. It is explicitly
  separate from the nonbillable scene checker and cannot reuse an old
  draft's cached model opinions as truth. Each new draft must have a fresh,
  source/world-bound evidence archive before any structural-ready decision.
- Per-scene stage contracts bind source, entry world, registry, model
  policy, max provider requests and observed spend. Fully receipted malformed
  replies can automatically use a fallback, completed paid responses are
  reused on restart, and even an accidentally lost export can be restored
  without new provider calls. Potentially paid *unknown* in-flight calls
  end safely without manual intervention or blind resend.
- [Integration and fault-injection tests](./tests/test_fresh_scene_evidence_worker_v022.py)
  cover a non-Mara box open/close scenario, actual independent re-extraction
  of both original and rewritten drafts, generic v0.19/v0.20 checks,
  crash/restart, forged quotes, world revision isolation, spend limits,
  and recovered paid receipts. No paid models or production DB were touched.

**v0.22 remains LAB NONCANONICAL.** Real deployed LUMI worker integration,
all event/knowledge/causal gates, provider-side idempotency/reconciliation,
authenticated transactional canon commits, unseen paid story runs, and
full Mara S1 canonical exit are still required. Zero mandatory manual
actions, zero artificial model output-token ceilings; original Sonnet
Spine remains unchanged.


## v0.23 — Full candidate-event qualification and composed autonomous lab loop

[Architecture, test scope and remaining release blockers](./SERA_V023_FULL_EVENT_QUALIFICATION.md).

- [Full scene qualifier](./full_scene_qualification_v023.py):
  independent v0.10 event coverage is checked **against** all v0.13 typed
  source operations. Incomplete untyped MOVE / TRANSFER / knowledge /
  temporal-causal state effects, nonobjective reported facts carrying
  physical changes, unregistered physical actors/objects, missing lexical
  action cues and uncorroborated typed model state changes remain automatic
  re-extraction/replan blockers rather than silently passing.
- [v0.21 evidence checker](./artifact_scene_checker_v021.py) can run with
  `full_qualification=True`, and the v0.20 unattended controller now
  incorporates that third gate's exact source/world-bound findings into the
  automated writer recheck cycle.
- [v0.23 composed lab runner](./composed_scene_runner_v023.py) wires the
  previously built OpenRouter-compatible model transport, durable
  source-revision-aware evidence worker, v0.19/v0.20/v0.23 checks and
  automated bounded rewrite loop. Synthetic integration validates
  restart, immutable policy changes and correct noncanonical qualification
  without human corrections or paid model calls.
- All source event/reducer digests are linked, but a model's confident
  classification is **not** objective semantic proof, and successful
  noncanonical evidence is **not** permission for WorldState/EventGraph
  commits.

Missing for production: all unsupported state reducers, real production
LUMI worker/model resolver integration, provider-side missing-response
idempotency, independently qualified canon commit/rollback, and an unseen
real-model complete Mara S1 release. No output token caps or human
review/approval dependency.


## v0.24 — Source-bound movement and no-phantom-object scenes

[Detailed spatial architecture, evidence and remaining limitations](./SERA_V024_SPATIAL_PREVIEW.md).

- [Pure spatial preview](./spatial_preview_v024.py) binds every
  independently extracted MOVE/WORLD event to a real registered character,
  its exact source quote, a source-mentioned registered destination and
  an application-governed temporal/route case. The v0.5 temporal DAG
  solver rules out impossible arrival windows and undocumented routes.
  Held/worn objects accompany the actor only in an immutable, **noncanonical**
  candidate snapshot. No invented arrival minute, scene-specific Mara
  rules, model approval or production WorldState writes.
- The [v0.23 full-event gate](./full_scene_qualification_v023.py)
  no longer has to block a MOVE that passed all of those checks, but
  reported/uncertain claims, unsupported transfers/knowledge effects,
  missing route evidence and other full-scene defects remain blockers.
- [v0.21 evidence checker](./artifact_scene_checker_v021.py) now accepts
  truly facet-free scenes without inventing a watch/document only
  when the full v0.23 gate runs. Its zero-facet conclusion alone is
  **not** scene qualification.
- [v0.22 source-evidence worker](./fresh_scene_evidence_worker_v022.py)
  accepts an application-owned, explicitly policy-fingerprinted temporal
  case builder for each fresh prose revision. The
  [composed lab runner](./composed_scene_runner_v023.py) propagates the
  trusted policy. No runtime manual per-story correction is required.
- [Pure movement tests](./tests/test_spatial_preview_v024.py),
  [v0.23 integration](./tests/test_spatial_full_scene_v024.py) and
  [fully composed mock-provider movement-only worker tests](./tests/test_spatial_worker_v024.py)
  cover route gaps, impossible timestamps, source binding, actor/region
  identity, carried gear, reported-claim isolation and resumability.

**Still experimental and noncanonical:** Production trusted-route
policy provisioning, full spatial semantic certainty, ownership/knowledge/
causal/state reducers, real production worker and model resolver, provider
request idempotency and machine-authenticated atomic WorldState/EventGraph
writes are not complete. Mara S1 remains HOLD. No output token caps,
no human intervention requirements or production database changes.


## v0.25 — Source-bound custody transfer and verified character knowledge

[Complete architecture and noncanonical boundaries](./SERA_V025_RELATION_KNOWLEDGE.md).

- [Relation/knowledge preview](./relation_knowledge_preview_v025.py)
  independently validates source-grounded item holder transfers and
  character learning against active known identities, deterministic
  application-owned alias/fact policy, co-location, holder compare-and-swap,
  source chronology and exact evidence. Moving **holder** does not change
  **owner**. No new objective fact is invented when a character hears a
  rumor; only facts marked VERIFIED in the trusted registry can enter a
  character's knowledge candidate list.
- The [v0.23 full scene gate](./full_scene_qualification_v023.py) can
  now simulate these source-bound state categories when a valid
  `relation_case` is attached to the current source/world archive.
  Unqualified transfer/knowledge changes still require automatic
  re-extraction/replan rather than human approval.
- The [v0.22 worker](./fresh_scene_evidence_worker_v022.py) and
  [v0.23 composed runner](./composed_scene_runner_v023.py) have an
  application-owned per-draft `trusted_relation_builder` with an
  explicit `relation_policy_id` bound into resumable state.
- **Cross-family caution:** Physical movement, custody/knowledge and
  openable/document facets still replay against separate entry snapshots.
  If multiple stateful families occur together, the full-scene gate
  blocks until a single causally ordered reducer can qualify them.
- [Isolated](./tests/test_relation_knowledge_v025.py),
  [full-scene](./tests/test_relation_full_scene_v025.py) and
  [complete mocked-provider worker](./tests/test_relation_worker_v025.py)
  tests address source truth boundaries, rumor rejection, forged prior
  holder, identity mismatch, duplicate knowledge, nested items,
  durable model receipts and zero-human recovery.

**No canonical authorization, production LUMI DB writes, model output
token ceilings or mandatory operator review.** Actual real-world
verified-fact origins, mixed-family state order, legal owner changes,
production worker integration and unseen paid-story acceptance remain
open; frozen Mara S1 remains HOLD.


## v0.26 — One chronological simulated world across movement, custody, learning

[Complete architecture and verified boundaries](./SERA_V026_ORDERED_CAUSAL_REPLAY.md).

- [Ordered v0.26 causal preview](./ordered_causal_preview_v026.py)
  uses an application-governed global v0.5 time/route DAG and
  independently sourced event spans. It then runs v0.24 movement and
  v0.25 custody/verified-fact transitions **in source order**, always
  starting the next event from the prior event's isolated validated
  WorldState snapshot. Its proof includes before/after SHA-256 state
  lineage for every step, no fabricated arrival minute or canon write.
- [Full v0.23 gate](./full_scene_qualification_v023.py) now calls
  v0.26 when BOTH movement and custody/knowledge are present, provided
  the two trusted per-scene application policies exist and no v0.13
  facet actions require yet-unsolved causal composition. Incorrect
  handoff after only the sender has arrived, missing route, unsupported
  source effect or alleged physical state change still returns typed
  automatic re-extraction/replan instead of unsafe approval.
- [Pure/adversarial regression](./tests/test_ordered_causal_preview_v026.py)
  and [full staged mocked provider worker](./tests/test_composed_ordered_worker_v026.py)
  cover dynamic possession changes, previously carried object movement,
  duplicate cost-free receipt replay, trustworthy fact registry,
  impossible chronology, tampering, safe terminal failure and
  immutable source/entry policy. No real model bill was incurred.

**v0.26 is NONCANONICAL:** openable/document facets in the same moving/
transferring scene, nested objects, additional untyped state changes,
real application-authenticated facts/route/identity provider, missing
billable-response reconciliation, production LUMI worker binding and
transactional authenticated WorldState/EventGraph commits/rollback
are still required. Mara S1 remains HOLD. Zero mandatory manual
intervention, zero application-defined LLM output token ceilings.


## v0.27 — One source-ordered world PLUS watch/document facet CAS chain

[Architecture, exact safety boundaries and proof scope](./SERA_V027_ORDERED_FACETS.md).

- [New v0.27 ordered facet preview](./ordered_facet_preview_v027.py)
  evaluates movement, custody, verified character knowledge, openable
  observations/changes, and document appends in a SINGLE causal
  source-order simulation. Every action uses the CURRENT detached
  WorldState and evolving facet map; v0.13-compatible source evidence,
  registered roles, co-location and compare-and-swap rules remain
  mandatory. Each world and facet transition records a deterministic
  before/after SHA chain, but never grants canonical authority.
- [v0.21 archive checker](./artifact_scene_checker_v021.py) defers
  the old entry-world-only facet check for this exact mixed scope.
  [v0.23 all-event qualification](./full_scene_qualification_v023.py)
  actually invokes v0.27 and refuses unmatched model proposals,
  duplicate physical/document state event IDs or missing trusted
  application policies. [Unattended scene controller](./unattended_scene_rewrite_v020.py)
  marks candidate READY only with complete noncanonical v0.27
  proof and no unresolved source defects.
- [Deterministic adversarial tests](./tests/test_ordered_facets_v027.py)
  and [fully staged synthetic provider integration](./tests/test_composed_ordered_facets_v027.py)
  cover the seven-event story, wrong world/actor, unsupported route,
  forged document text, wrong expected watch state, duplicate facet
  evidence, fake physical effect, rumor not treated as objective fact,
  archive replay without new model charges, and fail-safe boundaries.

**Scope deliberately remains NONCANONICAL:** auth-backed LUMI worker
and policy registries, arbitrary state families or nested-object
graphs, publisher authority, provider-side idempotent charged-request
reconciliation, transactional WorldState/EventGraph commits and unseen
paid full-story qualification remain unimplemented. No production
DB writes, human manual patch/approval/restart or LLM output-token caps.
Mara S1 remains HOLD.


## v0.28 — StoryForge request/result bridge (lab, noncanonical)

[Architecture, signed billing preflight and release constraints](./SERA_V028_STORYFORGE_BRIDGE.md).

- [First-party StoryForge input adapter](./storyforge_bridge_v028.py)
  validates a v1 StoryForge request/result pair, the accepted English
  source scene, matching request/profile/world IDs, story/fidelity
  editorial PASS and immutable frozen plan/context. StoryForge's
  `publication_ready` is expressly **NOT** authorization to publish
  SERA scene facts or commit WorldState/EventGraph mutations.
- An independent application `verify_scope` authenticates the active
  world/request/policy snapshot; exact qualification-ready runtime
  profiles for all SERA model roles are bound to the job contract.
  Unknown or fallback models and stale content hashes fail safely.
- The default `paid_authorized=False` creates only a signed-source
  **preflight** without sending ANY request. A real paid job additionally
  requires a separate authenticated, exact request/world/model-bound
  `paid_grant` and `verify_paid_grant`. Existing provider-side SERA
  journaling, source revision extraction and noncanonical gate are reused.
- [Integration and adversarial tests](./tests/test_storyforge_bridge_v028.py)
  cover the actual v1 field shapes, mock OpenRouter staged scene
  verification, model receipt replay, signed-grant rejection, world
  and source tampering, and no publication authority or manual gates.
  ZERO real billable calls were made.

**Still open:** actual authorized live StoryForge/LUMI worker integration,
full authenticated policy-grant provider, complete unseen and Mara
story acceptance, real provider idempotent charged-request
reconciliation, and safe machine-only transactional WorldState/
EventGraph commits. Historical StoryForge internal output caps must
be retired before a production StoryForge generation path is
requalified; this bridge adds none. Experimental branch only.


## v0.29 — Cap-free StoryForge runtime, provider-profile preflight and no blind retry

[Architecture, actual StoryForge test coverage and production boundaries](./SERA_V029_STORYFORGE_CAPFREE.md).

- [StoryForge runtime](../../src/storyforge/runtime.py) has all FOUR
  historical numeric output caps removed. Its 8 model-stage profiles
  are preflight-checked before any StoryForge provider call; a registry
  policy silently restoring an output ceiling will be rejected.
- [Generic OpenRouter transport](../../src/generate.py) has opt-in
  no-output-ceiling enforcement on the **final normalized request**;
  [structured retry](../../src/english_story_pipeline.py) forwards it.
  StoryForge opts in for planning, audits, editing, prose and fidelity.
- StoryForge also opts in to **no blind network retry** when a
  timeout/connection failure could hide a paid provider response.
  This produces a machine-safe unknown-charge diagnostic instead of
  a duplicate request. Actual provider-side reconciliation is still
  required for fully autonomous crash/outage resume.
- [v0.29 StoryForge runtime/transport tests](../../tests/test_storyforge_capfree_v029.py),
  [dedicated self-hosted CI](../../.github/workflows/sera-v029-storyforge-capfree.yml),
  and [SERA source policy guard](./tests/test_storyforge_integration_policy_v029.py)
  keep both the cross-runtime output-ceiling ban and legacy StoryForge
  behavior under regression coverage, without billable model calls.

**No LUMI production worker or authenticated WorldState/EventGraph
commit integration, no paid unseen story run, and no Mara S1 canon exit
are claimed.** Separate historical scripts may retain old output caps;
this change scopes specifically to the formerly-blocked StoryForge
runtime and transport. Frozen Sonnet Spine, main and production DB
remain unchanged; no manual story repair/approval gate is introduced.


## v0.30 — Authenticated, known-generation read-only provider recovery

[Full design and hard provider limitations](./SERA_V030_READONLY_PROVIDER_RECONCILIATION.md).

- [OpenRouter known-generation reader](./openrouter_reconciliation_v030.py)
  uses documented authenticated metadata+stored-content GET endpoints;
  recovery requires independent app-authenticated binding of generation
  ID to EXACT original model/request SHA and exact stored prompt.
  Wrong model/prompt, unknown ID, unavailable content or unverifiable
  cost fail closed. No generation POST, no output token ceilings, no
  human operator step or canonical approval is possible.
- Durable v0.21 writer and v0.22 source/typed stages can attach read-only
  recovered replies to STARTED checkpoints; v0.18 semantic task ledger
  supports the same. v0.20 can restart after verified independent
  evidence becomes complete, retaining prior safe-stop proof.
- The composed runner and [v0.28 StoryForge bridge](./storyforge_bridge_v028.py)
  bind the selected authenticated recovery policy into the immutable
  job contract. Preflight without signed paid grant remains no-cost,
  and no real WorldState/EventGraph writes occur.
- [Provider provenance/adversarial suite](./tests/test_openrouter_reconciliation_v030.py)
  and [automatic scene restart suite](./tests/test_reconciled_scene_resume_v030.py)
  use zero-billable synthetic inputs and explicitly reject unknown
  generations or duplicate POSTs.

**Not solved:** A lost generation ID cannot be discovered by those GETs
from request SHA alone; provider idempotency/extra authenticated ID
capture is still required. Full v0.20 writer-REWRITE in-flight recovery,
real app-world auth, actual paid unseen-story testing, transactional
WorldState/EventGraph commit/rollback and frozen Mara S1 canon release
are NOT yet implemented. Production main/DB/Spine untouched.


## v0.31 — Recovery-only, already-paid scene rewrite after worker restart

[Architecture, official provider research and hard unknown-ID limitation](./SERA_V031_WRITER_RECOVERY.md).

- [Source-bound writer](./openrouter_scene_writer_v021.py) now exposes
  `recover_existing`, which **never creates a fresh completion POST**.
  Recovery accepts an existing exact paid envelope or an authenticated
  GET-only generation response for an already-STARTED identical
  model/request. Without a trusted ID, or without proof the provider
  request started, the existing safe-stop stays intact.
- [Scene controller](./unattended_scene_rewrite_v020.py) verifies prior
  chronological source/defect hashes, checkpoints and receipts, persists
  any recovered result before reopening the scene, preserves the
  old final failure and runs all independent state/source gates again.
- [Composed runner](./composed_scene_runner_v023.py) wires this only
  from an opt-in versioned reconciler; v0.28 StoryForge freezes the
  policy to its authorized job contract.
- [Crash and double-billing adversarial tests](./tests/test_writer_reconciliation_v031.py)
  prove recovery from an existing provider archive, recovery with a
  trusted known-generation reader, unknown-ID terminal failure and
  zero duplicate billable model dispatches. Fixtures are synthetic.

**Unresolved:** OpenRouter's documented chat completion and
generation GET endpoints do not establish a general chat idempotency
key or lookup of a generation ID from arbitrary local request SHA.
A completely lost ID cannot be safely recovered by v0.31. A real
app-authenticated provider trace/id capture or supported idempotent
contract remains necessary. No real paid calls, LUMI production
WorldState/EventGraph writes or Mara S1 canonical exit are claimed.
