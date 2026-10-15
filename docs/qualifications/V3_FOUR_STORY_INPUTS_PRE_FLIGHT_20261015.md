# Final V3 four-story independent input qualification — 2026-10-15

## Scope and immutability
Target: four age-18 genre cases from issue #297. This branch is **isolated** and its PR #298 targets the laboratory's four-genre experimental branch, not `main`. No Final V3 runtime, prompt, model role, logic, cost guard, or production artifact was changed.

Canonical original frozen runtime SHA: `63e1e3ce82c244bc5bb02b0463a9a1a6715c941b`.

## New independent Saga Spine V2 inputs

| Genre | Character | Saga input |
| --- | --- | --- |
| Detective mystery | Mara | `four_genre_v3_inputs/closed_platform_saga_spine_v2.json` |
| Science fiction | Tavi | `four_genre_v3_inputs/orbit_rescue_saga_spine_v2.json` |
| Political intrigue | Sera | `four_genre_v3_inputs/council_seal_saga_spine_v2.json` |
| Fantasy adventure | Elen | `four_genre_v3_inputs/mirror_marsh_saga_spine_v2.json` |

Paths are relative to `data/specifications/story_lab/`. Each has **5 long-horizon anchors, 15 evidence-bound milestones**, alternative routes and strictly unresolved-by-design hidden causes. The first observation milestone is a real reference to the case's controlled-premise target. All additional world/character/state/premise inputs are independently specified, not reusing the old Forbidden Cartographer world.

## Real offline execution on ci-runner

A temporary independent checkout of this branch was created by the connected runner and removed after the test; no production tree changes. A temporary isolated Python virtualenv installed Pydantic v2, PyYAML and pytest.

- Four genuine `CharacterSagaSpineV2.model_validate_json` validations: **4/4 PASS**.
- Source-bound character/entry-milestone checks: **4/4 PASS**.
- Existing experimental four-genre router suite: **24/24 PASS** (retested after adding the Saga files, before final schema-valid matrix state).
- `verify_frozen_lane`: original Final V3 frozen runtime **43/43 PASS**.
- Models/providers: **0 real POST**, spend **$0** for this preparation, **0** new Writer stories, **0** translations.

## Next boundary

`real_spine_eligible=true` means **schema-qualified inputs**, not a provider authorization. The matrix separately records `provider_dispatch_authorized=false`. The four paid Spine Architect/Gate attempts still require each case's authenticated one-use stage-scoped grant, a bounded aggregate budget and a protected execution path. All 4 Spine outputs must pass deterministic and Luna checks then stop for genuine human creative approval before Aion Writer. No automatic retries, no fallback, no human/assistant edits to generated English or Turkish, no Canon/WorldState commit and no publication. If the first model or authority step fails, record STOP rather than a synthetic success.
