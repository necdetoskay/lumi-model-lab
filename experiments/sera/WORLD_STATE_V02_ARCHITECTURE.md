# SERA v0.2 — Persistent World / Object State (Experimental)

**2026-10-16 — ACTIVE ISOLATED DEVELOPMENT**  
**Issue:** [#303](https://github.com/necdetoskay/lumi-model-lab/issues/303)  
**Source:** original pre-Haiku Mara Spine SHA `fe1dda0047000438bbfaac69022e835bf7e0a1f8` (immutable).  
**Production readiness:** **NOT QUALIFIED**. Does **NOT** implement a Project LUMI PostgreSQL migration. This is an isolated Python + SQLite prototype with no model API calls.

## Why this exists

Narrative object continuity must be the **application's state**, not a story writer's memory. A coat worn in scene 1 must remain the same coat with the same color and physical dimensions 10 scenes later, unless an individually authorized, evidence-backed transition changes it. The system must retain an object's identity and history even when it is physically destroyed or no longer active.

## 1. Data model

Canonical schema: `sera.world-state.v0.2`, fully typed JSON serializable records:

- Stable `entity_id` and `kind = CHARACTER | OBJECT | WEARABLE`.
- `lifecycle = ACTIVE | DAMAGED | DESTROYED`; logical records never silently deleted.
- `location`, `owner`, `holder`, `worn_by`, `parent_id`: ownership **is not** the same as physical possession or clothing worn by a character.
- `appearance = {color, material, markings}`. Color is a controlled vocabulary; unknown values are stored as `UNKNOWN`, never guessed by the model.
- `dimensions = {width_cm, height_cm, depth_cm, mass_kg}`. All dimensions are normalized with units, and unknown dimensions are `null`. Physical dimension changes require application approval plus an explicit permitted world rule, even when an LLM suggests them.
- `condition = {integrity_pct, functional, age}` (NEW/USED/OLD/UNKNOWN).
- `size = XS | S | M | L | XL | UNKNOWN`. A wearable cannot be worn by an incompatible sized character.
- `traits`, `knowledge`: character-only. The character outfit and carried/owned inventory are calculated by traversing physical entity references, not duplicated into competing embedded lists.
- `regions` (weather/temperature/wind/clouds/precipitation/ground wetness/last change time). Environment is **story canon**, not a live external weather API.
- `minute`, `revision`, `scene_index` and accepted `events`.

A common `entity_template` implements the **Base Entity** concept through a typed schema plus `kind` specialization, without requiring fragile database inheritance. A future adapter may use dataclasses or application-native typed objects; stored JSON schema stays explicit/versioned.

## 2. Events are the only permitted mutations

`world_state_v02.py` offers a pure `apply_event` reducer. Every event must have **exactly**:

```json
{
  "event_id": "scene1-watch-examined",
  "type": "INTERACT_ENTITY",
  "at_minute": 140,
  "reason": "Evidence-supported examination",
  "evidence_ref": "scene1#span-51-90",
  "payload": {
    "entity_id": "vane_watch",
    "actor_id": "vane",
    "interaction": "LOOK_AT"
  }
}
```

An external trusted application must provide `approvals[event_id] = sha256(canonical(event))`. The LLM is **never** given authority to generate or approve that mapping. Each operation enforces strict typed required keys (no empty dict fallback, no extra fields). Approved operations include `INTRODUCE_ENTITY`, `CHANGE_APPEARANCE`, `CHANGE_CONDITION`, `CHANGE_DIMENSION`, `MOVE_CHARACTER`, `TRANSFER_HOLDER`, `WEAR`, `REMOVE_WEAR`, `LEARN_FACT`, `UPDATE_CHARACTER_TRAIT`, `SET_WEATHER`, `RETIRE_ENTITY`, `INTERACT_ENTITY`, `ADVANCE_SCENE`. Unknown operations fail closed.

No event = no change. The reducer always starts by copying the entire accepted state. An unchanged pencil, coat, station clock or weather record continues into every subsequent snapshot. A character moving carries worn and held objects along. An attempted physically impossible route is rejected. A destroyed entity is never deleted from the registry.

**Caveats:**
- `at_minute` is required for these authoritative transitions. Natural-language scenes still need v0.2 *relative-time extraction* and a time-resolving planner before the output can be accepted; invented clock times are forbidden.
- `evidence_ref` format/identity and real semantic support are **not yet cryptographically linked** to a completed JEV verdict. The reducer checks the approval fingerprint and typed/physical invariants but does NOT read prose or independently approve a semantic fact. The trusted application must grant authorization only after evidence review; current tests create controlled grants.
- Change-color and exceptional dimension/weather rules are explicit *capabilities*, not automatic plot events. Do not pass model-invented world rules into trusted `world_rules`.
- Story-time transitions here are deliberately conservative simplifications; environmental rates and clothing size are prototype contracts, not general physics.
- This remains an experimental model, not the formal LUMI World State Commit authority.

## 3. Transactional history and reconstruction

`world_store_v02.py` is an isolated standard-library SQLite event store. It stores:

- `world_streams`: current full snapshot and pinned route/world rules.
- `world_events`: immutable append-only serialized events, revision number and an event hash chain.
- `world_snapshots`: snapshots at each revision, including unchanged objects.
- `world_entity_history`: every actual entity change and each explicitly recorded non-mutating entity interaction, with `before`/`after` snapshots.
- `world_environment_history`: each weather/region change with `before`/`after` values.

Queries: `head(stream)`, `snapshot(stream, revision)`, `entity_at(stream, entity_id, revision=... | story_minute=...)`, `entity_history(stream, entity_id)`, `environment_history(stream, region_id)`, `verify_replay(stream)`, `loadout(state, character_id)`.

`commit` uses `BEGIN IMMEDIATE` atomic transactions, expected head revision (optimistic concurrency), event-ID collision protection, and all-identical batch idempotency. Rejected batches roll back entirely. SQLite triggers reject updates/deletions of immutable logs, snapshots and history. `verify_replay` independently recomputes state from pinned initial snapshot and sequenced events, checks all checkpoints and chained hashes. The hash chain detects accidental tampering **against a separately trusted anchor**; a database administrator can rewrite the whole database, so this is not a signature or adversarial tamper-proof guarantee.

Every-revision full snapshots are intentional for the prototype and simpler proofs; production scaling should use periodic checkpoints + replay, indexed history and migration/retention policies.

## 4. Safety boundaries and product integration

- No LUMI Postgres/database connection, schema change, migration or canon commit. SQLite in-memory and temporary-file tests only.
- Do not replace existing SERA v0.1 scene state reducer until offline validation, semantic proof, exact event-time resolution and independent migration/field-mapping review.
- No pre-Haiku Sonnet Spine mutation and no V4/V4.1/V4.2 code changes.
- Issue #303 tracks persistent state and future product integration. Issue #304 independently tracks model extraction to strict event contracts, relative event time and JEV verification.
- Qualify sample Mara scenes one at a time. Before any real state commit, verify the proposed event was actually **entailed** by the accepted prose and authorized by the application.

## 5. Offline tests

```bash
python -m unittest discover -s experiments/sera/tests -v
```

Cases include 10 unchanged scene transitions, persistent coat color/sizing, watch age/physical size, color change CAS and history, stopped/broken status, impossible travel, exceptional size rule, clothes worn/removed, weather timing and abrupt-temperature rejection, new objects and destroyed-object history, character knowledge/traits, SQLite reopening, append-only triggers, replay hash chain, concurrency conflict, idempotency and transaction rollback.

## 6. Future work

1. M3.1: Typed model extraction adapter to v0.2 event operations with event-level role IDs, required fields and independently corroborated evidence spans.
2. M3.2: Relative/interval story time that never forces models to hallucinate absolute event timestamps.
3. M3.3: Provenance-binding of `evidence_ref` to exact text SHA/offsets and judge verdict; application-owned acceptance gate.
4. M3.4: Richer ontology (nested containers, clothing layers, anatomical dimensions, material-specific transitions, damaged vs destroyed physical affordances, multiple locations/regions, multi-chapter replay).
5. M4: First Mara scene accepted snapshot after independent gold assessment; then nine-scene transfer demonstration, not before.
6. Product adoption: field mappings, PostgreSQL migration, world state lock/concurrency, permissions, security review and EOS stabilization, as a **separate approval-gated project**.
