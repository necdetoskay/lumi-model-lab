# Q25 — Provider-neutral evidence extraction boundary V1

Status: **EXPERIMENTAL / OFFLINE REPLAY ONLY**
Date: 2026-10-12
PR: #273
State authority: **NONE** — this module cannot accept a final StoryState.

## Goal and explicit limitation

Build the *next boundary* needed for model-driven automatic state extraction
without privileging model output as truth. A future model can return **typed,
untrusted candidate proposals**, backed by exact quotations. An application
then assigns offsets and identities and runs the already established Q25 gates.

**Implemented today:** deterministic compilation of the extraction request;
a vendor-neutral Pydantic JSON Schema; strict parsing of untrusted model-style
responses; character-offset citation materialization (including safe
disambiguation of repeated quotes); existing entity admission, narrative
claims, object property checks and complete coverage replay.

**Not implemented:** a provider transport, automatic semantic interpretation,
independent semantic reviewer, adjudication of contradictions, generation of
additional entities/locations/decisive clues, accepted terminal StoryState,
or canonical state writes. The saved Q24 raw output was transformed from
prior offline annotations — **not generated automatically by an LLM**.
A second synthetic story validates generic identities and schema behavior,
not actual extraction accuracy.

## Trust/authority separation

```text
IMMUTABLE SEED + FROZEN PROSE
  └─ build_extraction_request()  # no model call
       ├─ original seed + source fingerprints
       ├─ immutable seed/allowed existing actor, object, location IDs
       ├─ known goals, open threads and narrative obligations
       ├─ exact response JSON Schema / guidance
       └─ original prose (untrusted text)

EXTERNAL BACKEND [not implemented; explicit authorization needed]
  └─ q25.extractor-raw-output.v1  # untrusted suggestions + literal quotes
       └─ materialize_quotes()
            ├─ exact SHA binding
            ├─ strict no-extra-fields contract
            ├─ exact contiguous quotes in source
            ├─ one unique location or exact surrounding context
            └─ deterministic source-character offsets
                 └─ build_draft (entity candidate graph and policy)
                      ├─ BLOCKED_BY_POLICY → STOP, no coverage/commit
                      └─ eligible draft
                           ├─ character/goal/obligation/thread claim gate
                           ├─ terminal property candidate gate
                           └─ q25.story-state-coverage.v1
                                → INCOMPLETE, no semantic certification
```

The client of this boundary MUST NOT treat a returned structurally valid
candidate as a semantic certification. The original story's narrative
acceptance is unchanged; legacy Q24 rejection is not overwritten.

## Quote resolution

A backend supplies a `quote` (8–1200 Unicode characters) and optionally
an exact `context_before`/`context_after` (1–240 characters). The
application searches the frozen source string. Exactly one occurrence
must match the quote and any supplied context. If zero or multiple:
**fail closed**. No fuzzy search, whitespace repair, paraphrase matching,
model-authored offsets or first-match fallback is permitted. Span indexes
use Python Unicode character positions; do not confuse with UTF-8 byte
offsets. Every terminal claim goes through the existing proposal validator.

A quote is only textual support. It **does not establish** that the
claim's meaning is warranted (e.g. "she read the book" does not prove
ownership; "I am sure" does not prove knowledge; apology is not proof
of restored trust).

## Offline CLI (no provider keys)

Compile a deterministic request containing the original Q24 seed/prose:

```bash
python -m src.q25_extractor_adapter \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json
```

Replay *previously saved*, untrusted model-shaped annotation without an
API call or artifact write:

```bash
python -m src.q25_extractor_adapter \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --raw-response evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json
```

Everything prints JSON to stdout. Source artifacts and seed are not
modified; the CLI does not contact any external service.

## Policy and safety invariants

- Strict `extra=forbid` rejects invented authority fields in model JSON.
- Every response binds *both* the immutable seed fingerprint and full
  frozen prose SHA256. Invalid bindings fail closed.
- Role or semantic classification remains unverified; new
  `DECISIVE_CLUE` suggestions are rejected by ordinary-object policy.
- The normal object admission policy defaults to **DENY**; an explicit
  `EXPERIMENTAL_DRAFT_ONLY` policy can enable ordinary candidates.
- Unknown owners/locations are preserved or blocked, not invented.
- Schema type confusion, bad citations, duplicate/conflicting
  relations, invented actors/goals/properties, topology expansion and
  claim injection are rejected in downstream validators.
- Q25 only accepts claim **candidates**, never final canonical values.
- No rewriting, retry loop, production dispatch, hidden merge or revision
  number is included.
- The offline replay reports `provider_calls=0`; it does **not**
  represent a live backend invocation.

## Next bounded implementation

1. Add **one** explicit backend adapter through a transport interface,
   disabled by default. A caller must first authorize a named model,
   count ceiling, USD ceiling and immutable test input. Do not
   silently migrate to another provider or reopen prior paid grants.
2. Save raw prompt/response, model ID, prompt version, source SHA,
   seed SHA, stage ledger (tokens, actual USD, latency), and errors,
   as immutable evidence in a future scoped test.
3. Independently score *semantic* citation relevance and epistemic
   status, plus completeness for object terminal properties,
   character knowledge/relationships/goals, narrative obligations,
   time and inferred locations. Evidence precision alone is not enough.
4. Run synthetic negatives and at least Q22/Q24 saved fixtures, then a
   genuinely **new unseen story** with blinded human adjudication.
5. Only a separate typed authority gate can propose canonical state.
   Promotion must be explicitly requested and is NOT part of Q25 V1.

## Result classification

`SOURCE_BOUND_CANDIDATES_ONLY`:
passes typed + source + structural validations, not semantic verification.

`BLOCKED_BY_POLICY`:
ordinary object admission denied; no draft/coverage returned.

Exceptions:
invalid quote/shape/reference/seed binding or other fail-closed errors.

No branch promotion, production write, model dispatch or story acceptance
is authorized by these statuses.
