# StoryForge RC1 Callable Smoke Result — 2026-09-26

Status: **PASS**
Profile: `LSF-A4-W500-v1.0-rc1`
Workflow run: `36267804926`

## What changed

This run exercised the qualified StoryForge stack through one callable entrypoint:

```python
from src.storyforge import run_storyforge

result = run_storyforge(request)
```

The smoke did not manually chain experiment scripts.

## Input

Request:
- exact age: 4
- target words: 500
- family: friendship / emotional-social
- deterministic direct refs:
  - `relationship.ada`
  - `location.chalk_box`
  - `world.physics_normal`
- hard relationship constraints preserved

## Context Builder

JEV soft enrichment selected:
- `inventory.blue_chalk`
- `inventory.yellow_chalk`

Review only, not sent to planner:
- `inventory.toy_truck`
- `location.cardboard`
- `saga.explorer`

Forbidden facts sent to JEV: **false**

## Planner

Planner:
- `aion-labs/aion-3.5-mini`

Plan gate:
- deterministic errors: 0
- Sonnet serious/critical defects: 0
- PASS

The planner independently created a red-chalk bridge solution.
No adult mediator, prior feud, relationship history, or moral was supplied or invented.

## English story

Writer:
- `aion-labs/aion-3.5-mini`

Final English:
- 489 words
- hard range PASS
- primary Sonnet audit: 0 findings
- secondary Sol audit: 0 findings
- bounded repair: none

## Translation

Translator:
- `google/gemini-3.8-flash`

Fidelity:
- `openai/gpt-5.6-luna`
- serious/critical findings: 0
- PASS

Final runtime status:
- `publication_ready`
- `publication_ready=true`

## Cost / latency

Total:
- ~$0.05728
- ~110.4 s

This is qualification evidence, not a production SLA.

## Meaning

The StoryForge RC1 package can now execute its qualified A4/W500 flow behind a single request/result contract without weakening authority boundaries.

The remaining boundary is **not another story benchmark**.

Before Project LUMI integration:
1. freeze fail-closed request/result contract behavior;
2. verify invalid inputs and rejected plan/story states cannot leak into later stages;
3. preserve external StoryOutcome commit authority;
4. integrate through a separate L3 production change.
