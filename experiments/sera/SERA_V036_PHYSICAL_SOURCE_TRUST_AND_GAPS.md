# SERA v0.36 — pinned physical source and native evidence gap

**LAB ONLY / SHADOW ONLY.** A signed G2 StoryContract is not proof of physical position, custody, verified knowledge, or event occurrence. A signature does not authorize canonical mutation.

## Implemented

The new Python module **g2_physical_pinned_reader_v036.py** requires an independently provisioned Ed25519 public-key PEM, RAW-public-key SHA-256 fingerprint and key ID. It checks issuer, audience, permission g2.physical_registry.readonly, challenge nonce, source snapshot digest, G2 authority digest, snapshot UUID, expiry <=60 seconds, real signature and one-use replay callback. It then reuses the v0.33 strict physical projector, which still returns a detached NONCANONICAL world preview and never a G2 write request.

The **test_g2_physical_pinned_reader_v036.py** suite uses real ephemeral Ed25519 signing (not HMAC) and checks tampering, scope substitution, replay, expired evidence, missing trusted nonce store, wrong custody/location, invalid key pin and strict no-commit output. The nonce callback here is an **in-memory test double**, not durable production proof. The source is NOT a deployed GET. No billing, production SQL, secrets, mutation, migration, model call or output token ceiling is added.

## Native G2 evidence inventory — inspected repository schemas only

| Source | What the schema establishes | What it does NOT establish |
| --- | --- | --- |
| Universe nodes and edges (packages/world/migrations/g2/0001_living_universe_foundation.sql) | Registered graph nodes, edges, lifecycle and revisions | Current character position, object possession, measured travel time |
| World instance anchor_node_id (same migration) | World anchor node | Character current location |
| Character world membership | Character is associated with a world | Where the character currently stands |
| Character location knowledge (packages/world/migrations/g2/0002_local_play_map.sql) | RUMORED, DISCOVERED or EXPLORED location knowledge | Verified objective position or occupancy |
| Character route knowledge (same migration) | A route is known to a character | Real navigability and minimum duration |
| Character story snapshots (packages/profiles/src/db/schema/profile/g2/story-state.ts) | Versioned experiences, emotions, goals and general facts | Typed object holder/wearer/current location or independent event occurrence |
| G2 accepted story, heads and snapshots (v0.34 service) | Accepted text and frozen/current read consistency | That SERA inferred actions really happened |

This inventory is source-code evidence only. It is not a live database audit, nor proof that no other application tables exist.

## Required real physical authority

A future off-by-default Project_LUMI physical GET must return **actual registered and versioned** current character location; registered objects and wearables with owner, holder, wearer, lifecycle and location; registered route direction and source-backed positive minimum travel time; facts with independent objective proof and character-specific knowledge isolation; and committed event occurrence evidence with pre/post versions and idempotency key.

The physical snapshot must match the exact five-key household/profile/universe/worldInstance/primaryCharacter scope, world revision/fingerprint and CharacterState snapshot from the separate v0.35-signed G2 authority source. All records must be sampled in a consistent read-only snapshot. Server must use an actor-scoped bearer token, dedicated SELECT-only DB role and private signing key. Model Lab pins the public key independently and atomically consumes the nonce. Missing or unregistered current position, inventory, provenance, routes or event occurrence is **NOT_AVAILABLE / INCOMPLETE** — never inferred from prose, an anchor node, location knowledge or a plan.

Do not fill unknown physical properties using a model. Weather, appearance and measured dimensions remain UNKNOWN until separately evidenced. SERA output and two agreeing models cannot manufacture a committed event occurrence. No physical registry signature or model output authorizes G2 StoryOutcome/WorldState writes.

## Independent remaining gates

1. Project_LUMI v0.34 server tests and actual CI completion — separate from Model Lab CI; no deployment or production activation implied.
2. Audit actual Project_LUMI native inventory/placement and physical event authorities, then design missing data lifecycle, versioning and mapping. This document does not authorize a migration.
3. Implement read-only, properly scoped source in its isolated Project_LUMI branch; staging-only signed GET with real physical source and durable challenge replay protection, no production DB changes.
4. Qualify full semantic/source/time evidence and a separate native transactional CAS/rollback publisher; only then consider canon release.
5. Mara S1 **HOLD** with frozen original inputs and zero world writes. No mandatory manual runtime rescue and no application model output-token ceilings.

Epic: https://github.com/necdetoskay/lumi-model-lab/issues/306
