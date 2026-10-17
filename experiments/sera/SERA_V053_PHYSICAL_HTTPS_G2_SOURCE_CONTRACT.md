# SERA v0.53 — G2 physical HTTPS read-only integration contract

**Status: CLIENT_IMPLEMENTED_OFFLINE; ACTUAL_G2_ENDPOINT_NOT_VERIFIED; REAL_WORLD_PROOF_PENDING.**

This document is a proposed read-side contract, **not** a claim that
`/api/internal/sera/g2-physical-readonly` exists on Project_LUMI.

## Why the new client exists

An accepted G2 story/CharacterStoryState is NOT a reliable source of
physical location, holder/owner, clothing or object introduction. Those
attributes need their **own application-maintained physical registry**,
attested independently of the story-producing model. The old signed
`/api/internal/sera/g2-authority-readonly` provides story authority only.

1. Resolve **G2 story authority** using the existing v0.33 authenticated
   HTTPS GET + pinned Ed25519 signature and v0.32 contract/scope/head
   validator. Never substitute a model-authored boolean
   `authenticated_source_preflight=true`.
2. Check the **ORIGINAL accepted English prose SHA** against the G2
   `accepted_english_sha256` before starting physical GET. A Writer
   revision is NOT a newly G2-accepted story: use separately proven signed
   source lineage for revisions, and do not call original-source GET.
3. GET only
   `https://<operator-pinned-host>/api/internal/sera/g2-physical-readonly?contractId=<G2_UUID>&nonce=<fresh_nonce>`
   with an operator-issued read-only bearer token, TLS CA validation, 15s
   timeout, 1.5 MB cap, redirect forbidden and JSON MIME type required.
   No `POST`, no production DB write, no fallback to prose.
4. G2 responds with `{schema, snapshot, provenance}` compatible with
   `g2_physical_projection_v033.SCHEMA`. The app must produce this from
   **one transaction-consistent physical registry snapshot**, bound to
   the G2 world revision, world fingerprint, character snapshot, contract,
   exactly the requested nonce, and short-lived permission
   `g2.physical_registry.readonly`.
5. The server signs the v0.36 canonical signature domain
   `sera-g2-physical-readonly-v036` using the **APP/infra-owned** Ed25519
   private key. Never place a private signing key in an LLM prompt, model
   response, SERA code, CI artifacts or story metadata. The SERA client
   must get the independently protected public-key fingerprint, `key_id`,
   `issuer`, `audience` and read bearer from trusted deployment config.
6. `project_pinned_physical` verifies issuer/audience, signature and
   full G2 scope; `consume_nonce` must be an **atomic durable
   app-controlled one-use store**. A Python in-memory set or callback
   accepting all nonces is permitted only in offline tests, not production.
   Read-only output is a NONCANONICAL physical **ENTRY baseline**.
7. Only after the physical signature is verified can SERA build a
   `source_chronology_v052` for the signed world SHA and attach candidate
   scene events. Even then, candidate event occurrence and action clock
   remain UNVERIFIED; no WorldStore, G2, database or canonical commits.

## Failure behavior

Any missing endpoint, unauthorized GET, TLS error, mismatched accepted prose
SHA, untrusted key, stale scope, replayed nonce, missing registered physical
entity, fabricated custody chain or broken source span **fails closed before
any provider billable POST**. It MUST NOT create an alternative fake physical
registry, forge evidence, accept signed authority from an unrelated story or
ask a human to edit model output during story execution.

The read-only app endpoint and operator-owned trust provisioning are
**not** deployed/proved by these offline CI tests. LIVE testing and
deployment are separate release gates.

## Test evidence

- `test_g2_physical_authenticated_http_v053.py`: synthetic signed HTTP
  GET, original accepted prose SHA, foreign Mara story rejection before
  network, fake nonce/signature/snapshot, unpinned HTTPS endpoints, exact
  one-time nonce, unavailable source.
- `test_signed_physical_reconciliation_v053.py`: signed physical baseline
  owner/holder/location/route, epistemic false-positive rejection,
  unknown identity, unrelated world/SHA rejection.
- Self-hosted CI uses discovery guards and no real network/provider calls.
  The raw signed fixtures are TEST-ONLY and prove neither G2 availability
  nor the correctness of Mara's 28-sentence physical events.

## v0.53 local physical nonce consumption implementation (offline)

`g2_physical_nonce_store_v053.py` supplies `LocalPhysicalNonceStore.consume`
for the `consume_nonce` callback. It uses a protected, **pre-provisioned**
SQLite file and `BEGIN IMMEDIATE` plus a UNIQUE nonce primary key.
A story worker cannot silently recreate a lost file; file identity and
protected parent/directory permissions are validated. Concurrent same-host
workers compete for the same nonce and **exactly one wins**. This is
**security metadata only**; it never updates G2 WorldState, story events or
canonical data.

Provisioning this file is a separate deployment owner/infra step. The
app-private nonce store MUST be durable across restarts and MUST NOT be
mounted on NFS or shared across uncoordinated hosts. The true G2 endpoint,
public signer pin, real read-only service credentials and authoritative
physical registry still must be independently provisioned and verified.
The mock CI test key never authorizes real G2 state.
