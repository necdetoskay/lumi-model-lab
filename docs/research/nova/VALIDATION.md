# NOVA pilot validation — 2026-10-14

**Engineering PASS; narrative benefit NOT ESTABLISHED.**

| Check | Observed result |
|---|---|
| Syntax, whitespace and dependency-boundary lint | PASS |
| Source/archive/release/schema integrity | PASS |
| Unit/integration/adversarial suite, Windows Python 3.14 | **94 tests PASS**, no skips; 54 inherited + 40 NOVA; final local run 37.168 seconds |
| Original Atlantis completeness validator | 100/100 PASS, no issues |
| Exact and thresholded lexical near-duplicate scan | No findings; semantic duplicates not certified absent |
| Frozen 16-brief selection | 16/16 feasible, two source series and two mechanic families per selection |
| Deterministic OFF/ON smoke | 16 pairs, 32 synthetic stories, 64 synthetic ballots; replay JSON hashes identical |
| Quality conclusion | `NOT_ESTABLISHED_FIXTURE`; equal fixture scores, 16 ties, zero claimed improvement |
| External real-trial preparation | 48 pairs / 96 requests prepared locally; no generation or dispatch |
| Provider calls / paid experiment cost | **0 / $0** |
| Production/state/integration authority | **false**, no integration or production writes |

The fixture's `red_gate_failures=[]` reflects deliberately synthetic ballot
values and lexical screens, not independent human safety or originality review.
The test suite additionally proves each negative red gate blocks acceptance.
The evidence report preserves this distinction rather than presenting simulated
ratings as real reader preferences.

## Checked-in evidence

`experiments/nova/evidence/pilot-v1/` contains:

- `report.json`: machine-readable engineering and non-quality result.
- `blind-packet.json`: the 32 short fixture stories with byte hashes.
- `requests.private.json`: model-independent requests; no model was invoked.
- `allocation.private.json`: balanced hidden arm mapping, for audit only.
- `ballots.fixture.json`: 64 explicitly SYNTHETIC ballots with neutral scores.
- `artifact-hashes.json`: hashes of those JSON artifacts.

The generated SQLite index remains in that directory locally but is ignored by
Git because it is rebuildable. JSONL is the authoritative, versioned vault.
Do not hand the private artifacts or the repository seed to actual reviewers.

## TEST → FIX loop

1. First NOVA test run exposed a Turkish uppercase/dotless-I duplicate-detection
   failure. Normalization now folds dotted/dotless variants consistently for
   conservative duplicate screening; original source text is untouched.
2. SQLite transaction contexts did not close connections on Windows. Explicit
   closing now releases handles, and repeat build/drift/cleanup tests pass.
3. The combined inherited suite initially used a temporary directory inside the
   checkout. Git walked up into the parent repository, invalidating the inherited
   missing-Git-object test. Moving TMP/TEMP to a workspace sibling resolved the
   environment issue without editing or weakening the inherited test.
4. Review identified generator-request leakage through a forbidden-franchise-name
   list and fixture examples. The request now uses an allowlisted projection of
   LAB facts and brief fields. A regression test checks all generated requests.
5. Statistics now group repeated runs by brief for the acceptance interval,
   preventing 48 repeats from being advertised as 48 independent brief samples.
6. Final suite and smoke passed; external imports additionally reject overbudget,
   missing authorization metadata, self-review, changed receipts, incomplete
   coverage, source-copy screens and invalid story lengths.

## Limits and remaining research

No real paid/unpaid model experiment or independent human reading took place.
The present renderer is a deterministic plumbing fixture; its ON paragraph reacts
to the presence of selected advice, not an intelligent use of a mechanic. This
is enough to test OFF/ON routing and evaluation integrity, not creative benefit.

Eighteen source-linked candidates are available, but the requested high-quality
semantic qualification remains unproven. Source readers must verify claims and
narrow broad spans; age profiles require actual reader/pedagogical review; real
blind trials and independent replication must meet the preregistered thresholds.
No integration proceeds while these are unresolved. This report grants no budget.

CI is defined by `NOVA Independent Offline`, on self-hosted runners only, with
no provider secrets or network/model steps. The Draft PR and its exact-head check
URLs are the live authority for CI status; local PASS alone is not called CI PASS.
