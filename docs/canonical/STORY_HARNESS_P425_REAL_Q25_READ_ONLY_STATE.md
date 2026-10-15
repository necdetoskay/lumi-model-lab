# P4.25 — B01 genuine Q25 final-state draft, read-only and source-sealed

**2026-10-13 · Draft PR #275; Issue #291**

Real B01-r06 has completed the **pilot** pipeline through observed state evidence:
- Variable Canon state + topic: source SHA `91854710f46db13ee2599d567ca2fcbbcd945af50515a779ddee58211ee050dc`
- Real Sonnet SpineForge (5 grounded beats) SHA `daafc25a6701a8369be994000e71669722c1cb56364bce3559f5fb8ca944f7a9`
- Real Sonnet Writer, 516 English words SHA `cbbf3ba8cb3a9ec5d19ed51238bc3b9a0259237cdb7896b75dcdd0584adca912`
- Separate independent **initial** literary quality audit: ACCEPT, 0 blockers, 4/5. **Full original frozen v21.4 final quality was not rerun.**
- Same-byte Pilot English Master sealed in q25 runner and frozen evidence, no manual prose edits.
- Genuine Q25 evidence call [#38463131701](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38463131701): source-bound exact quotes, real generation ID `gen-1791923622-5CitCjZOpgV38KerIIny`, actual OpenRouter reported Q25 cost **$0.026022**.
- Deterministic **P4.25 read-only Final StoryState candidate** created from the exact byte-verified Q25 response: 0 new model calls, 0 new dollars, no production changes.

## Provenance

Reference source evidence files are under `evidence/story_harness_p421` (Spine and Writer), `evidence/story_harness_p422` (initial independent ACCEPT), `evidence/story_harness_p423` (same-byte pilot Master), `evidence/story_harness_p424` (original real Q25 response), and `evidence/story_harness_p425` (state draft).

- Real Q25 receipt SHA: `58f265f5684acf3552b7cf9b9de7cbfca592ef8cc2f3d5d5caa03f6dca324568`
- Read-only Final StoryState draft exact SHA: `79b2ec9d32890cb4d229ee4f44f47b419439d4e7ad43cfc44ca4da6822eafa9c`

The first Q25 attempt (v01) failed closed and had unknown charge (conservatively reserved **$0.05**). The second attempt (v02) passed. Original v01 was never retried or overwritten. A separate Git checkout recovery was performed after an initial GitHub checkout failure; none of the producer, auditor, Master or Q25 one-use claims was mutated.

## Safe facts in candidate

- Protagonist Mira last observed at HOME.
- New discovered location MEADOW; known locations candidate `HOME, MEADOW`.
- Glowing stone observed held by protagonist; little star observed at window; **both owners remain unknown**. Possession does not confer ownership.
- Two starting obligations have evidence for status `SATISFIED`, but obligations are **not removed from Canon** until independent terminal-state semantic validation.
- Unknown `unobserved_owners`, `unobserved_locations` retained; world-time change **unmeasured**, so no numeric elapsed value is fabricated.
- Final-state candidate is not production-ready or semantically certified. Flags: `state_commit_authorized=false`, `original_v21_4_full_final_quality_audit_passed=false`, `production_change=false`.

## Budget and completion caveat

Confirmed known model charges:
P4.18 compatibility $0.000714 + B01-r04 $0.020428 + B01-r05 $0.045866 + B01-r06 $0.050276 + B01 initial audit $0.021066 + actual B01 Q25 $0.026022 = **$0.164372**.

Separately, **$1.13** conservative exposure remains reserved for earlier requests whose exact bill was not established ($1.08 from previous uncertain steps and $0.05 from first Q25). The resulting conservative working total is **$1.294372**, well below the user's $10 aggregate authorization; this is not the authoritative OpenRouter invoice.

**Do not report 90% success**: we have one true B01 pipeline candidate; target demands >=9/10 real diverse pilot and >=27/30 separate holdout with the same complete stage requirements and an independent reading-quality threshold. Generic case support across ages and topics is next. ModelLab remains Draft; no main merge or production cutover.

## Next

Generalize the already tested P4.16 variable state+topic bridge and real Sonnet Spine/Writer to a **second distinct case** B02. Preserve source-provenance/cost claims, run one bounded genuine API attempt and independently check the output. Do not expand into the complete benchmark until the varied-case path is stable. Continue the user's 3 distinct corrective fixes per failure family before considering a replacement method.
