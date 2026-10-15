# P4.28/P4.29 — Actual B02 independent English Master and Q25

**Draft PR #275 · 2026-10-14 · Production untouched**

## Actual evidence so far

B02 `Şarkı söylemeyi unutan bulut` used a **distinct** Canon/topic/character (Aren, GARDEN and newly seen COMMONS). Actual source SHA `95397810d5a20c9c7f4a4185f914bf73bf84179ddc5a495c62db84c1fcdac2b8`, Spine SHA `9223dc5662f8a200b23ce3011bd36f8f84c3278ca9e2665feb3ea124a3cef25b`, original 561-word English story SHA `7712f1561881ba50544857bc1d384eba163691c6a1e1bf65b295d90f86e5955d`.

- Genuine B02 SpineForge and Writer [Actions #38465486629](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38465486629), **$0.04503**.
- Separate real B02 initial Sonnet audit [Actions #38507421533](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38507421533), **ACCEPT, 5/5, 0 blockers**, actual **$0.02069**. Not original frozen v21.4 final audit.
- Independent audit generation `gen-1791949279-wfeuT7G0vvvCMKuOjmsB`. Real audit receipt frozen in `evidence/story_harness_p427/`.
- B02 **Pilot-only English Master** created from original accepted Writer bytes, **no text edits and no new model calls**, SHA matched exactly; immutable runner artifacts under `_lumi_p428_b02_master_claims/b02-7712f1561881ba50/` and frozen same-byte evidence under `evidence/story_harness_p428/`. It is not authorized for production.

The independent Q25 proposal candidate for B02 is implemented in `src/story_harness_p429_b02_q25.py`: it builds an entirely new claim `p429-b02-r06-q25-evidence-v01`, verifies all original source/quality/master bytes and same-story SHA, then calls Sonnet **at most once**. It shares the verified P4.24 flat response schema / deterministic quotation validator, but derives exact allowed spatial relation vocabulary from **B02 Canon** (`AT_GARDEN`, `AT_COMMONS`, never B01 HOME/MEADOW). A model may only propose final GARDEN/COMMONS location with a verbatim story excerpt near the ending, actual observed objects, unknown ownership, exact Canon obligations and unknown world-time; invented facts or mismatched quotes fail closed. No retries or fallback, no story rewrites.

## Costs and limits

Verified B02 production and independent initial audit together: **$0.06572**. Prior conservative budget after B02 initial audit **$1.360092**, including previous unknown-cost reservations, not a confirmed invoice. B02 Q25 application-stage maximum **$0.050**, after reserving **$1.410092**, below user's $10 overall authorization. A verification failure consumes its run ID and cannot be retried without a **new** uniquely authorized run and separate allowance.

## Not yet proven

No claim of 90% reliability. B02 Q25/Final StoryState and B03–B10 diverse real pilots, then independent holdout are pending. B01 and B02 initial ACCEPTs do not constitute full frozen v21.4 final audit. This pilot path must never modify main, production data or final canonical LUMI state.
