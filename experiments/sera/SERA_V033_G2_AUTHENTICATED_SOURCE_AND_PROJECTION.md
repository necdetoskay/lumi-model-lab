# SERA v0.33 — G2 Authenticated Reader and Physically Grounded World Projection

**Status:** MODEL LAB experiment. The client and pure state projection are
implemented; no Project_LUMI production endpoint, deployed service,
live G2 database read, LUMI story-worker invocation, paid OpenRouter
generation, or canonical WorldState/EventGraph commit is claimed.

## What the real Project_LUMI code already provides

Production repository (inspected read-only):
[Project_LUMI at 64fe6a7](https://github.com/necdetoskay/Project_LUMI/tree/64fe6a7201978d09ce5c3a8f38e79f05f8e7f5f0).

- \`apps/web/lib/story/g2-story-read.service.ts\` and
  \`/api/profiles/[profileId]/characters/[characterId]/stories/latest\`
  can read a *latest committed story* under the logged-in parent's
  profile entitlement. They do **not** return the full immutable
  StoryContract, accepted-production-run scope, frozen universe/world
  revisions and live character snapshot+head needed by v0.32.
- \`/api/profiles/[profileId]/characters/[characterId]/story-contracts/[contractId]/production\`
  is **POST** and calls \`completeWebG2Story\`, which can generate a
  story and commit an outcome. It is prohibited for SERA's read-only
  authority preflight.
- The native G2 truth lives in
  \`packages/story/src/db/schema/story/g2-story-contract.ts\`,
  \`g2-story-production.ts\`, and
  \`packages/profiles/src/db/schema/profile/g2/story-state.ts\`.
  The existing atomic commit service and domain fingerprints are NOT
  the same as SERA's detached simulation fingerprints.

Therefore no suitable deployed GET can be claimed to exist.

## Implemented: pinned read-only client

[The v0.33 HTTPS reader](./g2_authenticated_http_reader_v033.py) defines
a **proposed**, not currently deployed, server contract:

\`GET https://<operator-pinned-host>/api/internal/sera/g2-authority-readonly?contractId=<uuid>&nonce=<random>\`

An independent production implementation must own this endpoint
behind an application service-account authentication boundary and
must enforce the five-key StoryContract scope on the server. The
service-account token must be allowed only
\`g2.story_authority.readonly\`, not story generation, commit, or
cross-profile discovery.

The response must carry the v0.32 \`rows\` shape:
\`contract\`, \`intent\`, \`production_run\`, \`accepted_story\`,
\`universe_head\`, \`world_head\`, \`character_before\`,
\`character_head\` and \`snapshot_refs\`, all from a consistent,
server-owned read snapshot of the same Contract. It must not assemble
a falsely consistent mixed revision from unrelated read times.

Attested \`provenance\` fields:
\`source=PROJECT_LUMI_G2_READONLY\`,
\`contract_id\`, \`snapshot_id\`, \`rows_sha256\`,
\`scope_sha256\`, \`permission\`, \`nonce\`, \`issuer\`,
\`audience\`, \`key_id\`, \`issued_at\`, \`expires_at\` and
\`signature\`.

The exact signed message is the UTF-8 JSON canonicalization of:

\`\`\`json
{
  "domain": "sera-g2-authority-readonly-v033",
  "rows_sha256": "<sha256-of-rows>",
  "provenance": {"...": "all provenance fields except signature"}
}
\`\`\`

**Security requirements:**
- Operator-configured HTTPS host/path only, TLS verified, fixed GET
  and no redirects, no arbitrary user-supplied URL or IP/port,
  no server-side configuration changes from SERA.
- Per-read single-use unpredictable nonce, issuer/audience/key-ID
  pinning, exact requested five-key scope hash, read-only permission,
  response freshness and short expiry. Wrong or replayed signed
  evidence fails BEFORE v0.32 structural tests.
- A REAL source must sign with a separately managed private key and
  SERA must verify against a **pinned asymmetric public key**. The
  adapter takes an application \`verify_signature\` callback; a
  permissive callback does not establish authenticity. The test
  suite uses HMAC *only as a clearly synthetic substitute*, never as
  evidence of an installed production signing service.
- Credentials must come from the server-side secret manager and
  never enter model prompts, git files, stored journals or output
  logs. Do not put production parent session cookies in Model Lab.
- Authentication of a server read does NOT authorize billable model
  generation or a G2 StoryOutcome commit.

The adapter directly provides \`readonly_lookup\` and
\`verify_source\` callbacks for
[the v0.32 G2 scope bridge](./g2_readonly_scope_bridge_v032.py).
No authenticated live G2 read was made in this development pass.

## Implemented: separate physical world source

[v0.33 physical projection](./g2_physical_projection_v033.py)
proves that the native G2 CharacterStoryState \`facts\` and
\`emotions\` do NOT establish physical entity location, holder,
wear state, route access, or verified objective world facts.

A second authenticated \`PROJECT_LUMI_G2_PHYSICAL_READONLY\`
snapshot must be bound to exactly the same five-key scope,
world revision/fingerprint, character snapshot ID and v0.32 authority
digest. It must explicitly enumerate:
- Existing character, object and wearable **native IDs** and
  active lifecycle, location, holder/owner/wear relations.
- Registered real locations and routes with signed minimum travel
  time, not invented navigability.
- Separately verified knowledge IDs, with exact character isolation.
  Alleged/rumored facts cannot be promoted to objective knowledge.
- Unknown appearance, dimensions and weather remain literal
  \`UNKNOWN\`, not model-generated or inferred values.

The projector produces a detached \`sera.world-state.v0.2\` with
native registered IDs and a local simulation digest. This is
explicitly **not equal** to the native G2 world fingerprint.
Any absent physical registry, missing primary character,
unregistered location, wrong holder location, stale head or
unverified fact is a safe blocker.

## Self-hosted coverage

- [HTTPS authority reader tests](./tests/test_g2_authenticated_http_reader_v033.py):
  challenge/response nonce, signed and expired/replayed/wrong
  audience/profile/issuer/permission cases, exact G2 story source,
  denied untrusted endpoints, and a v0.32→v0.28 zero-cost preflight.
- [Physical projection tests](./tests/test_g2_physical_projection_v033.py):
  real format typed IDs with synthetic data, custody/location
  consistency, missing registered object/location/route, wrong
  CharacterState head, cross-world scope, rumor isolation,
  unsigned/tampered projection, no canonical writes.
- All transport and signatures are mocked. No live server data,
  model cost, production SQL or production access needed.

## Next exact action before claiming "real integration"

Create a **separately reviewed, isolated Project_LUMI integration
branch** for the internal GET source and physical projection, with
application-authenticated server-side actor/profile/household scope,
read-only database role, repeatable-read snapshot of G2 authority
and physical registries, short-lived asymmetric signatures, unit
and integration tests proving no generated or committed outcome,
and deployment-gated credentials/configuration. Its production
use requires explicit authorization and separate shadow traffic
acceptance. The current Model Lab client is ready for such a source
but cannot invent that endpoint's existence.

Only after the real application-signed read succeeds can SERA
further qualify a production-model worker, signed billing grant,
complete unseen story, and **independently** authorized native G2
transaction/rollback; Mara S1 remains HOLD.

No application model output token ceiling, no human story repair or
mandatory approval, no main merge, and no database writes.
[Canonical Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
