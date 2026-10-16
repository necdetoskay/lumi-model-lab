# SERA v0.34 — Project_LUMI read-only server integration

**Reality check:** This phase changes code ONLY in a separate
Project_LUMI development branch:
[Project_LUMI v0.34 branch](https://github.com/necdetoskay/Project_LUMI/tree/experiment/sera-g2-readonly-authority-v034-20261016).
It is NOT deployed, not merged into Project_LUMI main, not connected
to a live G2 database, and not a published StoryOutcome. A queued CI
job is not a verified passing test; always check final job conclusions.

## Implemented server source

[Internal GET-only route](https://github.com/necdetoskay/Project_LUMI/blob/experiment/sera-g2-readonly-authority-v034-20261016/apps/web/app/api/internal/sera/g2-authority-readonly/route.ts)

[Application-only scoped adapter](https://github.com/necdetoskay/Project_LUMI/blob/experiment/sera-g2-readonly-authority-v034-20261016/apps/web/lib/story/sera-g2-authority-readonly.adapter.ts)

[Isolated source service](https://github.com/necdetoskay/Project_LUMI/blob/experiment/sera-g2-readonly-authority-v034-20261016/apps/web/lib/story/sera-g2-authority-readonly.service.ts)

- Hard opt-in \`SERA_G2_READONLY_ENABLED=true\` with all
  application-owned five-key UUID scope settings, a dedicated
  minimum-length internal bearer token, separate database credential,
  signer and audience/issuer configured. Default is 404 and zero DB
  reads. No parent-session cookie or inferred user role bypass.
- The client and server now agree on proposed internal
  \`GET /api/internal/sera/g2-authority-readonly\` parameters
  \`contractId\` and fresh \`nonce\`. No POST, no redirection,
  no provider chat calls or state commits.
- Single Postgres.js transaction under
  \`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY\`.
  A separate \`SERA_G2_READONLY_DATABASE_URL\` must be supplied with
  TLS \`sslmode=verify-full\`, and the server actively rejects an
  account with any relevant G2 table DML privileges or CREATE in the
  \`story\`/\`profile\` schemas. Stronger DB/operations review and
  correct read-only grants remain a rollout prerequisite.
- Reads genuine \`story\` / \`profile\` schema table names for the
  scoped StoryContract, Intent, ACCEPTED run/artifact, original
  character snapshot ref, Universe/WorldInstance revisions and
  CharacterStoryState head. Rejects stale/mismatched heads and
  attempts to read a completed/incorrect story as precommit evidence.
- Signed server evidence uses Ed25519 PKCS8 private key, fresh nonce,
  actual DB snapshot fingerprint, scope SHA, issuer, audience, key ID,
  read-only permission, and 60-second expiry; server never returns
  private key or token. Output is limited in size before signing.
- Per-contract source contains the EXACT same v0.32
  \`sera.project-lumi-g2-readonly-binding.v0.32\` keys. The native
  G2 world and StoryArtifact fingerprints are distinct from
  detached SERA WorldState and source text SHA values.

## Safety

NO installed env/secrets, no SQL grants or migrations applied,
no actual prod DB queries, no runtime deployment or G2 outcome
writes. Only the detached experiment branch is modified.
If the app uses a broad PostgreSQL owner/superuser role, the
endpoint must reject it before reading contract details.

**Missing**: a live and *authenticated* G2 SQL read with verified
Ed25519 public key in Model Lab; real separate authoritative
physical registry for location, custody, wearable state, facts and
route costs; atomic Model Lab ↔ G2 cross-revision consistency;
signed paid-worker grant and full unseen-story qualification,
transactionally authorized G2 commit and rollback.
Mara S1 remains HOLD.

## Qualification

[Self-hosted workflow](https://github.com/necdetoskay/Project_LUMI/blob/experiment/sera-g2-readonly-authority-v034-20261016/.github/workflows/sera-v034-g2-readonly-source.yml)
exercises G2 read source and API abuse tests and \`@lumi/web\`
typecheck. The tests use in-memory synthetic SQL rows and
ephemeral Ed25519 keys, never production auth, keys or database.
A CI run only qualifies when it has a final **SUCCESS** conclusion.

The Project_LUMI side includes
[Architecture + security setup](https://github.com/necdetoskay/Project_LUMI/blob/experiment/sera-g2-readonly-authority-v034-20261016/docs/07-delivery/lumi/sera-v034-g2-readonly-authority.md).

SERA Epic: [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
