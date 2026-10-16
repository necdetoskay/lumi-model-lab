# SERA v0.24 — Source-Bound Physical Movement and Spatial Preview

**Status: experimental / noncanonical.** This does not deploy to the real
LUMI story worker; no WorldState/EventGraph commits or simulated model
"approvals" are ever elevated to application authority. Frozen Sonnet
Spine and Mara S1 canonical HOLD remain untouched.

## Problem closed

v0.23 had to block every MOVE event because the v0.13 openable/document
CAS reducer does not simulate characters changing locations. v0.5
already provided a **pure temporal DAG solver** and v0.2 already
specified the world entity/held/worn invariants. v0.24 reuses these
contracts rather than inventing another model's judgement of when or
where a character has travelled.

[spatial_preview_v024.py](./spatial_preview_v024.py) accepts the frozen
entry WorldState, original source prose, v0.10 independent extracted
events, and an **application-supplied** temporal/route interpretation.
It demands:
- Exact registered, active CHARACTER and independent MOVE/WORLD source
  event; an unobserved, reported, uncertain or negative claim cannot
  establish physical travel.
- 1:1 matching source MOVE and temporal MOVEMENT IDs; same character,
  source order and original text span. Temporal source cannot add an
  unaccounted movement or silently omit a sourced movement.
- Target region already exists in trusted WorldState, and its
  canonical region name appears in the exact move source quote.
  Ambiguous aliases and inferred destinations FAIL SAFE until a
  trusted general alias registry is added.
- v0.5 temporal constraint proof for original entry revision, known
  route legs, bounded source-app world/scene windows, action ordering
  and causal/travel minimums. No synthetic arrival minute is ever
  presented as a narrative fact.
- Pure detached preview moves actor and all currently held/worn items
  together, validates resulting co-location invariants and leaves
  original world revisions and DB unchanged. Hashes bind original
  source, world, temporal case and report.

[full_scene_qualification_v023.py](./full_scene_qualification_v023.py)
now regards only successfully previewed MOVEs as having a partial
reducer; unverified MOVE, TRANSFER, LEARN_FACT, knowledge/ownership
effects and other unimplemented state families **still block**.
v0.23 continues to check unrelated fact, source, semantic and facet
defects independently. A successful preview is *not objective proof*
that the described walk truly happened, nor a canon commit grant.

## Important pure-movement scenario

A normal scene need not include a pocket watch or notebook.
[artifact_scene_checker_v021.py](./artifact_scene_checker_v021.py)
supports an entirely empty openable/document role registry when
(and only when) v0.23 full event qualification is enabled and the
independent typed model returned an empty candidate list. No phantom
object or "fake typed event" is created. The v0.20 controller and
v0.23 gate accept this *no applicable facet* contract only when
full-event qualification independently passes. An unsupported
movement still fails safe if the application has not supplied a
registered route/time source.

The [v0.22 fresh-evidence worker](./fresh_scene_evidence_worker_v022.py)
accepts an **application-owned deterministic temporal-case builder**
that receives every fresh source SHA, frozen WorldState and exact
independent extraction report. An explicit immutable
\`temporal_policy_id\` is part of its durable replay contract.
The [composed runner](./composed_scene_runner_v023.py) passes this
builder through its lab entrypoint, so a changed story revision cannot
reuse the previous temporal evidence. Neither model-generated
location/clock fields nor manual per-story editing are allowed as an
authority source.

## Evidence and limits

- [Pure spatial test suite](./tests/test_spatial_preview_v024.py):
  source-to-event-to-route binding, impossible arrival times,
  fake/reported movement, missing routes, registered destination,
  two-leg return travel, carried/worn co-location and untouched world.
- [v0.23 spatial coverage integration](./tests/test_spatial_full_scene_v024.py):
  a valid sourced movement passes noncanonical all-event gate, while
  forged MOVE, infeasible time, wrong entry revision, swapped source
  proof and unsupported route cannot pass.
- [Composed zero-billable movement-only story tests](./tests/test_spatial_worker_v024.py):
  no phantom object, source-indexed temporal policy builder,
  independent per-draft sweep, v0.23 qualifier, and durable provider
  receipts. These tests use simulated OpenRouter envelopes, NOT real
  paid provider calls.

**Not done:** automatic authenticated application route/alias policy
distribution in production, independent real-model meaning
qualification, general relocation of nested/unheld items,
cross-scene character transfer, source-to-temporal automatic
classification for every narrative, complete knowledge/ownership/
causality reducers, provider-side idempotency reconciliation for
unknown charged calls, and machine-authorized atomic production world
commits/rollback. A possible model hallucination that happens to
match a source phrase and a registered route still needs independent
semantic qualification; this gate alone does not prove world truth.

Zero mandatory human intervention. Zero application-defined model
output-token ceilings. No production database writes.

[Tracked under Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
