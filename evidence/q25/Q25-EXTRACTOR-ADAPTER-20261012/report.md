# Q25 — Provider-neutral extractor boundary offline qualification

**Result:** ENGINEERING REPLAY PASS / NOT A SEMANTIC EXTRACTION QUALIFICATION
**Date:** 2026-10-12
**Source commit:** `457657ef637fb94a2c6ce87c7d76303cae07275b`
**PR:** #273 (Draft; no merge)

## Scope of implemented stage

A transport-free input compiler and an untrusted response materializer were
added as `src/q25_extractor_adapter.py`. Input: immutable seed + exact
story text. Output request: immutable seed, actor/object/location/goal and
obligation constraints, source/seed SHA256, Pydantic JSON Schema and
verbatim prose.

A response uses a fixed, provider-neutral `q25.extractor-raw-output.v1`
envelope. It contains proposed ordinary objects and object relations,
character changes, goal/obligation/thread outcomes and existing scalar
object property changes, with exact quote strings. Character offsets are
computed from the frozen story by the application; repeated quotes require
exact left/right context that selects precisely one occurrence. Bad hashes,
ambiguous/absent quotes, schema additions, unrecognized actors and
unapproved structural/property claims fail closed.

An `offline_replay` call materializes the exact quotes, runs structural
admission, and then reuses the Q25 character, property and coverage
validators. `BLOCKED_BY_POLICY` never produces a draft or coverage.
Even a successful replay returns only
`SOURCE_BOUND_CANDIDATES_ONLY`; semantic and persistence authority
always stay false.

## Replayed cases

- **Q24:** `evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json`
  is a translation of **previous offline Codex annotations** into an
  untrusted model-shaped reply. It is not a new model extraction.
  Deterministic materialization matches the earlier proposal claims.
  Coverage still flags 70 fields: 12 candidate, 1 partial candidate,
  23 structural only, 32 unassessed, 2 unknown. This is not 70 errors.
- **Synthetic second story:** character Ela and marker/new reading book,
  separate objective, obligation and thread. The same generic adapter
  passes without Q24-specific names. This tests only structural
  generality, not semantic extraction accuracy.
- **Adversarial:** incorrect binding, non-source citation, shuffled
  whitespace, repeated quote without disambiguating context, invented
  actor/goal/object clue/property, unauthorized relations and
  `state_commit_authorized` injection are rejected. Even exact quotes
  cannot certify the proposed meaning.
- **Read-only replay:** CLI output equals pure Python replay; original
  archived source hashes are unchanged.

## Test verification

Real GitHub Actions **#38235452237**, conclusion **SUCCESS**,
`134 passed in 1.52s` at commit `457657ef`.
Workflow: https://github.com/necdetoskay/lumi-model-lab/actions/runs/38235452237

The self-hosted `q25-offline` runner runs with a separate unprivileged
Linux account, no Docker/sudo group, and private-network restrictions.
CI workflow is PR-only (plus manual workflow_dispatch) with
`contents: read` and 5-minute job timeout, avoiding the former
duplicated push/PR workload.

Source SHA256 at this qualification:
- `src/q25_extractor_adapter.py`:
  `ff3579c87b31fc6a746772bb163b634fbea0953e140175884c767147ff06b249`
- `tests/test_q25_extractor_adapter.py`:
  `d6eb1df3a1e5e43779a46e6acfe6fc24a6d47198c6a57d95c98e037e4a322e3a`
- `evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json`:
  `44c9e2134482d1bfe24541c6038fbb084ee887643a3f1ac6a29a59b3d71a8e92`
- `.github/workflows/q25-offline-diagnostic.yml`:
  `51dfb82774ab03042214ff85034fd6aa5681f789258315bf0dbcd6bdfc63b75a`

No model/provider calls were executed. Incremental model API cost:
**$0**. No production deployment, code merge, canonical StoryState
commit, historical Q24 verdict change, revision assignment or
story-quality acceptance.

## Decision

**PROCEED WITH EXPLICITLY SCOPED BACKEND INTEGRATION DESIGN, NOT PAID
DISPATCH OR PRODUCTION PROMOTION.** Provider transport, raw
token/cost ledger and independently evaluated semantic extraction
remain outstanding. A future paid call requires separately authorized
model, immutable prompt fingerprint, call-count and USD ceilings.
