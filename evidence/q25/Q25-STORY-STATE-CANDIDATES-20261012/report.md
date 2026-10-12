# Q25 source-bound character, goal, obligation and thread candidates

Status: EXPERIMENTAL, ANNOTATED_CANDIDATES_ONLY — NOT AN ACCEPTED FINAL STORY STATE

Date: 2026-10-12
Code/test commit verified: `8c813c11ccaf807854220540f4ace7de3ce17b6b`
Branch: `experiment/q25-narrative-memory-intent`
PR: #273

## Reused immutable inputs

- Q24 seed fingerprint: `777b2d432ad292a91d9390725d4fe03c2ad91e4d358c9e3dcc785ee0b1daeb88`
- Q24 story prose SHA256: `5c68a942aae7101ecd117e24e6c8a9495ffea58d4b55f65d0fa62ba2a83be9d4`
- Object proposal source: `evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json`
- Explicit experimental admission policy: `evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json`
- Annotated narrative proposal: `story-proposal.json`, SHA256 `930e8cb0107760fc3d05c17c6b809dba0ef6d453a5be1e95eb7bb8f750e5b974`

## New projection

- Two character change claims (observed knowledge and candidate emotion).
- Three goal achievement claims.
- Three narrative obligation satisfaction claims.
- Three open-thread resolution claims.
- Each claim has exact contiguous story spans with immutable source-hash binding; multi-span claims preserve a unique ordered citation list.
- Existing objects, initial character state, world, topology and seed obligations remain unchanged.
- Every accepted admission draft is independently recomputed from frozen seed/prose/entity proposal/policy before adding claims; forged objects, identities, knowledge and world/topology are rejected.
- No automatic interpretation of unchanged `found=false` as terminal fact.
- Independent semantic support **NOT CERTIFIED**; both candidate validity and role labels still need independent assessment. No semantic gold labels or verified story acceptance.

## Verification

Executed on the separate, non-production Python virtual environment of the `ci-runner` host:
```sh
python -m pytest -q tests/test_q25_offline_diagnostic.py tests/test_q25_frozen_baseline.py tests/test_q25_entity_candidates.py tests/test_q25_entity_frozen_case.py tests/test_q25_state_admission.py tests/test_q25_admission_frozen_case.py tests/test_q25_story_evidence.py
# 71 passed in 0.85s
```

Previously 64/65 passed under Linux; the remaining failure was a Windows-style path in frozen evidence provenance. The test normalizes separators for path lookup without modifying original archived evidence. Complete rerun of the above seven suites now PASS 71/71 at `8c813c1`.

SHA256 sources at that commit:
- `src/q25_story_evidence.py`: `7f1caaa43598158ad9106bdd55cd15b2eeece98109b92c8aae65ae20074fb1e3`
- `tests/test_q25_story_evidence.py`: `9cb820568fa3301b0ac868c3362fa92720b4b38d4244b5afe9d1d643732abbc8`
- `tests/test_q25_admission_frozen_case.py`: `85029e7706fccf1bc2afac448a2556e252ada8453440880f43db5480ef196856`
- `.github/workflows/q25-offline-diagnostic.yml`: `ba6b39b821fd32b3bc8586487fa47cb53b43f496b53e1e991d95b2d0d974f927`

GitHub Actions `Q25 Offline Diagnostic` remains QUEUED on self-hosted, not GREEN. There is no remote CI PASS claim; this is an **isolated manual test execution on the CI machine**.

Actual newly dispatched model calls: **0**. Incremental model API spend: **$0**.
Production state commits, canonical promotion, merge, historical Q24 acceptance edits: **NONE**.

## Explicit gaps

This change validates a source-bound manual annotation; **automatic story-to-state extraction is not implemented**. Independent semantic support, proof of goal/obligation completion, object property extraction, episteme of character changes, full coverage and authorized canonical conversion remain unresolved. P0/P4 partial and other phases outstanding. No blanket authorisation for paid calls.
