# LUMI V4.2 — Bounded iterative English model-quality repair

Date: 2026-10-15
Branch: `feature/story-pipeline-v4-2-iterative-quality-20261015`
Status: **offline qualified, not yet authorized for another paid V4.2 run**.

## Trigger from real provider evidence

Fresh V4.1 live execution [#38791816691](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38791816691) reached the English quality recheck before stopping:

- Sonnet 5.5 genuinely produced a new accepted Spine. Luna Spine Gate genuinely returned `ACCEPT`; no Haiku epistemic repair was required.
- Aion 3.5 Mini genuinely produced an English episode of **1,943 words**.
- First Luna English audit reported four possible canon defects; Sol adjudicator confirmed only the unsupported new `guild investigator` access requirement.
- Sol model-authored exact replacement changed `the inspection siding was open to any guild investigator` to `the inspection siding was open to any rail investigator` and hard guards accepted the change.
- Second Luna audit flagged 14 possible semantic defects (many false positives). Sol confirmed **four** residual local canon-integrity findings.
- V4.1 stopped as designed after one round (`V4_ENGLISH_QUALITY_BLOCKED`). No Turkish translation was attempted, and no story was published.
- Provider-confirmed total: **8 HTTP POSTs, $0.29756985**. The spent one-use authorization **must not** be retried.

## V4.2 improvement — general, not specific to Mara

1. Make **up to 3** successive Sol model-authored English local-repair rounds available, requiring full deterministic hard-guard check and new Luna+Sol adjudication between attempts.
2. Never let the orchestrator modify narrative prose. Each patch remains a model-generated, exact-source replacement vetted by the existing bounded-patch engine.
3. Track SHA-256 of every accepted intermediate English story, and **STOP** upon oscillation or repeated identical story output. The repair stage itself refuses zero/invalid patches and disallowed scope.
4. STOP if a fourth round would be necessary. No fabricated quality PASS.
5. World and Saga commits, publication and manual text edits remain forbidden. Previous frozen V4 / V4.1 code and evidence are unmodified.
6. The future paid V4.2 runner must have a fresh distinct commit-bound, owner-approved grant and a complete provider-call ledger. The V4.1 grant is already consumed. This branch does **not** automatically dispatch paid models.

## Evidence

- The V4.2 test suite runs mock stage outputs through **two complete independent Sol repair → Luna re-audit loops** and then through mock EN-to-TR finalization. No mock result is presented as a real story.
- Additional tests verify no-progress abort and exhaustion handling.
- Old V4.1 and V4 tests remain green.
