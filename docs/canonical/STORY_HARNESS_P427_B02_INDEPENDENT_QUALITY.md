# P4.27 — Independent first quality audit of genuine B02

Draft PR #275 · 2026-10-14 · standalone B02 initial quality, no production changes.

## Evidence and source identity

B02 topic: **Şarkı söylemeyi unutan bulut**, reader age 4, protagonist Aren. Canon start at GARDEN; unknown Commons until observed; stranger/cloud's proper name remains unproven. Its **actual Sonnet SpineForge→Writer generation** completed in [Actions #38465486629](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38465486629), offline CI [#38465486562](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38465486562).

- B02 original source pack SHA: `95397810d5a20c9c7f4a4185f914bf73bf84179ddc5a495c62db84c1fcdac2b8`
- B02 original five-beat Spine SHA: `9223dc5662f8a200b23ce3011bd36f8f84c3278ca9e2665feb3ea124a3cef25b`
- B02 Writer original 561-word story SHA: `7712f1561881ba50544857bc1d384eba163691c6a1e1bf65b295d90f86e5955d`
- Spine provider generation `gen-1791924649-l35Hyv491YV9pvzYIcxr`; cost **$0.02301**.
- Writer provider generation `gen-1791924666-ZBDHDinhuZCE5lsF7Pt1`; cost **$0.02202**; total B02 production cost **$0.04503**.

Four exact original JSON files have been snapshotted from the protected CI runner into `evidence/story_harness_p426/`. The P4.27 auditor first cross-checks **byte identity of those frozen evidence files** and the original protected real provider claims. It also uses the P4.22 settled generation receipts, checks original Writer text hash, Spine hash, token/cost consistency, reader age, original state, all obligations and the 12 blocking categories.

This does NOT reuse B01 acceptance. The P4.22 *adapter* is parameterized to accept reviewed B02, while leaving original frozen v21.4 untouched and B01 quality artifact unchanged. P4.27 has separate `p427-b02-r06-<story-hash-prefix>` one-use durable audit directory. One Anthropic Sonnet request, no fallback, no retry; original quality stage cap **$0.040**. The provider's actual cost is captured where a valid complete receipt exists. Reject findings must refer to verbatim B02 story quotes; ACCEPT is only allowed with zero blockers and reader score >=4/5.

## Budget control

Original aggregate model budget approved by user **$10.00**. Previously conservatively reserved **$1.294372**, plus the **verified** B02 generation **$0.04503**: **$1.339402** exposure so far. Reserve up to **$0.040** for B02 initial audit, giving **$1.379402** conservative total post-run. The reservation is not necessarily an OpenRouter bill, and the application budget check is not a provider-side prepaid limit.

## Admission limits

If initial B02 quality returns ACCEPT, this alone is **not** English Master, Q25, final state certification or production-ready release. Explicit same-B02 source verification and new separate steps are needed. If REJECT or timeout, never rewrite the story or replay the consumed provider request silently. Follow the user's requested 3 targeted fixes per failure family before proposing an alternate architecture. No main merge, no production cutover.
