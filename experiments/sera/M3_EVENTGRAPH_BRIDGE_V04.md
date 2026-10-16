# SERA M3.4 — Typed Extraction → JEV → EventGraph Advisory Bridge

**Status:** Experimental offline bridge; no real-story canon acceptance  
**Date:** 2026-10-16  
**Repository:** `necdetoskay/lumi-model-lab`  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Issues:** [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304), [#305](https://github.com/necdetoskay/lumi-model-lab/issues/305)

## Why

Our first live Mara scene (243 words) produced a valid Writer response, but:
- Haiku's first independent extraction was invalid JSON.
- Gemini extraction emitted **empty event argument dictionaries**.
- Many story actions had **no grounded absolute clock time**.
- Both writer and Gemini omitted **bench** and **pencil**.
- M2 returned HOLD and JEV returned ESCALATE; no state commit was authorized.

The bridge must never invent missing event arguments, time, object identity,
fact authority, participation or before/after state. It provides an explicit
place to reject invalid proposals and inspect compatible ones.

## Module contracts

### `typed_event_bridge_v04.py`

Consumes validated `sera.extraction.v0.1` writer/independent reports and an
immutable typed `sera.world-state.v0.2` entry.

Pilot supports only exact lossless operation mappings:

| M2 input | Typed world operation | Required model arguments |
| --- | --- | --- |
| `INTERACT_OBJECT` | `INTERACT_ENTITY` | `actor_id, object_id, interaction` |
| `MOVE_CHARACTER` | `MOVE_CHARACTER` | `character_id, to` |
| `TRANSFER_OBJECT` | `TRANSFER_HOLDER` | `object_id, from_id, to_id` |
| `LEARN_FACT` | `LEARN_FACT` | `character_id, fact_id` |
| `TELL_FACT` | `LEARN_FACT` (attributed claim reception) | `from_id, to_id, fact_id` |

`fact_id` in this pilot must start with `claim:`. For `TELL_FACT` the speaker
must already know that claim. The underlying reported claim is **not**
converted into an objective world fact. Missing or extra keys, empty dicts,
unknown object IDs, unmapped operations and unknown speaker knowledge are
returned with machine-readable `EVENT_V04_*` blockers.

An entire extraction report remains represented; *unsupported events never
silently disappear*. Exact spans remain bound to the unchanged scene prose
SHA-256 and entry revision.

### Relative time

The source `at=null` remains
`time.exact_minute=null` even if a trusted application later assigns
`resolved_world_cursor`. `resolve_time` requires an exact scene window,
matching entry revision, window hash, stable candidate ID, explicit reason
and `authority=APPLICATION`.

A cursor is only a **world simulation ordering index**, not a claim the
character performed the action at that absolute hour. Boundary and monotonic
checks reject fabricated out-of-window or backward transitions. The v0.2
reducer then independently checks travel minimums and physical invariants.
The `authority` string and source hash here are **not authentication**;
the output never grants commit permission.

### `m3_event_graph_bridge_v04.py`

Recomputes original M2 reconciliation and independently normalizes both
reports. It compares canonical reducer operation, explicit payload, epistemic
modality and time. A disagreement leaves the entire scene HOLD.

JEV's provided verdict must match the **exact recomputed claim IDs and the
original `adjudicate` result**; missing/duplicate/altered judgments fail
closed. This establishes deterministic consistency with the M3 question
bundle, not evidence that the response actually originated from JEV.
Provider identity, calibrated thresholds and review authentication require a
trusted server-side integration.

A clean, fully evidenced synthetic example reaches
`PENDING_TRUSTED_HUMAN_AND_APP_REVIEW`, **not COMMITTED**. The EventGraph
draft is intentionally extra-tagged `status=DRAFT_NOT_AUTHORIZED`,
`commit_authorized=false` and is not a valid `EventGraphStore.commit`
proposal. Draft roles are derived from trusted registered entity references,
including carried/worn equipment on character movement.

`shadow_reduce` uses the pure v0.2 reducer with an **ephemeral test-only
fingerprint** to check physical feasibility. It does not persist state,
return any approval, or prove a language model's claim is true. It rejects
impossible travel and computes effects for a possible movement with carried
objects.

## Real Mara source inspection

`mara_s1_v04_audit.py` reads only the existing analyst-curated
`fixtures/mara_s1_real_eventgraph_candidates_v03.json`. It verifies the
original 243-word prose SHA-256
`80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`,
all nine event quote spans and their status. Its result:

- **9/9 candidate events HOLD**, 0 graph commits.
- Physically unregistered noun candidates **new:bench** and **new:pencil**.
- **train_41** is referenced as a topic; this is **not evidence of physical
  presence** and does not authorize entity creation.
- Clock time of an action is not grounded by a document's 02:10 or a watch's
  02:07 reading.
- Real scene M2 HOLD and M3 JEV ESCALATE remain intact; no semantic result
  is overwritten.

This is a **read-only audit of human-inspected annotations**, not a new live
model extraction benchmark, not independent gold qualification and not a
successful EventGraph acceptance.

## Offline tests

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.mara_s1_v04_audit
```

No paid requests, no LUMI production DB connection and no modifications to
the original Sonnet pre-Haiku Spine. Tests include empty argument dictionaries,
invalid keys and actors, unsafe fact IDs, reported claim attribution,
unregistered objects, mixed writer/extractor reports, exact JEV question
binding, clock-time conflict, relative time, object double omission and
noncommittable physical shadow effects.

## Open blockers — NOT implemented as a production feature

1. Provider-bound verifiable evidence receipts, validated golden
   annotations and a real extractor/JEV-to-application review capability.
2. Typed `RECORD_FACT`, object case open/close, rich object documents and
   physical entity discovery/registration for the real Mara scene.
3. Fully general temporal partial-order constraints and grounded schedule
   resolution, including multi-scene transfer.
4. Real-scene **accepted** end state and complete event coverage qualification;
   until then no automatic story commit or nine-scene production run.
5. Production/PostgreSQL persistence, security permissions and EOS
   stabilization are a separate approval-gated undertaking.

**Status labels must be interpreted literally. Passing offline tests proves
only deterministic implementation behavior on test inputs, not that live
narrative extraction is correct or complete.**
