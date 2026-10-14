# P4.33–P4.36 — B03 quality, immutable promotion, and diverse 10×3 pilot

Status: DRAFT PLAN / NOT A PASS CERTIFICATE. PR #275 only; no production writes.

## Verified starting evidence (2026-10-14)

- P4.32 head before this work: `4142be3867d8a795814d10fa8f7cff48aaac512f`, offline run `38509478552`: SUCCESS. Its offline tests perform **zero** model calls.
- B03 source pack SHA `b55ba5c57a3abda0a1b4ef18fe98284f4fea7511b1b82281585ac9da77a205c0`, original Spine SHA `9a0b0476c2c5f94bc5e7f3a6d0261cefbee9ce22062c02f8a55fed761c10a9ad`, original 1,300-word Writer SHA `80fa8224c78c494b13bc347ecabdfff75fd5c9e1638ad88ee9ba47c6986643f9`.
- Historical B03 SpineForge+Writer receipt cost $0.067720; source copies retained under `evidence/story_harness_p431/`. Actual provider provenance remains subject to byte equality against protected runner claim files.
- Budget ledger's prior **conservative reservation**, including B03 generation, is $1.449558 (not necessarily the same as provider-billed cumulative spending). User cap $10.00. B03 next quality maximum $0.040, thus $1.489558 after reservation.
- Initial quality is NOT accepted. B03 English Master, Q25 and Final StoryState do NOT exist as an authorized chain. P4.22's original auditor adapter, not the frozen production v21.4 final-audit engine, is used.

## P4.33 independent original B03 initial audit: 0/1 paid call

The companion workflow `.github/workflows/story-harness-p433-b03-quality-once.yml` is **not** a general PR-check fee trigger. It requires one exact manifest-only commit in PR #275 on the trusted experiment branch. Only a synchronize event and the first workflow attempt qualify; all other runs STOP before key use.

Preflight verifies: exact-case B03 original protected runner claim; four files byte-identical to checked-in original provider records; Canon, Spine and Writer SHA; 1,300 English words; genuine settled provider generation IDs; age 10; one original quality request using Sonnet with provider fallback disabled; all 12 blocking defect families; current inference-key read-only allowance; conservative ledger <= $10.00. The audit writes a unique O_EXCL 00-intent and an immutable 01-outcome (or STOP_UNKNOWN_OR_INVALID); unknown charge means consumed attempt, no auto-retry.

A **real** ACCEPT requires original audit `ACCEPT`, zero quoted/grounded blockers and reader score >=4/5, exact story + Spine SHA, authentic generation ID, provider-reported usage and cost <= $0.040. Mocked responses, green offline CI, a prior B01/B02 verdict or a malformed audit never count. REJECT is a valid measured outcome, not CI failure. Do not run repairs or master promotion automatically.

## P4.34 acceptance-only English Master → genuine Q25 → read-only Final StoryState

1. Independently validate P4.33 real audit receipt against B03 exact immutable Writer/Spine and policy; if missing, STOP.
2. Promote English Master with the existing source-sealed master admission contract; no text rewrite, no state mutation, record SHA linkage and its own receipt.
3. Execute original real Q25 once on this exact Master/Canon, with its own separate one-shot grant, cost reservation and model generation ID. Preserve passage-grounded state candidates and failure evidence.
4. Deterministically project only verified Q25 evidence into a read-only Final StoryState draft; preserve unknown/unresolved facts, no invented object owners or locations, no Canon or production writes. Final-audit completeness must not be implied by initial-quality acceptance.
5. Any new request can only be issued with a new reviewed scope and fresh ledger allowance. No automatic retries. Resolve at most three *offline* code/contract attempts per distinct defect before escalating or stopping.

## P4.35 ten diverse scenarios

Benchmark set is fixed **before** generation. Reuse original B01 and B02 (age 4), B03 (age 10) as historical baseline only when their frozen source/story/quality receipts meet precisely the same pilot rubric. Add seven independent Canon/topic packs: B04 (10, nonmagical mystery); B05 (10, fantasy with an explicit irreversible choice); B06 (25, ethical dilemma); B07 (25, exploration); B08 (40, relationship conflict); B09 (40, speculative fiction); B10 (4, gentle imaginative adventure). This yields age strata 4:3, 10:3, 25:2, 40:2. These are proposed cases, not existing generated stories.

For each: independent Canon/unknown-facts/open-obligations; actual verified SpineForge -> Writer -> adversarial quality -> acceptance-only Master -> genuine Q25 -> read-only State; immutable artifacts; no cross-case acceptance; ledger of invocation/usage/cost/latency. Capture structured failure taxonomy (input invalid, provider/transport unknown, Spine, Writer, initial audit REJECT, Master, Q25, evidence projection) and human reader engagement assessment. No 90% success assertion from 10 cases. Archive exact prompt/model versions and the seed when supported; absent reproducible seed, use unique claim/run identifiers.

**Per new full-run worst-case reserve** using current caps: $0.35 for generation + $0.040 for initial quality + $0.050 for Q25 = **$0.440**; offline Master/State $0. The final allocation is always computed using the *latest* ledger, not these example ceilings. For one historical B03 after acceptance, an additional Q25 cap of $0.050 must be separately reserved. Stop before any invocation that could exceed $10 conservative exposure.

## P4.36 thirty independent end-to-end trials

Target 10 scenarios × 3 genuinely distinct independent generation/audit/Q25 runs = 30 trials. Historical runs qualify only if the same full rubric and evidence are met; repeated audits of one manuscript are **not** 30 independent story-generation trials. Stratify every case, vary run IDs/unknown inputs, pre-register pass/fail criteria and prevent memorized narrative leaks.

Primary pass gate: at least **27/30** fully verified end-to-end, AND at least 2/3 for each case, with zero unreported Canon writes, no synthetic ACCEPT and no ledger exceedance. Report numerator, denominator, Wilson/binomial uncertainty, case-level results, reader scores, length targets, SHA/receipts, median and p95 cost and latency. 27/30 is a pilot gate, **not** proof of >=90% population success. Additional holdout studies would be needed for a strong statistical reliability claim.

At current $0.440 maximum per fresh trial, **30 new runs could require $13.20**, above the $10 user authorization even before historical exposure. Therefore all 30 are *not* pre-approved at current worst-case caps: execute in measured, budget-guarded tranches. After the ten-case pilot, reduce cost by qualified model/prompt evaluation only after maintaining gate correctness. Never silently weaken audit, omit Q25 from an end-to-end pass, reuse a verdict, exceed the budget or extrapolate results from mocked trials.

## Reporting contract

Each stage receipt: schema_version, case/run ID, source_pack_sha256, spine_sha256, story_sha256, previous_receipt_sha256, exact model/route, generation ID, attempt count, outcome, blocking findings, word count and reader score (as applicable), tokens, provider-reported cost, unknown-charge reserve, cumulative conservative cap, timestamps and duration. Every denied admission records STOP reason and the prior immutable SHA. Production/main change policy: **NO**.

