# LUMI Story Harness P1 — Frozen Historical SpineForge/Q25 Evidence Bridge

**Status:** Offline experiment; Draft PR #275. **No provider calls**; no semantic certification, stage execution, production/canonical writes or automatic stage advancement.

## Purpose

P0 proved that a small mock chain can be inspected deterministically. P1 now proves that **actual historical model-lab artifacts** from another experiment branch can be imported **byte-for-byte**, compared against their recorded SHA-256 and classified using pinned schema-specific, *read-only* adapters.

These four cases are **different experiments**; do not falsely join a SpineForge sky-island case to the unrelated KITE or GREENHOUSE Q25 cases. Being able to read both types does not mean the combined end-to-end story pipeline works.

## Provenance and frozen source

Original source repository: `necdetoskay/lumi-model-lab`, experiment commit:
`2eb3d825b5baf8f0f16ccb23805f619d433c7236` from branch `experiment/q25-narrative-memory-intent` (Draft PR #273). The exact six original files were imported as copies into `evidence/story_harness_p1/snapshots`.

At import time, all six local copies were compared **byte-for-byte** using `git show <original_commit>:<original_path> | cmp - <imported_file>` and separately checked by SHA-256. The script pins their original source path and digest per case. A **normal harness run does not re-fetch or re-authenticate that Git commit**; it validates the archived copy against a hash locked into the code/manifest. Source provenance is a recorded claim, NOT proof of a GitHub gate's authenticity.

Case/archive mapping:

| Independent case | Frozen real source | Original recorded decision | Harness interpretation |
| --- | --- | --- | --- |
| SPINE-V20-HUMAN-APPROVED | `evidence/spineforge-v20-human-review/36910614976-approved.json` | `gate_decision=ACCEPT`; human review says APPROVE | **Human approval was recorded historically**. Writer handoff was indicated ready, but the record explicitly **did not authorize paid writer execution**. Harness does not authenticate that human review |
| SPINE-V20-AUDIT-REJECTED | `evidence/spineforge-v20-paid-story-audit/36969500342/qualification-report.json` | `status=FAIL_KNOWN_DEFECT_MISSED`, `qualification_pass=false` | Rejected story audit; do not proceed |
| Q25-KITE01-CANDIDATES | `evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-03-{public-ledger,raw-extraction}.json` | `SOURCE_BOUND_CANDIDATES_ONLY`, **$0.042406** | Source-bound structural candidates only; **not accepted Final StoryState** |
| Q25-GREENHOUSE01-REJECTED | `evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/paid-attempt-01-{public-ledger,raw-extraction}.json` | `REJECTED_BY_OFFLINE_GATE`, **$0.042746** | Historical paid rejection **remains rejected** even though a *later and separate* offline source-order normalizer was able to replay the unchanged raw response structurally |

The Q25 historical provider-reported cost **$0.085152** is only the sum of these two old Q25 runs. It is **not** a new harness cost, and does not include every prior Model Lab model call. This P1 implementation: **0 model calls / $0 new spend**.

## P1 implementation

- `src/story_harness_p1.py` accepts an immutable import manifest and a repository root.
- `configs/story_harness_p1_frozen_import.json` identifies **four independent historical cases**, their exact source SHA and source commit.
- It reads **only JSON archive copies**, validates canonical source/case identity and pinned hashes, and does not call any stage validator, model, network endpoint or shell command.
- Frozen case-to-file bindings in code prevent swapping KITE/GREENHOUSE identities or rewriting historical RED as GREEN.
- The two Q25 snapshots are checked for matching seed/story SHA, original provider calls, bounded and measured usage, and original outcomes; they remain *untrusted*.
- The SpineForge records are checked for historical writer handoff and failed audit conditions. The system never promotes an author-recorded ACCEPT into an authenticated gate or allows paid writer execution.
- Every report has `historical_gate_authenticated_by_harness=false`, `spine_and_q25_story_chain_claimed=false`, `semantic_support_certified=false`, `full_story_state_qualified=false`, `state_commit_authorized=false`, `production_write_performed=false`.
- The P0 demonstration remains explicitly mock and unchanged. **No end-to-end generation is claimed.**

## Commands

```bash
python -m unittest discover -s tests -p 'test_story_harness*.py' -q

python -m src.story_harness_p1 \
  --manifest configs/story_harness_p1_frozen_import.json \
  --repo-root .
```

Reports are deterministic and emitted to stdout by default. No files need to be written.

## Important trust boundary / next phase

A pinned byte hash proves the imported artifact was not modified; **it does not make a recorded gate decision truthful**. P1 has not independently validated the source's review identity or re-run the actual SpineForge/Q25 quality and semantic gates. A third-party reference to `ACCEPT` in a JSON file cannot itself authorize the next stage.

**P2 must** define an actual authenticated `StageGateReceipt` and typed `StageResult` bound to exact source code/gate version, input/output digests, stage/scene identity and explicit policy. Only a receipt from a verified, isolated gate invocation may authorize controlled downstream workflow progression. A review-pending Q25 story cannot be made canonical from citation/hash success.

Production LUMI and Q25 PR #273 remain untouched; Draft PR #275 must not merge without review.
