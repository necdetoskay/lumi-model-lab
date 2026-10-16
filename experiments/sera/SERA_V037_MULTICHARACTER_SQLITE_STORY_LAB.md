# SERA v0.37 — Multi-character SQLite story world

**LAB ONLY — NONCANONICAL.** The SQLite world contains expressly synthetic fixture truth. It is not a real Project_LUMI physical G2 source, a live signed authority or a story outcome publisher.

## Existing engine reused

SERA already has SQLite WorldStore v0.2: immutable world snapshots, event hash-chain, entity history, CAS revision fencing, replay, and transactional rollback. No second physical state engine is introduced. v0.37 adds lab-only identity, character membership, story-run tracking and event/run ownership metadata using the SAME SQLite file/connection.

World-scoped entities allow N simultaneous CHARACTERS and N OBJECT/WEARABLE records. One G2-shaped profile owns each synthetic world, which can host multiple characters. Same character ID can be used in an isolated separate world without leaking physical state. Actors have distinct knowledge and traits.

The model-facing story context reveals **only the focal character's private traits/knowledge**, plus basic physical state of co-located entities. It never includes other characters' private facts or traits. The separate validator-only world contains all actors for collision, custody and temporal checks and MUST NOT be exposed to writer model prompts.

Existing WorldStore's seed operation now takes optional on_stream_created callback, which stores scenario metadata, initial world snapshot, travel constraints and character membership in ONE SQLite transaction; rollback leaves zero partial world rows. Existing APIs are backward compatible.

## Fixture schema

Fixture: experiments/sera/fixtures/multi_character_story_v037.json

- Synthetic scope: scenario_id, world_id, household_id, universe_id, profile_id.
- Locations: registered room/area IDs; unmeasured weather UNKNOWN.
- Characters: id, profile_id, name, location_id, private knowledge and traits, optional Origin/Saga reference markers.
- Objects: id, kind OBJECT or WEARABLE, location_id, owner_id, holder_id, worn_by_id.
- Directed routes: from_id, to_id, positive minimum travel minutes.

Example seeded world: Mara and Elin in a workshop, robot Rho in a hallway; pocket watch held by Mara, notebook/pencil nearby, wearable on Rho, private knowledge specific to each character and registered routes.

Metadata: lab_worlds, lab_characters, lab_runs and lab_run_events. Physical state remains in existing world_streams, world_snapshots, world_events and history. Story run event attribution joins the WorldStore event transaction. Rejected event batches never partially commit; exact replay is idempotent and different runs cannot claim another run's event ID.

A writer/validator handoff is provided by scene_inputs(run_id, expected_revision), whose result separates writer_context and validator_world. It does NOT yet assert a full actual StoryForge model generation, and does NOT itself authorize any model-inferred event. commit_story_fixture requires an external test-fixture exact fingerprint approval: never a model assertion and never a real G2 grant.

Run kinds STORY, ORIGIN, SAGA are reserved structurally, and characters have optional origin_fixture_ref and saga_fixture_ref fields. **Only STORY is executable in v0.37**. Actual Origin/Saga and unplaced character candidate onboarding are future-scoped, not silently implemented.

## Acceptance tests

The deterministic test suite covers multi-character private knowledge separation, source-separated writer/validator inputs, item transfer and movement together with holder, persistent SQLite close/reopen, CAS conflict, duplicate event ID ownership, atomic multi-event rollback, rejected impossible route/custody, distinct worlds sharing character IDs, noncanonical outputs, and atomic seed rollback under injected failure.

No real G2 DB calls, secrets, Project_LUMI server modifications, production or canon writes, paid model calls, manual story gates, migrations, main merges or application-defined model output-token ceilings. Frozen actual Mara S1 remains HOLD.

## Subsequent scoped work

Connect scene_inputs to the existing synthetic StoryForge/independent assurance pipeline for real scene handoff; add fixture variations and automated fault injection. Actual independent signed physical source and transactional native G2 publishing remain production gates. Later create separate unplaced character candidates for Origin/Saga without misrepresenting pre-creation characters as world residents.

Epic: https://github.com/necdetoskay/lumi-model-lab/issues/306
