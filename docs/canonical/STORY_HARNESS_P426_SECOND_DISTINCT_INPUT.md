# P4.26 — Second genuinely different Canon/topic story pilot (B02)

**Draft PR #275 · Issue #291 · 2026-10-13**

## Why this stage exists

The completed B01-r06 pilot does not establish the user's target >=90% genuine independent end-to-end success. A hardcoded B01 audit or saved English Master could make false successes appear green for another state or topic. P4.26 reuses the existing **same** model-generation engine (`src/story_harness_p417_live_pilot.py`) and the P4.16 dynamic input compiler for **a second distinct benchmark case**, B02. This is a variation test, not a new writing method or production cutover.

B02's topic is `Şarkı söylemeyi unutan bulut`, reader age 4, with different canonical protagonist/locations (`GARDEN`, `COMMONS`) and different obligations from B01. B02 state/topic SHA is derived from the frozen P4.15 fixture. The actual paid call is **off by default**; a single exact GitHub Actions manifest change is required.

- B02 one-shot model plan: Sonnet 5.5 → actual state-grounded SpineForge → source-bound Writer, via the unchanged real OpenRouter transport and strict local validators. Exactly **two or fewer model POSTs**, one per stage, without automatic retry.
- Immutable B02-specific run claim `b02-<source-prefix>-r06`; original model-generated Spine `spine-plan.json` is durably saved before Writer; story draft SHA/receipts follow. Any failure consumes the entire B02 attempt and is classified; user requested up to three **distinct corrective fixes** before considering a new approach.
- No automatic literary or terminal-state claim: `independent_quality_accepted=false`, `english_master_authorized=false`, `q25_evidence_accepted=false`, `final_story_state_certified=false`. B01's ACCEPT and Q25 result **never apply** to B02.
- Maximum new B02 application-level cost reserve **$0.35** (Spine stage $0.075, Writer stage $0.14); earlier stage-wide user total conservative exposure **$1.294372**, after reserving B02 **$1.644372**, below the original aggregate $10 user authorization. Such caps require authentic OpenRouter usage receipts and don't constitute provider-guaranteed prepaid limits.

## Acceptance gates

Real B02 generation must produce **independent source SHA/Spine SHA/Writer SHA** (different from B01). Then independently audit B02 against its own Canon and reader-age narrative quality criteria. Only after genuine quality acceptance should a separate same-source pilot Master, quote-backed Q25 and read-only Final StoryState be allowed. No production write, no main merge.

Pilot cases B01–B10 should eventually attain >=9/10 complete real accepted stories; release holdout >=27/30 varied unseen cases. Model-only mocks must never be counted as those successes. The old production LUMI path and frozen v21.4 code remain untouched.
