# SERA v0.35 — Project_LUMI Node Ed25519 → Python Trusted Reader

**Boundary: LAB / NONCANONICAL.** The v0.34 Project_LUMI branch provides a proposed off-by-default, GET-only G2 source. It has NOT been deployed or read from a live G2 SQL database; server CI remains separately gated. v0.35 adds the real cryptographic verifier that the v0.33 client had only specified as an abstract injected callback. There is no new provider cost, secret, model call, DB write, migration, manual review, token output ceiling or story commit.

## What is now implemented

- [Pinned key verifier](./g2_ed25519_pinned_reader_v035.py): uses Python \`cryptography\` Ed25519 public-key verification of the **64-byte Ed25519 signature emitted as standard base64** by v0.34 Node \`crypto.sign(null, …)\`. The verifier rejects RSA, private-key PEM, malformed base64, invalid signature, wrong key ID, SHA-256 fingerprint mismatch and caller attempts to override \`verify_signature\`.
- Independently configured **pinned PEM**, 32-byte RAW Ed25519 public key SHA-256 hex and key ID are all required. Never retrieve trust material from the G2 JSON document, a model response or the live HTTP endpoint. The private key exists **only on the Project_LUMI server** and is never imported by the SERA reader.
- \`create_pinned_reader\` delegates signed-message generation, HTTPS transport rules, scope, issuer/audience, challenge nonce, expiry and replay guard to [v0.33](./g2_authenticated_http_reader_v033.py). It returns \`readonly_lookup, verify_source\` for [v0.32](./g2_readonly_scope_bridge_v032.py). A valid signature authorizes **only** an independently scoped source read, NOT story generation or world mutations.
- Real **cross-runtime cryptographic interoperability** test: Python creates an ephemeral Ed25519 test pair, **Node.js** \`node:crypto.sign\` signs the same sorted JSON shape as v0.34 \`g2Canonical\`, then the Python v0.35 verifier authenticates the signed response and v0.32 checks an entire synthetic G2 StoryContract, intent, accepted artifact, frozen universe/world head, character snapshot and source. This is stronger than older HMAC-only fixture verification. The test also checks integrity tampering, scope/issuer/permission substitution, malicious key override, invalid algorithms/PEM, bad signatures and one-use read.
- CI installs an explicitly pinned \`cryptography==46.0.4\` on the **self-hosted Linux** offline SERA test job before running Python tests; Node.js is already in the offline runner. The test never fetches source from a production app, issues a paid call or uses a production signing key.

## Unfinished production qualification — do not conflate with this proof

1. Actual Project_LUMI v0.34 server CI completion, real Postgres SELECT-only role and TLS verification; the off-by-default endpoint has no production enablement.
2. An actual authenticated round trip from SERA to the off-by-default service in an **isolated staging environment**, with safely distributed pinned public key/ID/fingerprint and server-scoped secrets. No production secrets in Model Lab.
3. Separate authenticated physical world registry for location, custody, weather, routes, objective facts and independently qualified entity/state transitions. G2 facts/emotions are not equivalent to physical truth.
4. Paid worker/model resolver replay and strict aggregate spend authority, provider-side uncertain-generation-ID reconciliation, complete unseen-story tests, then isolated authenticated machine-only G2 transactional publication with conflict fencing/rollback.
5. Mara S1 remains **HOLD** until the full provenance, temporal, world and completion gates qualify.

No application-defined model output-token ceilings; no mandatory human workflow, main-branch merge, live G2 connection or canonical world writes were introduced.

Epic [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
