# SERA Mara S1 — First real extraction/JEV diagnostic

**Status:** HELD, NOT CANONICALIZED. **Date:** 2026-10-16. Original Sonnet pre-Haiku Spine remained unchanged (blob SHA fe1dda0047000438bbfaac69022e835bf7e0a1f8).

## Immutable run references

- [First scene Writer + failed Haiku extractor](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38808450095). Archived artifact ID 12007457147.
- [Exact-source Gemini extractor + JEV continuation](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38809210994). Archived artifact ID 12007632779.
- First run result.json SHA-256: 4e287eac417836f15c63c38a4247a56c04eecb1fed8aa0c43f034722d40e456f.
- Frozen 243-word prose SHA-256: 80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03. The continuation reused this prose, not a regenerated scene.

## Real observed result

| Dimension | Measured |
|---|---|
| Writer | openai/gpt-5.6-luna, 243 words |
| Writer mentions/events | 8 / 6 |
| First extractor | anthropic/claude-haiku-4.5; invalid JSON; fail closed |
| Resume extractor | google/gemini-3.7-flash; 8 mentions, 7 events |
| Structural M2 decision | HOLD |
| Structural M2 findings | 10 event disagreements, 10 ungrounded event times, 1 non-asserted event |
| Exact writer-vs-independent event matches | 0 |
| JEV 1.13 | 18 claims, 17 SUPPORTED, 1 INSUFFICIENT_EVIDENCE; ESCALATE |
| Python reducer | HOLD_COVERAGE; no accepted exit snapshot |
| Canonical/DB writes | 0 |

### Partial provider cost, NOT total

- Writer cost as reported: USD 0.003069.
- Gemini independent extractor cost as reported: USD 0.004692.
- Known reported subtotal: USD 0.007761.
- Haiku failed-call spend not captured; JEV price/usage not returned in recorded verdict. Neither is assumed to be zero.

### A genuine double omission

Manual analyst inspection of the exact prose revealed two physical object candidates both extractors omitted:

- **Bench:** "Teodor Vane stood beside the bench"
- **Pencil:** "Vane watched the pencil move"

Neither appeared in either 8-mention report. Therefore equal lists do NOT prove complete object coverage. Treat these as physical entity CANDIDATES pending canonical ID/attributes; do not invent location/ownership/color/size beyond supported evidence.

### Detected protocol defects

1. Gemini's strict schema permitted empty event argument dictionaries. It supplied empty dictionaries for all events. Writer also used free-form non-reducer keys. Such outputs must not be used as typed transitions. Require exact per-operation argument schema and reject missing properties.
2. An unreported exact event minute is often legitimate in prose. Retain unknown time and a scene-local relative order/time interval; never fabricate clock times to satisfy Python. M1 currently holds such events.
3. Independent object discovery needs supplementary lexical candidates plus semantic checking and labeled gold recall. A static noun lexicon cannot guarantee exhaustive discovery.
4. JEV's 17 supported labels are uncalibrated evidence, not accuracy or canon authority. Argument-free LEARN_FACT cannot be considered an executable state mutation.
5. Writer fact claims were not canonical fact_id references. Establish knowledge and epistemic authority before committing.
6. Nine-scene M4 qualification is NOT started until these gaps are addressed.

### Targeted offline protection added

The experimental M2 reconciliation layer now accepts an optional, versioned noun-candidate lexicon. It flags previously unreported objects as UNREPORTED_OBJECT_CANDIDATE, with source text span, and treats them as HOLD findings; JEV question builder can include these omissions as new semantic candidates. The new code never silently adds them to state.

This document records observational evidence, not a successful production acceptance. Prior runs and evidence are preserved and no V4/V4.1/V4.2 production pipeline was modified. The separate object-history/weather backlog remains [Issue #303](https://github.com/necdetoskay/lumi-model-lab/issues/303).
