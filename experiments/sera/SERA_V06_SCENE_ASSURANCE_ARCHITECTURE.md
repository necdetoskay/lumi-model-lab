# SERA v0.6 — Evidence-Led Scene Assurance

**Status:** ACTIVE ISOLATED PROTOTYPE, **NOT A RELEASE / NOT CANON ACCEPTED**  
**Date:** 2026-10-16  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Related:** [#303](https://github.com/necdetoskay/lumi-model-lab/issues/303) Object State, [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304) typed events & extraction, [#305](https://github.com/necdetoskay/lumi-model-lab/issues/305) EventGraph  
**Immutable source:** original Sonnet Mara Spine Git blob `fe1dda0047000438bbfaac69022e835bf7e0a1f8`, frozen live S1 prose SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`.

## Decision from three external architecture reviews

Preserve deterministic state reducer, EventGraph and immutable evidence.
**Stop increasing graph/reducer complexity until extraction coverage is measurable.**
Shift the verification unit from *only the events the model reported* to
**every sentence in the source**, with independent entity/physical-change
hints, scene intent alignment and explicit evidence provenance.

This delivers **structural accountability**, not perfect semantic recall.
Even a ledger disposition for every sentence may misclassify a meaningful
action as texture. No source or model provides a theoretical 100% recall proof.

## New modules and roles

| File | Function | Canonical state permissions |
|---|---|---|
| `sentence_ledger_v06.py` | Exact sentence span partition, candidate lexical scanning, action/time/pronoun cues, one disposition per sentence, exact event evidence link checks | **None** |
| `scene_contract_v06.py` | Before-the-writer EventIntents, tracked refs, texture freedom, separate MATCHED/MISSING/CONTRADICTED/UNCERTAIN alignment | **None** |
| `scene_assurance_v06.py` | ONE offline entrypoint composing new scans, sentence ledger, plan-diff, existing M2 `reconcile()`, bounded repair suggestions | **None** |
| `observation_archive_v06.py` | Isolated SQLite append-only store for noncanonical T2 sightings, source quotes, sentence position, HOLD inspection | **Only advisory SQLite** |
| `aspect_epistemic_v06.py` | Registered typed aspect change proposals; attributed proposition/stance records, no truth promotion by assertion | **None** |
| `mara_s1_v06_audit.py` | Frozen real first-scene advisory CLI + regression baseline | **None** |
| `tests/test_scene_assurance_v06.py` | Cross-component positive/negative tests | **None** |

## 1. Sentence ledger contract

1. Split the **exact** prose into ordered, non-overlapping, source-bound
   sentences `s001 ... sN`; no nonwhitespace text may be left unpartitioned.
   Preserve codepoint `start/end/quote`, source hash, original dialogue
   quotation. Splitting is conservative heuristic and can be improved with
   calibrated segmenters for other languages.
2. For every sentence a reviewer returns **exactly one** disposition:
   `STATE_EVENT`, `KNOWLEDGE_EVENT`, `CLAIM_ONLY`,
   `NO_TRACKED_CHANGE`, `TEXTURE` or `AMBIGUOUS`.
3. An event-bearing sentence must reference actual `event_id`(s), and every
   referenced event must have a matching exact quote/offset inside that
   source sentence. Orphan event or duplicate sentence ID => deterministic
   failure. Every lexical candidate tied to a sentence must be accounted
   for in the sentence row.
4. `NO_TRACKED_CHANGE`/`TEXTURE` with significant action/claim cues or
   T2 entity presence => explicit review finding, not silent PASS.
5. Until independent semantic review, every sentence starts `AMBIGUOUS`;
   construction of a complete ledger does **not** mean completeness was
   semantically checked.

This closes the "extractor returned no record for the sentence at all"
*structural* loophole. It does not guarantee a reviewer will see every
implicit/subtle state change within a reviewed sentence.

## 2. Candidate scanner and T0/T1/T2 memory

- T0: existing canonical characters/major tracked objects. Existing
  `world_state_v02` and `world_store_v02` continue to own their state.
- T1: tracked physical interacting/held/worn items. There is no automatic
  promotion in v0.6. Authorized promotion must be a separately reviewed
  event with provenance.
- T2: observed candidate noun **sightings**; exact quote, source offsets,
  sentence ID and `UNDETERMINED` physical presence. No guessed color,
  owner, dimension, identity, or physical manifestation. T2 evidence can be
  persisted in an **isolated** append-only `ObservationArchive` without
  writing the canonical WorldStore.

Scanner uses existing SERA candidate lexicon, registered aliases, simple
pronouns, time expressions and localized action cues. Compound registered
aliases protect against spuriously adding the noun inside them as a new
entity (`platform clock` should not create a second unknown `clock`).

Words in a **document or a character's dialogue** can refer to a train
without demonstrating the train was physically present. Occurrence is only
an evidence candidate. `02:07` is a time expression, **not** proof the
observation/action happened at that clock minute.

**Not solved:** open-world noun phrases not in lexicon, metaphor, complex
coreference and multilingual morphology; lexical scans alone cannot certify
full coverage. Gold labels and blind probes remain necessary.

## 3. Scene Contract and prose alignment

A `SceneContract` is prepared from an approved Spine beat and the current
accepted World State **before the Writer writes**. It lists tracked
entities, optional `EventIntent` entries, whether an intent must appear in
prose, epistemic scope and literary texture freedom.

When the Writer returns prose, an external aligner should provide evidence
spans for each intent:
- MATCHED with exact evidence = structurally grounded candidate, **not
  semantically proven**.
- MISSING required intent => HOLD; do not apply planned event to state.
- CONTRADICTED / UNCERTAIN => targeted human/JEV question.
- Unplanned state-bearing action => HOLD for separate assessment, not
  automatic acceptance or rejection.

The v0.6 Python API validates the supplied alignment's structural evidence;
it does not presently run an LLM aligner and does not assert the semantic
MATCHED label is true.

## 4. Typed aspects + claims

Aspect proposals `openable.case_open` and `writable.entries` address
current Mara gaps without allowing arbitrary dynamic keys. The module
validates type, controlled operation and quote reference, but **does not
change the v0.2 physical reducer** yet. `mechanical.functional` is also
registered as a proposal example.

Proposition records distinguish originating **DIALOGUE, DOCUMENT,
DIRECT_OBSERVATION, NARRATOR, THOUGHT**. Character stance is HEARD,
OBSERVED, BELIEVES, DOUBTS, DENIES or KNOWS_CLAIM_EXISTS. A document or
dialogue claim cannot mark itself `VERIFIED`. Proposal and stance records
have no production approval token.

Proper future implementation requires trusted objective-truth determination,
state reducer event additions, compatibility mapping and proof-bound commit.

## 5. Bounded repair router, not silent invention

`scene_assurance_v06.repair_routes()` classifies findings:
- ambiguous sentence => focused sentence review;
- planned event missing => probe first, then Writer patch if warranted;
- unknown observed object => candidate check and possible formal introduction;
- unplanned state change => targeted plan/prose compatibility review;
- unsupported aspect => schema review, not arbitrary property insertion.

After two report repair rounds the suggested route becomes human escalation.
This is **a number of attempts, not a model output-token ceiling**.
No paid models are called and no automatic prose edits/reducer writes happen
in v0.6.

## 6. Real Mara S1 measurement (read-only)

Run:

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.mara_s1_v06_audit
```

CI [SERA State Engine Offline Tests](https://github.com/necdetoskay/lumi-model-lab/actions/workflows/sera-state-engine-tests.yml)
asserts:
- exact frozen 243-word source hash;
- **28/28 sentence spans covered**, all starting **unreviewed/HOLD**;
- both **bench** and **pencil** appear in T2 candidate sightings;
- **watch-case closure** and **notebook writing** appear as review cues;
- prior nine analyst-curated event candidates remain **9 HOLD**;
- **0** new model calls, **0** canonical state writes, no automatic truth
  promotion or live event approval.

The `28/28` number means **structural partition completeness** on one
specific English source, NOT entity/event recall or narrative correctness.
This corpus is **not human-adjudicated gold**.

## 7. Acceptance and next handoff

Implemented and regression-tested:
- every sentence receives a review slot and exact source span;
- no orphan event evidence accepted;
- independent T2 bank/pencil observation candidates retained;
- plan omission and plan-external deltas routed to HOLD;
- controlled aspect and epistemic proposals without direct world truth;
- isolated append-only SQLite T2 memory and bounded repair routes;
- existing SERA v0.1-v0.5 tests, no-output-token-cap policy and Spine
  baseline continue through CI.

Remaining:
1. Human-adjudicate Mara S1 entity/event/cue gold to measure recall,
   precision and semantic false-PASS.
2. Feed **independent** compact sentence-level model/reviewer dispositions
   into the ledger; detect unaccounted physical/knowledge changes; no
   fixed output token limits in outgoing model API payloads.
3. Calibrate targeted probes and actual model costs before claiming
   improvement in extraction reliability.
4. Extend reducer and EventGraph with approved typed aspect and knowledge
   transitions plus document write effects.
5. Add server-authenticated provenance-bound approval gate and qualified
   first true Mara S1 exit World State; then continue to scene 2.
6. Production PostgreSQL adapter, snapshot optimization and release
   approval are separate projects.

Never treat passing offline unit tests, T2 sighting retention, or a single
model/judge PASS as a sufficient event commit authorization.
