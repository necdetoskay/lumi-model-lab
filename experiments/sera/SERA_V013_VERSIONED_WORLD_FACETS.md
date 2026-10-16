# SERA v0.13 — Versioned World State facet reducer qualification

**Date:** 2026-10-16  
**Branch:** `experiment/sera-scene-state-v0-1-20261015` (isolated from main)  
**Issue:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Source Mara S1 prose SHA:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`  
**Actual CI:** [38867777726](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38867777726)

## Context and design decision

v0.12 achieved a `SHADOW` projection for watch case
`UNKNOWN → OPEN → CLOSED` and one verbatim notebook append, but
`world_state_v02.py` and its SQLite store do not support these property
families. Neither physical watch states nor text entries belong in
generic `appearance` or `condition.functional` properties.

Rather than changing the existing v0.2 canonical schema or silently
migrating active worlds, SERA now defines an **explicitly experimental,
versioned candidate schema**:
`sera.world-state.v0.13-experimental` in
`experiments/sera/world_state_v013.py`.

The v0.13 snapshot contains a byte-identical, validated copy of the
original v0.2 entry world, a SHA binding to it, and separately typed
object aspects. Production `WorldStore`, existing snapshots, the
story prose and original Sonnet Spine remain untouched. There is
**no database migration** in this phase.

## Typed events and guards

| New event | Payload | State effect |
| --- | --- | --- |
| `OBSERVE_OPENABLE` | `expected=UNKNOWN`, `observed=OPEN/CLOSED` | Source-backed initial observation; not a physical action |
| `SET_OPENABLE` | `expected=OPEN/CLOSED`, `next=OPEN/CLOSED` | Exact compare-and-swap physical state transition |
| `APPEND_DOCUMENT_ENTRY` | `expected_append_count`, `text` | Append source-verbatim document entry, preserving prior content as UNKNOWN |

Every event requires a registered object and character, compatible
aspect type, co-location, exact source text span and numbered sentence,
strict source ordering, unique event ID and an exact typed payload.
Additional fields such as a guessed `at_minute` are rejected.

All three event types are pure reducers. No model can create a real
canonical state update through this module.

**Simulated authority:** Tests and the experimental Mara runner
supply an explicit `OFFLINE_APPROVAL_FIXTURE` and exact event digest
approval mapping. This checks that a reducer **requires a separate
approval argument** but is **not authentication**, a human signature,
or proof of trusted adjudication. This v0.13 module does not expose a
production commit mode.

## Immutable history, consistency and recovery

Event receipts use a deterministic hash chain; event keys,
typed effects, prior hashes and latest projected state are verified by
complete replay from the original v0.2 entry snapshot. Invalid old
values, duplicate IDs, insufficient evidence and invalid event order
fail closed.

`simulate_batch` returns a new detached snapshot, leaving the input
unchanged if any event fails mid-batch.
`restore_simulated_revision` reconstructs an earlier version
without deleting or modifying the original snapshot. This is a
functional local rewind, **not** a production backup or database
disaster recovery mechanism.

## Real Mara S1 evidence integration

`mara_s1_versioned_facets_v013.py` reads the v0.12 **actual
Gemini+Haiku archived correction artifact**, never a synthetic replacement
or a new paid provider result, and adapts only three source-pinned
properties:

1. `s004`, Vane's open pocket watch → `OBSERVE_OPENABLE`
   `vane_watch.position: UNKNOWN → OPEN`.
2. `s011`, case closure → `SET_OPENABLE`
   `vane_watch.position: OPEN → CLOSED`.
3. `s021`, Mara adds `Discrepancy documented; explanation unknown.`
   → `APPEND_DOCUMENT_ENTRY` to `mara_notebook`.

The entry scene's notebook's **pre-existing content is UNKNOWN**. The
new append does not prove it was empty or capture every earlier line.
Clock readings `02:07` / `02:10` remain object/document data,
**not inferred action times**. No objective train arrival is created.

Run [38867777726](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38867777726):

- **337/337 Python regression tests PASS**.
- **Three** source-bound typed events simulated under an explicit
  offline-only approval fixture.
- Openable case final state **CLOSED**.
- **One** exact-source notebook append.
- Initial v0.2 world snapshot **unchanged**.
- Event chain replay **PASS**; reconstruct revision zero **PASS**.
- **Zero** production writes, **zero** real approval grants,
  **zero** model API calls and **zero** output-token ceilings.

Relevant modules:
`world_state_v013.py`,
`mara_s1_versioned_facets_v013.py`,
`tests/test_world_state_v013.py`,
`tests/test_mara_s1_versioned_facets_v013.py`,
`.github/workflows/sera-mara-v013-real-reducer.yml`.

## Important non-goals / remaining gates

The presence of an externally supplied `approvals` dictionary in a
test does **not** create a trusted decision authority. The system
still needs a separate, appropriately authenticated adjudication
service and auditable production approval workflow, with database
transaction, provenance and rollback tests.

The 3 typed events do **not** cover the complete Mara scene.
Among the unresolved items are the remaining 22 Gemini event candidates,
bench/pencil registration, a watch case as a part vs an independent item,
notebook's earlier write action, attributed testimony/knowledge, and
narrative temporal constraints. All model outputs and suggested repairs
remain `HOLD` until separately qualified.

**Next:** run a *full-scene event/entity blocker census* and verify
all 25 candidate semantics before allowing any first-scene exit state
to be accepted. Then create a versioned migration and real commit
authorization design; never silently migrate from v0.2 or write directly
to the production database.

## Complete Mara model-event and entity-mention audit

After qualifying the three versioned facet reducers, two independent
**offline** censuses inspected the **original archived provider evidence**.
Neither census submitted any additional model requests or generated an
accepted scene exit state.

### 25 source-bound event candidates

[Actual 25-event audit run 38868197633](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38868197633)
via `mara_s1_event_census_v013.py` and
`mara_s1_event_census_cli_v013.py`.

| Gemini-proposed event type | Candidates |
| --- | ---: |
| `CLAIM_MENTION` | 8 |
| `COMMUNICATE` | 5 |
| `OBSERVE` | 4 |
| `MOVE` | 3 |
| `WRITE` | 2 |
| `OPEN` | 1 |
| `CLOSE` | 1 |
| `KNOWLEDGE_UPDATE` | 1 |
| **Total** | **25** |

Of those **16 were tagged observed actions**, while **9 had
`REPORTED_CLAIM` epistemics**. Eight `CLAIM_MENTION` candidates
do **not** exhaust all reported statements. Eleven candidate events
still need qualified typed effect/timeline mapping, nine include
unregistered identities, and all 25 lack authenticated adjudication and
a measured independent completeness benchmark.

The two Haiku-supported semantic repair proposals remain marked
as **noncanonical corrections**. The three v0.13 reducer events are
offline **simulations**, not a three-event approval of Mara S1.
**0/25** original event candidates are authorized for canonical commit.

### All 60 model-proposed entity/character mentions

[Actual all-mentions audit run 38868633198](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38868633198)
via `mara_s1_mention_census_v013.py` and
`mara_s1_mention_census_cli_v013.py`:

- **28/28 original numbered source sentences**, **7/7 archived
  source-bound batches**, **60 exact-source mentions**, **22 distinct
  entity references**.
- **16** different unregistered/provisional references including
  `new:bench`, `new:pencil`, `new:watch_case`, document/record
  subobjects, location aliases and reported train subjects.
- The model proposed `PRESENT` once for each of
  `new:bench` and `new:pencil`; this is *not* verified identity,
  ownership, physical presence or authorization to create entities.
- `new:vane_thumb` is an anatomical part mention, **not** a standalone
  object for inventory.
- `new:train` and `new:train_41` are
  `REPORTED_ONLY`; the archive's quoted `Arrival recorded: 02:10`
  is **not** an objectively verified physical arrival.
- `new:watch_case` remains a provisional reference / potential
  component of `vane_watch`; its ontology/identity is not silently
  inferred or created.

No new physical entity was auto-registered: **0**. Distinguishing
entity mentions from event references caught the previously hidden
`bench` entity, which is explicitly mentioned but does not require a
new state-changing event.

**Current test gate:** [run 38868633198](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38868633198)
— **345/345 Python tests PASS**, with versioned v0.13 reducer replay
qualification and real-provider mention census separately green.

### Next qualification sequence

1. Perform context-sensitive identity resolution of every unregistered
   candidate: registered objects versus components, anatomical parts,
   locations, evidence artifacts and reported subjects.
2. Review typed effects for the 25 events, especially apparent movement,
   document writing, observation and testimony. Preserve `HOLD`
   on ambiguous candidates; never convert claims to world facts.
3. Use an authenticated external adjudicator / independent validation
   authority and genuine calibration data, not fabricated model or fixture
   approvals.
4. Only then design production migration, validated transactional
   WorldStore + EventGraph commit and rollback checks. The source-bound
   v0.13 experiment is not a production schema upgrade.
