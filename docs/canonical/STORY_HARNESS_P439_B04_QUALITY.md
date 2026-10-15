# P4.39 — B04 independent actual quality; quality is NOT authoring

**Status: source/audit module and zero-call tests implemented. Paid one-shot requires separate exact grant, only after GREEN preflight. PR #275 Draft; no production changes.**

B04 is age 10, *Kayıp renklerin peşinde*, protagonist Emir, MARKET→STUDIO. Original paid SpineForge+Writer [CI #38530980592](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38530980592) was GREEN, with 5 approved beats and 1,277 EN words. Both stages performed real OpenRouter Anthropic Sonnet calls; no retries.

- Source pack: `f6edbf321afab965b1a0166ff0a4feb267935f6be556996c4168572477fa1c47`
- Spine: `af7e8520ba8f06a24906dfffe02cd32d39ff75ff4727f3d3c5e450d515bfa236`
- Writer story: `1648b29b47a830cb7c524e3264f6171ac750a390665207e8453f434d36413557`
- Original Spine provider generation: `gen-1791964646-Ji5krc5hQOiyGfz89qKM`
- Original Writer provider generation: `gen-1791964669-IWfJ0pbhobSncWHBgDBZ`
- Original reported charges: `$0.026102 + $0.032974 = $0.059076`
- Original GitHub Actions archive: `11877788277`; archive digest `sha256:71136f30712920b245c835c99453cc3fdb6e556868f700915c1ab8367ff40b44`.

`src/story_harness_p439_b04_quality.py` accepts only the original protected B04 r06 source and exact per-file SHA-256 digests of Spine, Writer and both provider receipts. It reuses the **unchanged** P4.22 independent 12-family auditor wire and strict response validator. The auditor is a separate Sonnet request bound to the full original prose, approved Spine, input Canon, unknown facts and open obligations. Findings must quote original prose; initial `ACCEPT` requires no blocking findings and reader score at least 4/5. Only one POST, no retry, no fallback. Outcome is not a frozen v21 full final audit.

Proposed quality budget: conservative prior `$1.889558` (including all reserved B04 generation exposure) + stage maximum `$0.040` = `$1.929558` under the overall approved `$10.00`. Before granting, require actual-key remaining limit, full protected source digest verification and the exact manifest-only commit. No grant file is committed with this preparation; thus no provider POST is authorized by adding this code.

The original B04 source keeps both `Emir'in boyası tükenmiştir` and `Harita henüz bulunmamıştır` as open facts. The quality auditor may accept an honest open ending if supported by the approved Spine; it must not invent a found map or new paint supply. Even an initial ACCEPT will **not** automatically promote to English Master, Q25 or Canon. Later stages require original receipt-linked immutable artifacts and separate gates.

Negative and positive admission tests: `tests/test_story_harness_p439_b04_quality.py`, read-only `.github/workflows/story-harness-p439-b04-quality-offline.yml`. Single-use real audit workflow (initially no grant): `.github/workflows/story-harness-p439-b04-quality-once.yml`.

After genuine accepted quality, create a separate immutable pilot-only English Master → evidence-only real Q25 → read-only final state. If REJECT, retain provider receipt and findings, do not claim B04 complete, and do not retry the paid call.
