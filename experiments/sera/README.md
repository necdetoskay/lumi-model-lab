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
