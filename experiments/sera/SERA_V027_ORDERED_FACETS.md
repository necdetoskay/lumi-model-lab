# SERA v0.27 — Causally Ordered World + Openable + Document Facets

**Scope: experimental only, NONCANONICAL.** Does not change LUMI production
story worker, database, world truth, EventGraph, frozen Mara Sonnet Spine,
or output token policy. No human correction, manual review or model-granted
publishing authorization.

## Problem

v0.26 correctly replayed physical movement, holder transfer, and verified
character learning in source order through ONE changing WorldState. However,
v0.13 independently simulated opening/closing a watch or writing in a
document against the ORIGINAL entry world. A character who walked to
another region and then wrote in a notebook could therefore be marked
invalid; conversely separately approved facets could hide impossible
cross-family chronology.

## Implemented v0.27

[ordered_facet_preview_v027.py](./ordered_facet_preview_v027.py)
reuses v0.24 movement, v0.25 possession and verified-knowledge CAS and
v0.5 GLOBAL temporal DAG. It adds a shared facet ledger with **v0.13
compatible** source proof, registered object-role, active actor/object
co-location (against the **CURRENT** temporary world), baseline openable
observation, strict expected/next openable CAS and exact-word document
append CAS. The facet ledger never claims to be a production v0.13
authorization; its simulation receipts and world+facet hash lineage are
strictly noncanonical.

To enter the mixed gate, the evidence must contain:
- An independent source-complete sentence sweep with each world or facet
  action's exact original evidence span, sentence ID, effect and entity
  references; every supported facet candidate is paired exactly 1:1
  with a matching source event of a supported kind, source sentence
  and overlapping source span. No typed candidate can silently create
  a new physical act unseen by the source extractor.
- Application-registered openable/document role IDs with active typed
  WORLD entities, plus a trusted immutable route/temporal policy covering
  **every** source action in the exact order and a trusted immutable
  relation/verified-fact policy.
- Separate v0.19 risk projection, v0.20 facet source digest and v0.23
  complete-event gate. A complete source-bound model's opinion does not
  constitute semantic truth or a canon event authorization.
- Every replay step validates the detached mutable candidate state and
  records a deterministic before/after world SHA + facet SHA + source
  event ID. Original input/world revision never changes.

[v0.21 artifact checker](./artifact_scene_checker_v021.py) **defers**
the original-entry-only v0.20 facet simulation *only* when mixed
source movement + relation + typed facets are present, both trusted
per-scene policies exist, and v0.23 full qualification is required.
This is not a PASS: the [v0.23 qualifier](./full_scene_qualification_v023.py)
must actually invoke v0.27's ordered reducer. The
[v0.20 unattended controller](./unattended_scene_rewrite_v020.py)
permits READY only when v0.27 proof exists, the full gate has zero
defects, and all model/source/world/auth boundaries hold.

Failed/missing v0.27 proof still triggers automatic re-extraction/replan
and the historical CROSS_FAMILY_STATE_ORDER_UNQUALIFIED safe blocker.
Old v0.20/v0.21/v0.26 laboratory replays are retained.

## Regressions

- [Mixed seven-event replay](./tests/test_ordered_facets_v027.py):
  Vane walks to archive; Mara follows; watch changes holder;
  Mara observes watch open, closes it, writes in a registered notebook
  and learns a separately VERIFIED fact. All changes happen against
  the latest *same* isolated WorldState and facet map.
- Adversarial: wrong openable expected state, fabricated document text,
  missing or duplicated typed source event, forged actor/timeline,
  unsupported route, reported handoff, unverified fact and immutable
  frozen entry. No invented narrative time, real model call or DB write.
- [Composed mocked-provider end-to-end worker](./tests/test_composed_ordered_facets_v027.py):
  blind source sweep + separately prompted facet proposals, versioned
  evidence archive, actual v0.19/0.20/0.23/v0.24/v0.25/v0.27 recheck,
  exact request+model paid receipt cache replay, and rumor-safe stop
  using ZERO billable provider requests.

## Remaining acceptance blockers

1. The v0.27 scope is **movement + relation/knowledge + openable/document**
   in the same scene. Less common combinations (for example movement
   + facets but no holder/knowledge event) still need generalization.
2. Nested containers, all character traits/relationship/ownership
   mutations, arbitrary knowledge and rumor projection, scene-to-scene
   causality, and real independently authenticated identity/fact/route
   registries remain separate work.
3. Real LUMI production story worker and model resolver, provider-side
   request idempotency/reconciliation after a charged response is lost
   before local journaling, machine-authenticated WorldState/EventGraph
   atomic transactional commit/rollback, and unseen paid full-story
   tests including frozen Mara S1 are not implemented here.
4. SERA can validate **logical consistency of an extracted event
   interpretation**, not that the source narrative is objectively
   true, that a model's extraction is perfect, or that the WorldState
   database is authorized for commit.

No LLM output token ceiling. No obligatory human intervention. All
noncanonical outputs explicitly deny WorldState/EventGraph writes.
Follow work in [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
