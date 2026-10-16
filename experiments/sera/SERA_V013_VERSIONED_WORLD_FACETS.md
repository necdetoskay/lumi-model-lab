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
