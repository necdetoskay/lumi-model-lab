# P4.30 — B02 genuine English Master → Q25 → Read-only Final StoryState

**2026-10-14 · Draft PR #275 · No main merge or LUMI production changes.**

## Verified second distinct pilot

B02, `Şarkı söylemeyi unutan bulut`, actual reader age 4, Aren starting at GARDEN with COMMONS initially unknown, passed:

1. Actual B02 Sonnet SpineForge and Writer — five beats, immutable full original Spine, 561-word source-grounded English story, **$0.04503**, [run #38465486629](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38465486629). 
2. Separate adversarial **initial** quality audit — **ACCEPT, 5/5 reader score, 0 blockers**, **$0.02069**, [run #38507421533](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38507421533). Frozen v21.4 original final audit has **not** been rerun.
3. Pilot-only English Master sealed with *exactly identical* Writer text bytes/SHA, independently source-bound to B02 audit, **no API call**, evidence `evidence/story_harness_p428/`.
4. Genuine B02 Q25 Sonnet evidence extraction — source-bound and Canon-checked, **$0.021746**, [run #38508253659](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38508253659). Original completion receipt `evidence/story_harness_p429/b02-r06-original-q25-evidence.json` SHA `27df345c2433b7828b6c8439f5eae44420cebf31cc03fbdf08a3fc067187f27f`.
5. Deterministic P4.30 read-only final state draft created from original Q25, **$0 / no model call / no production writes**; original runner and GitHub `evidence/story_harness_p430/b02-r06-real-read-only-final-state-draft.json` exactly match SHA `c19e2624950e6735b4bef6a7d9fe4aeea93596f9b3c44b920a339b7f1c722a63`.

Original source SHA `95397810d5a20c9c7f4a4185f914bf73bf84179ddc5a495c62db84c1fcdac2b8`; Spine SHA `9223dc5662f8a200b23ce3011bd36f8f84c3278ca9e2665feb3ea124a3cef25b`; English Master and Writer SHA `7712f1561881ba50544857bc1d384eba163691c6a1e1bf65b295d90f86e5955d`.

## Proposed state with evidence discipline

- Final protagonist location proposed: **GARDEN**; COMMONS newly discovered and quoted from the story, so known locations propose `GARDEN, COMMONS`.
- No separate object identity or ownership facts are invented; model returned zero object observations, and original Canon objects stay unchanged.
- Obligation `Aren bahçeyi bilir`: Q25 proposed `SATISFIED`.
- Obligation `Yabancının adı kanıtsız uydurulmaz`: Q25 proposed **OPEN**. Crucially P4.30 preserves this status and **both original canonical obligations remain present**. The draft does not auto-mark this obligation satisfied simply because the prose uses the generic nickname Cloud.
- Unknown owners/unknown locations retain original unknown markers. Numeric world-time delta is unmeasured, and final world time stays null.
- `independent_final_state_semantic_certification=false`, `canon_commit_authorized=false`, `production_change=false`, and no Prose edit.

## Real provider cost accounting

B01 known charges **$0.164372** (including earlier diagnostic r04/r05, r06 and Q25); B02 real Spine+Writer+quality+Q25 **$0.087466**. Therefore verified known total of these recorded model calls **$0.251838**. Additional prior unknown-cost claims **$1.13** remain reserved rather than falsely billed, yielding a conservative working exposure **$1.381838**, under the user's original **$10** authorization. Only reconciliation with OpenRouter invoice can determine the real account total.

## What still prevents production and a 90% claim?

Two genuine different **4-year-old** pilots passed original generation and an **initial** model audit, but neither is a full v21.4 final quality acceptance. Q25 proposals and read-only state drafts do not certify semantic consistency or authorize production updates. Age 10/25/40, novel topics and negative holdout must be tested to substantiate `>=90%` reliability, with no extra manual prose fixes. Before scaling, P4.31 should make model input age/topical behavior generic; maintain existing immutable artifacts and stage gates.
