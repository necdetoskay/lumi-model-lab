# SERA v0.1 — Scene Event Registry & Assurance

**Date:** 2026-10-15  
**Status:** isolated Model Lab experiment; NOT production-promoted  
**Repository:** `necdetoskay/lumi-model-lab`  
**Experiment branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Canonical source:** `evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json`  
**Canonical source Git blob SHA:** `fe1dda0047000438bbfaac69022e835bf7e0a1f8`  
**Story:** *The Platform That Arrived Empty*  
**Baseline commit:** `b51c2560aba4489fd62b8eb3bb25f17cca225901`

## 1. Purpose, boundaries, and invariants

Investigate whether each Spine beat can be expanded into a self-contained scene with a complete, verifiable input/output state; whether local scene repair can operate on only the affected scene and its dependencies; and whether a deterministic reducer plus independent semantic checking can prevent silent entity, object, location, knowledge, and causal drift.

**Non-negotiable boundaries:**

1. Original pre-Haiku Spine is immutable; verify its Git blob hash in tests.
2. Do not change V4, V4.1, V4.2, previous tests, historical runs, costs or evidence.
3. Do not call paid models in deterministic unit tests; no production database writes.
4. SERA records are experimental, protocol-versioned, and never merged into prior qualification cells.
5. All model-produced claims are proposals, not authority. A semantic PASS is neither deterministic proof nor permission to commit production canon.
6. No truncating/max-output token cap imposed as a cost-saving policy on model generation. Transport constraints must be explicit, and incomplete output must fail closed.
7. Maintain immutable accepted snapshots and append-only event evidence; rollback is by new version, never editing an old accepted record.

## 2. Architecture and authority

```text
Original Sonnet Spine (immutable, 9 ordered beats)
       |
       v
Spine->SceneContract compiler (derived sidecar, no source mutation)
       |
       v
Entry state S[n] + current SceneContract + relevant evidence
       |
       +--> Event planner (proposed typed events)
       +--> Scene writer (prose, reported entities/events)
       +--> Independent extractor (blind extraction from prose)
       |
       v
Entity/event reconciliation (union; do not silently discard differences)
       |
       +--> deterministic span/pointer/schema check (Python)
       +--> JEV atomic evidence & semantic verification (future adapter)
       +--> strong-judge escalation for ambiguous/critical disagreement
       |
       v
Python reducer + deterministic invariant validator
       |
       v
Accepted, versioned full-state snapshot S[n+1] + append-only events
       |
       v
Next scene entry; affected-dependent-scene invalidation if upstream changed
```

Application-owned Python validates typed operations and computes the state. It does not infer the meaning of arbitrary prose. JEV is a separately qualified semantic decision candidate, not a registry writer. Neither writer nor extractor may directly mutate an accepted snapshot.

## 3. Three distinct representations

- **SceneContract:** derived from beat ID, role, location, causal prerequisites, prohibited behaviors, required disclosure, intended exit conditions. It is a plan, not observed state. Initial experiment maps 9 beats to 9 scenes; later comparisons can test merging/splitting without changing source Spine.
- **Event Ledger:** immutable, time-indexed typed events, entity refs, actor refs and precise textual evidence spans; event semantics are application-defined. Newly introduced objects/characters are explicit `CREATE_ENTITY` proposals subject to authorization.
- **Full Scene Snapshot:** every registered entity, including those unchanged or not mentioned in the current scene; stable IDs, ownership, last known location, physical properties, per-character knowledge and associated certainty, fact registry, open threads and revision. Canonical exit is always `reduce(accepted_entry, approved_events)`. The next entry is byte-equivalent at the data-model level to that exit.

Store state diffs for efficiency, but NEVER substitute a diff for the full authoritative state snapshot. A model request may receive a relevant projection of the snapshot, whereas the engine retains all entities.

## 4. Completeness is an empirical property, not an LLM assertion

**Two-direction verification:**

- `state -> text`: every proposed mutation must carry an exact quote/span that exists in the accepted scene prose; JEV can independently decide whether that quote *semantically entails* the event.
- `text -> state`: writer-reported and independent-extractor-discovered mentions/events are unioned; unmatched items are reconciliation findings, not automatically rejected or automatically accepted. A model can miss the same event twice: completeness requires a labeled corpus, recall/precision, protected adversarial cases, and escalation.
- Purely deterministic checks: valid references, object ownership, co-location, allowed travel time, chronological ordering, knowledge prerequisites, duplicate event IDs, immutable identity, preserved unchanged entities, correct snapshot handoff and source blob identity.
- Non-deterministic checks: implicit state changes, ambiguous pronouns, emotional subtext, whether prose actually warrants a reported claim, whether any material event was omitted. JEV judges **atomic propositions** with explicit `SUPPORTED / CONTRADICTED / INSUFFICIENT_EVIDENCE` routing (via decision-question adapter; mapping must be calibrated). Confidence is not truth.
- Zero unexplained mismatches is required for a scene PASS; an unclear event is escalated or the scene is held, never silently committed.

## 5. Epistemic boundaries

Differentiate `OBSERVED`, `INFERRED`, `HYPOTHESIS`, and `UNKNOWN`. Character A learning a fact never implies character B knows it. A train manifest is evidence of a recorded arrival entry, not evidence of the physical train. Sealed dispatch contents are not available to witnesses. Do not promote hypotheses into world fact without an explicit authorized event and evidence. Keep narrative scene state separate from Project LUMI's typed world/character mutations and atomic persistence authority.

## 6. MVP event contracts

The first deterministic engine supports:

- `CREATE_ENTITY` (explicitly authorized introduction; never implicit);
- `MOVE_CHARACTER` (known travel route and sufficient elapsed time; held objects follow);
- `TRANSFER_OBJECT` (current holder and recipient co-located);
- `UPDATE_OBJECT` (allowed property change, actor in reach, and object not held by another person);
- `LEARN_FACT` (registered fact + explicit application-owned `(character_id, fact_id)` observation grant; a prose quote alone cannot grant access) and `TELL_FACT` (sender knows fact, recipient co-located);
- `RECORD_FACT` (holder of a document logs known information);
- `OPEN_THREAD` / `RESOLVE_THREAD` (well-formed thread transition).
- `INTERACT_OBJECT` (records a non-mutating observation or interaction in the append-only ledger; the object remains unchanged).

Other actions fail closed until implemented. Evidence strings are checked for literal occurrence in prose (a necessary condition, not a sufficient semantic proof). Every accepted event is recorded; no entity may disappear during a scene.

## 7. Time and location semantics

Timeline uses minutes since session-day midnight, not unsafely parsed natural-language timestamps. A `MOVE_CHARACTER` event timestamp denotes **arrival**. Minimum route times are supplied by a curated graph derived from the Spine:

- North Quay Station -> Signal Archive: 10 min
- Signal Archive -> Rail Yard: 15 min
- Rail Yard -> North Quay Station: 15 min
- Signal Archive -> North Quay Station: 10 min

No teleporter path to sealed dispatch office exists; visits are prohibited. Conservative departure availability uses the last recorded action time of that character. Future iterations can add intervals, waiting, simultaneous actions and route reachability. This MVP must not infer that a fictional train moved from a manifest signature.

## 8. Repair ownership and dependency invalidation

- Wrong Spine/contract: repair the derived plan with explicit approval, never rewrite prose to hide the defect.
- Wrong scene prose or missing evidence: local prose repair, fixed accepted entry.
- Wrong event extraction: independent re-extraction/reconciliation, no blind state mutation.
- Invalid proposed event: reject and repair proposal/prose locally.
- An accepted earlier-scene change invalidates affected downstream `causal_dependency_keys` and any actual read-set of entities/facts/threads; revalidate before reuse.
- Whole-story prose quality, pacing and literary coherence still receive an assembly-level review; it cannot mutate canonical event state.

## 9. Acceptance gates and milestones

**M0:** source SHA pinned; derived nine-scene contracts; complete documented design.  
**M1:** standard-library-only Python reducer, full state snapshots, evidence pointer checks, deterministic error codes, unit tests (no model calls).  
**M2:** writer/extractor output schema and independent coverage matcher; gold fixtures measuring mention/event/entity/knowledge recall and precision.  
**M3:** JEV atomic-proposition adapter; provider preflight, calibrated HOLD/ESCALATE, cost and latency logging, adjudicated test set.  
**M4:** a live, isolated nine-scene Mara run; compare with V4.2 on structural validity, false PASS, repair locality, quality, latency and per-call USD. Do not promote without cross-case repeat evidence.

**M1 success does not imply full extraction completeness.** No JEV/live-model result is claimed until M3/M4 actually runs.

## 9.1 M2 reconciliation implementation (2026-10-15)

M2 implements `sera.extraction.v0.1` reports for a writer and a separately
prompted, blinded independent extractor. Both are bound to the same prose
SHA-256 and entry revision. Each item carries an exact textual evidence quote.
Rather than trusting the LLM's character offsets, the `extractor_adapter`
maps the exact quote and occurrence index to string offsets deterministically.
Unknown exact quote, stale revision, fabricated source role or malformed schema
fail closed.

Known-entity aliases offer a supplementary lexical scan. Reports are compared
by canonical entity ID + qualified presence role, and typed event signature
(operation, arguments, event time, modality). A mismatch, an unsupported reducer
operation, an unknown event time, a non-asserted event, a provisional new entity,
or an unknown canonical ID yields `HOLD`. Agreement without a flagged
mismatch yields **`RECONCILED_PENDING_SEMANTIC`**, never production PASS.

M2 preserves quote-span evidence but quote existence alone does not prove
semantic entailment; JEV is a potential M3 atomic semantic gate. JEV itself
cannot prove that no unmentioned object was missed. The six synthetic,
manually adjudicated cases include an intentionally shared object omission
in which both extractors agree yet have 0% recall for that case; this
demonstrates why calibration must use external gold annotations.

The independent transport is opt-in only, one billable OpenRouter request
when explicitly launched with `--live`; the CI always uses mocked transport.
No model quality claim follows from these synthetic tests.

## 9.2 M3 preliminary JEV atomic-contract implementation

`jev_verifier.py` compiles M2 candidate entity/presence and typed-event claims
into versioned `choice` questions for the pinned
`typesafe/jev-1.13` Decisions API. The bundle carries source-prose SHA-256,
entry revision, registry and exact evidence spans, but strips producer identity
to reduce evaluation bias. M2 coverage is recomputed before the questions are
issued to prevent a forged clean coverage status.

Each claim has three evidence outcomes:
`SUPPORTED`, `CONTRADICTED`, and `INSUFFICIENT_EVIDENCE`.
The latter is an explicit escalation path. Contradiction routes to local repair;
a clean JEV answer cannot override an unresolved M2 discrepancy. Even all
SUPPORTED outcomes yield only
`PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW`, never commit authorization.

JEV response and confidence remain probabilistic, uncalibrated evidence.
Separate labeled calibration, provider timing/cost observations, error
adjudication, and independent holdout are REQUIRED before qualification.
The transport is lazy and opt-in; no paid API call belongs in offline CI.
No answer grants world/character/database mutation authority.

## 10. Initial spine integrity notes

The first two beats distinguish Vane's initial statement about 02:10 from his bounded direct observation through ~02:07. The validator must not confuse a reported claim with observed truth. The reversal beat similarly distinguishes a slow clock's face from a track-plate-triggered missing strike. The two decision branches must remain uncommitted until an actual choice, and audit authorization must never be inferred from filing a request.

## 11. Working commands

From repository root:

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.spine_contracts evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json
```

No external packages or API keys required for M0/M1.

## 12. Typed object/weather history extension (v0.2)

See [WORLD_STATE_V02_ARCHITECTURE.md](./WORLD_STATE_V02_ARCHITECTURE.md) and [Issue #303](https://github.com/necdetoskay/lumi-model-lab/issues/303). A standalone standard-library typed world reducer, character equipment graph, environment state, SQLite append-only event history and versioned snapshots are now implemented as **parallel experimental modules**. Existing v0.1 pipelines are not automatically rewritten. A live-model evidence/JEV-to-event approval bridge, relative-time resolution, and production PostgreSQL mapping are not yet complete. Unapproved model text cannot mutate SQLite state.
