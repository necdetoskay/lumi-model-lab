# SERA v0.26 — Source-Ordered Cross-Family Causal Replay

**Status: EXPERIMENTAL / NONCANONICAL.** No real LUMI production-worker
deployment, authenticated WorldStore writes, provider billing or frozen
Mara Sonnet Spine changes. Mara S1 canonical remains HOLD.

## Previous structural flaw

v0.13 facet, v0.24 movement and v0.25 possession/knowledge previews
each replayed against the ORIGINAL WorldState entry independently.
That could not qualify a mixed sequence:

1. Vane and Mara walk from station to archive.
2. Vane hands Mara his pocket watch at archive.
3. Mara learns a registered, independently verified fact.

The independent custody preview would see both actors at station,
not at their post-movement locations. Conversely, a scene where only
Vane has arrived could incorrectly pass a handoff modeled at the
original station. v0.25 correctly placed mixed families on HOLD.

## v0.26 implementation

[ordered_causal_preview_v026.py](./ordered_causal_preview_v026.py)
is a **single immutable-entry, mutable-isolated-preview reducer** that
processes registered MOVE + TRANSFER + KNOWLEDGE_UPDATE in the exact
order of their independent v0.10 source spans.

- Every state event is bound to its exact quoted source span and unique
  original event ID; effects require OBSERVED_ACTION epistemic status.
  Event spans cannot overlap, vanish from the action plan or reorder
  without an explicit failure.
- Application-owned v0.5 temporal policy must cover EVERY participating
  state event in that precise source order, including custody and
  knowledge as nonmovement ACTION nodes. A global DAG proves route
  feasibility, causal constraints and minimum travel times. No earliest
  feasible minute is ever claimed as a narration-observed timestamp.
- For each MOVE, v0.24 checks the *CURRENT simulated world*: registered
  character, actual current-location route, source-mentioned destination,
  carried and worn items, nested-object safe failure and original
  source/actor identity.
- For each TRANSFER/KNOWLEDGE_UPDATE, v0.25 checks the *CURRENT simulated
  world*: exact old holder CAS, same-location sender/recipient, active
  entities named in the quote, holder/owner separation, externally
  VERIFIED fact registry, no rumor promotion and duplicate-knowledge
  prevention.
- Every step leaves a deterministic before/after WorldState SHA-256
  lineage; the next operation starts from the previous step's fully
  validated candidate state. The frozen entry and DB are unchanged,
  the simulated world never gets a real canonical event/approval, and
  the returned result is explicitly NONCANONICAL.

[v0.23 full_scene_qualification_v023.py](./full_scene_qualification_v023.py)
uses v0.26 only if **both movement and relationship/knowledge events**
exist, trusted temporal+relation policy is supplied, and there are
**no v0.13 typed facet operations** in that scene. A failed v0.26
lineage triggers automatic
\`ORDERED_CAUSAL_REPLAY_UNQUALIFIED\` / re-extraction-or-replan.
No more treating two independent green assessments as a global PASS.

With openable/document typed facets present the scene still gets
\`CROSS_FAMILY_STATE_ORDER_UNQUALIFIED\` until those operations can
also share the common replay state. OTHER unknown effect families
remain blocked as before.

## Regression evidence

- [Deterministic v0.26 reducer and full-gate tests](./tests/test_ordered_causal_preview_v026.py):
  successful walk → handoff → learning, handoff-before-walk carries
  the item with its NEW holder, physically impossible handoff after
  only the sender walked, missing route, too-early timestamp, source
  quote tampering, missing action, reversed timeline, alleged physical
  change, rumored fact, exactly linked step hashes and no canon write.
- [Composed v0.26 worker tests](./tests/test_composed_ordered_worker_v026.py):
  actual v0.10 source sweep + v0.18 risk stages + v0.19/0.20/0.23/
  v0.24/0.25/0.26 composed worker, injected synthetic OpenRouter
  envelopes, new prose-scoped evidence, restart-safe paid receipt
  replay and machine-only safe-stop on invalid facts/routes.
  Tests do not incur paid model calls.

## Non-negotiable remaining tasks

1. General ordered typed facet operations (watch, notebook, physical
   changes) within that same evolving state; generalized nested
   object containment and additional world-state reducers.
2. Real authenticated LUMI world/identity/fact/route source providers,
   source-evidence model risk qualification, and complete cross-scene
   causality/knowledge isolation.
3. Production story worker/model resolver binding with durable
   stage/receipt ownership and provider request idempotent recovery
   for potentially billed lost responses.
4. Machine-authorized transactional WorldState/EventGraph CAS, rollback,
   full paid unseen-story end-to-end qualification and frozen Mara S1
   canonical HOLD exit. No manual repair or human approval dependency.
5. No model output-token ceilings at any stage, and no unsafe auto
   retry when a paid request has an uncertain in-flight result.

An offline source- and policy-consistent PASS proves a **possible,
noncanonical** state transition, not that a model's narrative
interpretation is objectively true or a world commit is authorized.

Tracked under [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
