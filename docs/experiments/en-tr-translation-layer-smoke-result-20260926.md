# EN→TR Translation Layer Smoke Result — 2026-09-26

Status: **SMOKE PASS / NOT YET BROADLY QUALIFIED**

## Objective

Evaluate a dedicated final translation layer for the English-first Story V5 pipeline without generating new stories.

Source story:
- writer: `aion-labs/aion-3.5-mini`
- source run: `36257356137`
- language: English
- exact age: 4
- raw source length: 501 words
- source serious/critical semantic audit: clean

## Translation candidates

One frozen English source story was translated under the same strict **translate, do not rewrite** contract.

| Label | Model | Observed translation cost | Blind evaluator result |
|---|---|---:|---|
| A | `google/gemini-3.8-flash` | $0.0138555 | PASS — 0 critical / 0 serious / 0 moderate / 0 minor |
| B | `qwen/qwen3-max` | $0.00448968 | FAIL — 1 serious / 4 moderate / 2 minor |
| C | `qwen/qwen3-30b-a3b-instruct-2507` | $0.0002295243 | FAIL — 3 serious / 8 moderate / 4 minor |

Evidence run: `36259699082`

Blind evaluator:
- `openai/gpt-5.6-sol`
- model identities hidden as A/B/C
- evaluator cost: $0.063806

### Key findings

#### Gemini 3.8 Flash

The evaluator found:
- zero semantic fidelity defects,
- zero Turkish-quality defects,
- fidelity PASS,
- exact-age-4 Turkish PASS.

The translation preserved:
- Deniz identity,
- object identities,
- event order,
- wind → ring movement → tick causal rule,
- palm-generated air experiment,
- two-ticks-and-wait rhythm,
- the source story's open waiting-for-the-wind ending.

#### Qwen3 Max

The general story survived, but one publication-relevant state change occurred:
- source: the metal rings were **still and quiet** after the wind stopped;
- translation: the rings were described as **still/quiet while continuing to swing**.

This changes the physical state and weakens the story's central causal rule.

Additional nonblocking issues included unnatural `tik/tiklemek` sound rendering and translationese.

#### Qwen3 30B A3B Instruct 2507

Multiple serious fidelity failures occurred, including:
- third-person `he heard it` → first-person `duydum`,
- chair → boat-like `sandal`,
- hook → nail,
- central title concept `tick` → `titrek`.

This candidate is not suitable for this translation profile based on the smoke result.

## Cheap translation-fidelity gate

The same frozen source + translations were evaluated with a narrow semantic-fidelity-only gate:

Model:
- `openai/gpt-5.6-luna`

Evidence run:
- `36259940429`

Result:
- A / Gemini clean: **0 serious/critical findings**
- B / Qwen Max: correctly detected the serious ring-state shift
- C / Qwen 30B: detected multiple serious character/object/omission shifts
- result: **3/3 PASS**
- total cost across all three cases: **$0.003416**
- cost for the clean Gemini translation alone: **$0.000681**

## Important distinction: Luna story gate vs translation-fidelity gate

Do **not** generalize this result into “Luna is a reliable story-quality gate.”

Story-gate evidence in the same session showed prompt/decision instability:
- one cheap-gate prompt caught N1 + N2 and left the English Aion Mini story clean,
- a Turkish N5 clean guard then produced a false-positive `response_causality`,
- the canonical checklist prompt kept N5 clean but missed N1 and N2.

Therefore:
- **Luna story-quality gate: not qualified**
- **Luna narrow translation-fidelity gate: promising smoke PASS**

The narrow fidelity task is materially simpler: compare source vs translation for semantic drift rather than judge the story itself.

## Current candidate pipeline

The evidence from this smoke supports testing the following architecture further:

```
StoryContract + Story Spine
        ↓
English story writer
Aion 3.5 Mini candidate
        ↓
English semantic QA / escalation
[story-gate model still unresolved]
        ↓
final accepted English story
        ↓
EN→TR translation
Gemini 3.8 Flash candidate
        ↓
narrow EN↔TR fidelity gate
GPT-5.6 Luna candidate
        ↓
Turkish delivery
```

## Decision

For the exact-age-4 / ~500-word profile:

- `google/gemini-3.8-flash` is the **current EN→TR translation candidate**.
- `openai/gpt-5.6-luna` is the **current cheap translation-fidelity gate candidate**, but only for the narrow source-vs-translation decision.
- Qwen3 Max and Qwen3 30B A3B are not selected from this smoke.
- No global production qualification is claimed from one source story.

## Next qualification step

Do not expand immediately into a large corpus.

The next useful translation qualification should reuse a **small number of already accepted English stories with different narrative characteristics** and verify that Gemini translation + Luna fidelity gate remains stable.

Until then, keep this result as a candidate profile, not a production default.
