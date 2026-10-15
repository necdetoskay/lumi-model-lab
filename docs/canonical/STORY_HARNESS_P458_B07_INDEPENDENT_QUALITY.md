# Story Harness P4.58 — Independent B07 Initial Quality (Age 25)

Scope: PR #275 Draft, no production or main changes. New model cost maximum $0.040 after B07 generation, never automatic reruns. B05 STOP and B06 ACCEPT evidence unchanged.

## Original frozen B07 provider lineage
- Original P4.57 CI: 38611801159; original source dbe62430a4a06fe82c3216275b04fdee7f340a7bd4718458d47097fa98fde476.
- 2,708 original English words, story SHA-256 cc89a48c9dde4ead0312fe69f838fee469dc69ca27dd741e2369cabd4536f226.
- Spine SHA-256 5101332bfa2ae683ae330441c3c99455ef618b71a5a3b92c47b10fe5259a610d.
- SpineForge provider ID gen-1792000970-lhLi0VZKObGfdDDrR1ud / cost $0.0282. Writer provider ID gen-1792000994-aY9vBKsRVGNbmKiSbPMH / cost $0.064866. Total reported $0.093066.
- The four original JSON artifacts are frozen byte-for-byte under evidence/story_harness_p457, while self-hosted runner claims remain unchanged.

## Exact original JSON SHA-256
| Artifact | SHA-256 |
|---|---|
| spine-plan.json | 95148dec43a7094ee6c9d71128555d6a2df1c92ebbb123f86c7e3a65a51c01c5 |
| story-draft.json | ab343362305aa2047bf918b319163b73bd932153fc88523576f84b97a844a50d |
| 01-spineforge-receipt.json | b21fc5e193dcf1cf3a861636d3118d412b078f6e69a4fdf418f90b5ed9d0cbb5 |
| 02-writer-receipt.json | c20d232ecfcaf2986823b94c070aa2e4044674bb71c48b6577184deccbe8836e |

## Request bound
- Original P4.22 audit_wire serializes the full B07 2,708-word story and source into 20,165 bytes, exceeding default 20,000-bytes cap.
- Default 20,000-byte limit and quality verification stay unchanged for every other story.
- Explicit 22,000-byte limit is permitted ONLY for exact B07 age 25 2,708-word source. No truncation, paraphrasing, deletion, selective scene audit, or omitted Canon context.
- Model quality result must be genuinely source and Spine matched, 12-family check, anchored blockers, score >=4 for ACCEPT, one independent model call at most.

## Authorization and ledger
- First commit freezes original data, QA code, tests, new inactive workflow, and offline guard. NO quality grant; $0 new provider costs.
- Only after targeted offline CI GREEN may a separate one-file config grant activate the one-shot quality workflow on PR synchronize event.
- Independent audit grant is bound to SOURCE_SHA, SPINE_SHA, STORY_SHA, original provider generation ID, and age 25.
- Previous conservative reserved $3.209558 / $10; new maximum quality stage $0.040; conservative post-audit reserve <= $3.249558.
- Explicit immutable claim before POST in _lumi_p458_b07_quality_claims; no retries on unknown charge or invalid quality. An ACCEPT does not itself authorize Master, Q25, production Canon or state writes.

## After quality
- On ACCEPT only: review frozen quality evidence and separately perform English Master -> real Q25 -> read-only Final StoryState, with additional spend reserved and approved before model POST.
- On REJECT or STOP_UNKNOWN_OR_INVALID: preserve receipt; do not invent ACCEPT, re-run, or promote.