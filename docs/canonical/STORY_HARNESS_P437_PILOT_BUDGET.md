# P4.37 — Ten genuine scenario pilot / thirty independent trials, budgeted

**2026-10-14. Draft PR #275 only. Production, main and Canon untouched.**

This is a **read-only, zero-provider-call planning and reporting gate**, not a generation-success certificate. The canonical age/topic matrix remains `configs/story_harness_p415_benchmark.json`; two cases each for ages 4, 10, 12, 25 and 40.

## Frozen pilot matrix

| ID | Age | Original registered topic | Original initial chain |
|---|---:|---|---|
| B01 | 4 | Kayıp yıldızın eve dönüşü | Spine→Writer→real initial ACCEPT→Master→real Q25→read-only state |
| B02 | 4 | Şarkı söylemeyi unutan bulut | Spine→Writer→real initial ACCEPT→Master→real Q25→read-only state |
| B03 | 10 | Gizli nehir festivali | Spine→Writer→real initial ACCEPT→Master→real Q25→read-only state |
| B04 | 10 | Kayıp renklerin peşinde | NOT GENERATED |
| B05 | 12 | Ağaçların hafızası | NOT GENERATED |
| B06 | 12 | Ay ışığındaki kütüphane | NOT GENERATED |
| B07 | 25 | Fenerdeki eski mektup | NOT GENERATED |
| B08 | 25 | Gölgeler pazarı | NOT GENERATED |
| B09 | 40 | Kış bahçesinin sırrı | NOT GENERATED |
| B10 | 40 | Son trenin hatırası | NOT GENERATED |

Historic B01–B03 initial pipelines are **not** the frozen v21 final production audit. They are also **not** independently preregistered holdout successes. Current release-certified count is **zero**. Current independently validated holdout count is **zero of thirty**.

## Conservative inference budget

The existing explicit authorization is **$10.00**. Budget fields are in `src/story_harness_p437_pilot_matrix.py`, validated by offline CI:
- Provider-reported documented original model costs: **$0.378446**.
- Prior unknown-charge safety hold: **$1.130000**, retained, not misrepresented as provider invoice.
- Unspent reserved amount from prior B03 quality/Q25 limits: **$0.031112**.
- **Total conservative exposure: $1.539558**.
- **Remaining headroom: $8.460442**.

The current complete new trial limits are generation **$0.350**, independent initial quality **$0.040** and Q25 **$0.050**, total **$0.440**; Master and read-only final state are offline stages. Hence the seven missing pilot scenarios can conservatively reserve **7 × $0.440 = $3.080**, leaving **$5.380442**. This reserves space for **12 additional full trials** at the unchanged caps. Across the current remaining budget there is room for **19 new complete trials**, not all 30 new validations. **30 × $0.440 = $13.200** even before earlier costs.

This is a forward reservation calculation, not a guarantee of provider-side prepaid enforcement. Before each new single-use grant, read the most recent real ledger and inference-key remaining allowance; never use stale estimates or automatically retry. Reducing caps requires separate empirical qualification, never dropping a required stage.

## Independence and evaluation policy

The holdout matrix has **three distinct run slots per scenario**, 30 total; all start `NOT_RUN_NOT_ACCEPTED`. Every slot requires a new original source-bound SpineForge/Writer generation, separate adversarial initial audit, immutable Master, genuine Q25 with quote-checked evidence, read-only State, usage/cost/token/latency receipts and human narrative assessment. Re-auditing or editing one existing manuscript does **not** count as independent story generation. Separate random seeds are preferred when supported; otherwise use unique run/claim IDs and record model decoding settings and provider generation IDs.

A provisional acceptance gate is **≥27/30** end-to-end and **≥2/3 in each of ten distinct scenario groups**, plus zero unreported Canon mutations, zero fabricated ACCEPT and no budget violations. It does not statistically prove 90% population reliability; release qualification additionally needs true holdout evidence and frozen v21 final audit policy.

## Implementation

`src/story_harness_p437_pilot_matrix.py` reads the original frozen benchmark and real B01/B02/B03 audit, Master, Q25 and read-only state artifacts. It refuses swapped/missing receipts, non-ACCEPT initial verdict, invented state, altered age matrix and budget inconsistency. It never calls a provider and never authorizes a run merely because a report is green.

`tests/test_story_harness_p437_pilot_matrix.py` checks truthfulness, negative tamper cases, case ages, ledger arithmetic and that 30 prospective runs remain unaccepted. Separate offline CI: `.github/workflows/story-harness-p437-pilot-matrix.yml`.

Next: **B04** under a new one-shot grant after exact Canon/source SHA freeze, original per-stage caps and protected runner preflight. Then B05–B10 in controlled tranches, measuring actual rates before allocating the 30 independent holdout.
