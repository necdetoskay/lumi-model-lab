# SERA v0.38 — SQLite story scene handoff: two-scene synthetic rehearsal

**LAB ONLY / SOURCE-CONSTRAINED REHEARSAL / NO LIVE MODEL or G2 CANON AUTHORITY.**

This is the next story-first increment after v0.37. It uses:
- ScenarioLab.scene_inputs to load the exact SQLite world revision and separate focal writer context from validator-only complete world state;
- the existing v0.6 sentence scanner and assurance audit;
- the existing v0.25 relation/knowledge preview for custody transfer and v0.24 spatial preview with v0.5 temporal constraints for movement;
- the existing v0.2 deterministic reducer/WorldStore SQLite transaction for a **fixture-authorized simulation commit only**, after checking physical parity with the preview.

## Actual two-scene path

Scene 1, Mara: "Mara handed the pocket-watch to Elin." The registered watch holder moves Mara -> Elin while its owner stays Mara. Both characters share the workshop. Scene 2, Elin: "Elin carried the pocket-watch into hallway." The registered route workshop -> hallway requires at least three minutes; the watch moves together with its new holder. Elin enters scene 2 against the **updated revision** after scene 1, not a separate copy of an old character world.

This exercises cross-character shared physical truth, item custody, location, minimum-route time, scene-to-scene CAS, private knowledge isolation, reboot/replay and rollback. The SourceEvent and exact Event fingerprint grants are **separate synthetic test fixtures**, NOT external model responses or production signatures.

## Hard safety boundaries

- One exact sentence with one source-attached observed physical event per scene in this initial pilot; fail on extra unreconciled prose rather than implying full recall.
- Source and reducer event IDs must match. Source quote exact codepoint span, documented lab evidence_ref tied to source SHA, actor and registered item all checked by existing preview. A reported assertion is NOT a physical event.
- SQLite-provided registered routes cannot be replaced by a model's custom travel table. The selected simulation minute must fit the temporal domain; it is NOT claimed to be stated by prose.
- v0.6 sentence assurance intentionally remains **HOLD**: independent semantic completeness is NOT proven. Test-fixture simulations can still be persisted within the isolated SQLite lab using only an external test fixture grant. This must never be reused as approval for a production or G2 write.
- Physically compared pre-commit v0.2 reducer state and source-bound v0.24/v0.25 preview must agree; mismatch fails closed before any DB mutation.
- The implementation does NOT call StoryForge, OpenRouter, Haiku, Gemini, LUMI production DB, an external provider, or canonical publisher. 0 paid calls, 0 production writes, no user-forbidden model-output token ceiling.
- A real story worker must separately acquire independent semantic, epistemic and world source authority, authenticated G2 scope, durable paid-request recovery and native CAS publisher. Frozen Mara original S1 remains HOLD; these are invented **synthetic** Mara/Elin tests, not canonical story acceptance.

## Test coverage

test_story_scene_rehearsal_v038.py tests the real v0.6/v0.24/v0.25 implementations and v0.2 SQLite world replay together across two different story runs, including program restart. Regression negatives cover absent synthetic grant, reported-only action, fabricated quote, second omitted sentence, route tamper, stale revision, wrong previous holder, incomplete registered aliases and infeasible travel time. The root SERA self-hosted offline suite runs these tests and Chromium reviewer E2E; check each CI run independently before claiming PASS.

## Next concrete increment

Extend independent blind extractor evidence, complete multi-event per-scene source coverage and automatic finite repair/re-extraction under a fully synthetic model-provider test double, then feed these source/scene gates into the existing composed StoryForge scene runner with the **writer-context-only** disclosure boundary. Do not silently turn a fixture rehearsal into a paid or production release.

[Tracking Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
