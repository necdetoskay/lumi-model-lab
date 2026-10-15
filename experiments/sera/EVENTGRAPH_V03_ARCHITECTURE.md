# SERA EventGraph v0.3 — Narrative Event State & Causality Architecture

**Status:** Isolated experimental implementation, not production-qualified  
**Date:** 2026-10-16  
**Issue:** [#305](https://github.com/necdetoskay/lumi-model-lab/issues/305)  
**Related:** [#303 Object State](https://github.com/necdetoskay/lumi-model-lab/issues/303), [#304 Typed Events & Time](https://github.com/necdetoskay/lumi-model-lab/issues/304)  
**Frozen baseline:** original Sonnet Mara Spine Git blob `fe1dda0047000438bbfaac69022e835bf7e0a1f8`.

## 1. Goal

In addition to entities, characters and environment, every material narrative event
is a persistent **first-class object**: who participated, what objects were used,
what had to be true, which earlier events caused it, what changed, which assertions
were reports rather than truth, and where its exact textual evidence lives.

Differentiate THREE authorities:

1. **Narrative event candidate**: proposed data extracted from prose, untrusted.
2. **Narrative event record**: reviewed, typed and linked to world mutations; its
   participant/object roles, provenance and causal edges persist.
3. **World-state event/reducer**: the Python state machine computes the actual
   before/after effect. Models NEVER dictate accepted state diffs.

A non-mutating action (e.g. looking at a watch) is still an event with a stable
ID, related objects, evidence and causal links; it has an **empty physical diff**.

## 2. Typed event contract

`event_graph_v03.py` defines `sera.narrative-event.v0.3`. The exact fields are:

- `event_id`, `event_type`, `scene_id`, `location`, `epistemic`;
- `participants: [{id, role}]`: ACTOR, SPEAKER, LISTENER, WITNESS,
  REMOTE_WITNESS, AFFECTED, RECIPIENT;
- `objects: [{id, role}]`: TOPIC, EVIDENCE, TOOL, AFFECTED;
- `time: {ordinal, earliest_minute, latest_minute, exact_minute}`;
- `caused_by: [prior_committed_event_id]`;
- `preconditions: [{scope: ENTITY|REGION, id, path: [field...], equals}]`;
- `evidence: {prose_sha256, start, end, quote}`: exact UTF-8 text hash and
  Python codepoint substring span;
- `world_event`: ONE valid, strictly typed v0.2 state operation with same
  event ID. An event with no physical change can use `INTERACT_ENTITY`.

No `before` or `after` fields may be supplied by a language model. A
proposal carrying invented accepted effects fails schema validation.

The valid event type and the world mutation type are **separate dimensions**:
`TESTIMONY` may map to `LEARN_FACT`; `MOVEMENT` may map to
`MOVE_CHARACTER`; `OBSERVATION` may map to `INTERACT_ENTITY`.

## 3. Epistemic and identity safety

`REPORTED_CLAIM` events cannot directly create physical reality. In this
experiment, reported knowledge may be recorded only as a namespaced fact ID
beginning with `claim:` and as a reviewed `LEARN_FACT`, or as a
non-mutating interaction/scene progression. `HYPOTHESIS` cannot directly
mutate world state.

The Mara example demonstrates the critical distinction:
*Vane says his watch stopped at 02:07* -> Mara knows **Vane's statement**.
It does NOT establish when a train physically arrived.

Participant references must resolve to registered characters. Object
references must resolve to physical entities (or to a separately authorized
INTRODUCE_ENTITY). Each explicitly changed entity must appear in the graph
with a role; **movement also changes the locations of carried items and worn
clothes**. Unreported indirectly moved objects cause whole-transaction HOLD.

## 4. Causality and order

Only references to **earlier committed narrative events in the same stream**
are permitted. This rejects forward references and cycles by construction.
Event IDs are never recycled. Scene ordinals increase within each scene, and
app-owned event timestamps must be within explicitly stated narrative bounds.

Unknown exact event clock times remain **null** in the narrative record.
The v0.2 world reducer presently requires an integer `at_minute`; that is an
APPLICATION RESOLUTION CURSOR for the experiment and is not evidence that a
character performed the action at that exact minute. Before live acceptance,
the #304 relative-time resolution protocol must pin a valid explanation of
the cursor without making fictional clock claims. No model may invent a
timestamp purely to pass Python checks.

Downstream repair can retrieve `descendants(stream, event_id)` to determine
the events that would require revalidation if an upstream dependency changes.

## 5. Before/after effects computed by Python

For each accepted v0.2 reducer invocation:

```text
before = accepted_world_snapshot(revision-N)
after  = apply_event(before, trusted_approved_world_event)
effects = recursive_diff(before.entities/regions, after.entities/regions)
```

Effects store `scope`, `id`, `path`, `before` and `after`. No change means
empty effect list; the related event and its objects still remain in history.

A changed character and EACH changed object must appear in the event's
role relations. An entity remaining unchanged is preserved by the full world
snapshot. An invalid dependency, missing relation, wrong precondition, invalid
state transition or missing application authorization fails closed.

## 6. SQLite architecture and atomicity

`EventGraphStore` wraps the existing **experimental** `WorldStore` on
the **same SQLite connection**. `WorldStore.commit` accepts a trusted
in-transaction callback. Both sets of tables update within the same
`BEGIN IMMEDIATE` transaction and either both commit or both roll back.

Tables:

- `narrative_events`: stable ID, scene, revision, ordinal, kind, epistemic,
  proposal hash and trusted review receipt;
- `narrative_participants`: who was linked and in what role;
- `narrative_objects`: items referenced or affected;
- `narrative_dependencies`: directed causal prior-event edges;
- `narrative_effects`: reducer-derived entity/environment diffs;
- `narrative_lifecycle`: append-only PROPOSED, VERIFIED, COMMITTED
  transitions for a successfully committed review;
- `narrative_rejections`: append-only REJECTED proposal identity and reason,
  **without** a world-state mutation.

Changes/deletions of accepted graph ledger/history rows are blocked by SQLite
triggers; event ID and stream-scoped relationships have unique constraints.
`verify()` replays world state, requires a **1:1 correspondence** between
world events and graph records, and checks every derived effect and causal
predecessor again.

The proposal fingerprint/review hash is an equality binding and audit aid,
NOT a cryptographic signature or real access-control boundary. The
`authority="APPLICATION"` field must originate from **trusted server
orchestration**, never from model JSON. No real JEV-to-authority binding has
yet been qualified.

## 7. Queries

- `get(stream, event_id)`: event, roles, evidence and computed effects;
- `history(stream, entity_id)`: any event involving or changing a person/object;
- `timeline(stream, scene_id)`: scene event ordering;
- `descendants(stream, event_id)`: causal downstream graph;
- `effects(stream, event_id)`: typed Python-computed diffs;
- `lifecycle(stream, event_id)`: committed or rejected lifecycle;
- `reject(stream, proposal, reason)`: append-only rejected proposal audit,
  no world mutation;
- `verify(stream)`: world event hash chain, snapshots, graph correspondence,
  causal references and derived effects.

The long-running world state snapshots/history remain in Object State v0.2.

## 8. First real Mara prose — explicit HOLD

Frozen 243-word live generated scene, source:
[Actions #38808450095](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38808450095).
[Gemini+JEV continuation #38809210994](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38809210994).

File `fixtures/mara_s1_real_eventgraph_candidates_v03.json` retains the
**exact 243-word prose SHA-256** and nine analyst-curated candidate events with
quoted text, exact codepoint offsets, participant/object relations, typed event
intent, causal links and **explicit reasons for HOLD**. Nothing there is a
verified v0.3 record or actual state commit.

The new physical objects **bench** and **pencil** were omitted by both
models. The watch case is closed during the scene, but the v0.2 object schema
does not yet have `case_open` as a typed property. Notebook writing needs
an explicit `RECORD_FACT` or document-content event type. Both gaps remain
HOLD; neither can be papered over by a fabricated state mutation.

JEV previously returned ESCALATE for the real scene. No attempt is made to
override that decision. The accompanying tests verify evidence quote offsets
against this EXACT real prose, prove the nine candidates stay noncanonical,
and reject ungraphed direct world events.

## 9. Qualification gates / next actions

1. Extend #304 with fully typed event arguments, epistemic claim facts and a
   grounded relative-time protocol; do not invent absolute times.
2. Add richer immutable document content, object case position, location event
   exceptions, and optional attendance/knowledge rules in a reviewed v0.4 schema.
3. Implement a trusted semantic/JEV+independent extractor result-to-approval
   adapter with audit trail and exact source SHA binding. A model confidence
   score alone is insufficient.
4. Create human-adjudicated gold labels and negative controls from the real
   Mara first scene, including omitted bench, pencil and reported train 41.
5. Qualify one genuine scene state commit, then only later nine-scene replay.
6. Real LUMI/PostgreSQL migrations are **not** covered here and need separate
   design freeze, DB mapping, security and EOS approval.

Offline only:

```bash
python -m unittest discover -s experiments/sera/tests -v
```

No paid model/API calls and no production LUMI database writes are part of
EventGraph v0.3 tests.
