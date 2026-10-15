# P4.16 — Real state/topic variability input bridge (not model execution)

**13 October 2026** — [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275), [Issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291).

## Problem fixed in this slice

P4.8–P4.14 were pinned to one editorially rewritten 2,491-word story, age 12, and a provisional S167–S203 scene. That same-story quality adapter is useful for its original source but does **not** establish any capacity to process different canonical states, topics and ages. Users now require >=90% real E2E success across varied inputs, with no manual story edits.

P4.16 reuses P4.15's **ten genuine different input definitions** to compile an immutable input **pack** and deterministic SpineForge/Writer **prompts**. All inputs carry independent hashes of canonical state, topic, full source, world time, protagonist, known locations, open obligations, explicitly unknown facts, reader age and target length. The pack can be reproduced bit for bit. Changing any source or target after freeze fails closed. Nothing in P4.8's frozen v21 quality gate, approved Spine or manuscript is changed.

### Handoff design

1. `compile_case(case)`: validates canonical state and topic; produces SHA-linked input pack with no guessed object owners or unknown locations and preservation of all open obligations.
2. `build_spine_request(pack)`: makes a state-specific **character-driven creative planning** prompt. It asks the planner for 4–8 causal beats and explicit obligations, not rigid generic engineering events. JSON output is planned with no provider invocation.
3. `approve_spine_for_writer(pack, spine)`: rejects wrong input SHA, wrong initial physical location (teleportation), unknown declared locations, missing obligation reference, empty cause/effect and nonsequential scene IDs. This is **light structural pre-validation**, NOT the genuine original independent SpineForge semantic ACCEPT.
4. `build_writer_request(pack, spine)`: verifies immutable scene-hash lineage and passes the **actual topic, Canon state, dramatic beats, age targets, unknown facts and forbidden inventions** to the Writer with a narrative/roleplay prompt; disallows any claim of real model output, genuine acceptance or Q25/State authority in offline mode.

P4.16 tests all ten P4.15 cases, source and topic perturbations, cross-state Spine swaps, fake unknown destinations, broken obligation lineage and accidental word-profile rewrites.

## Stop conditions and next reality checks

- The compiled prompts are **not story outputs**; no model was called, all offline status flags show `live_spineforge_connected=false`, `live_writer_connected=false`, `independent_quality_accepted=false`. No manufactured prose, old 12-year-old story or synthetic provider callback is counted toward 90%.
- This light input bridge is **not an alternative/duplicate LUMI production generation engine**. The next slice must connect to actual pinned SpineForge and Writer model execution + immutable artifact persistence, then v21 Quality → Master → actual same-story Q25 → evidence-linked State, without relaxing original approved rules.
- Real paid generation cannot start before an **isolated OpenRouter API key** with provider-side remaining budget matching a finite authorization has been configured in secure environment, original stage budget discrepancy addressed, live transport genuinely verified and secrets/financial receipt safe. This shell cannot access an OpenRouter limited key. Total user-authorized new model budget is **$10**, across ALL model stages and all attempts combined; no automatic API retries.
- If an issue arises with this generalized source-anchored approach, fix its root cause up to three distinct tested attempts before proposing another architecture. Never silently change frozen v21 code, production, or strong acceptance standards.

**Acceptance of P4.16 is ONLY input/lineage compiler GREEN** on ten varied scenarios. The first real model-generated story E2E, its sampled quality and >=90% success are still unverified.
