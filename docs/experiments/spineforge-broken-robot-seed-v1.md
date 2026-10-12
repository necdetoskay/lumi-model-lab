# Broken robot: frozen starting state and comparison

The user's selected SCENARIO-03 is preserved with all ten original suggestions in tests/fixtures/story_scenarios_v1/catalog.json. These are future test candidates, not golden verdicts. The selected Turkish synopsis is retained exactly in broken-robot-request.json.

## Frozen baseline

broken-robot-seed.json defines the initial characters, world, objects, spatial topology, canon, resource policy, open threads and narrative obligations. broken-robot-frozen-seed.json stores the complete canonical snapshot plus canonical and exact-byte fingerprints. Freeze creation and experiment output are exclusive: no overwrite/reopening. Seed verification is mandatory before planner preparation. Any byte replacement or canonical state change is rejected against the saved baseline. Git history retains the original freeze; legitimate new conditions require a new seed version and experiment, not modification of this baseline.

Fingerprint: 7c321d5a19f244d3ae05735d3d83a95ee2e9733bfc870560e6f0b97d4c818034.

Ada and Bora are 12-year-old classmates/project partners in the school workshop. Ada is anxious and wants to present; Bora is defensive and wants to understand the failure. Mutual trust is strained. They know yesterday's robot worked and today's exhibition is approaching, but neither knows the diagnosis. Ada has basic programming experience; Bora has basic assembly experience.

The contemporary school exhibition opens in twenty minutes. Workshop and exhibition hall have one established bidirectional indoor connection. The robot, a small toolkit and project notebook are present. The battery is charged and the program loaded; the robot is inoperative due to a loose motor connector. That object fact does not automatically become character knowledge. No magical fixes, unexplained replacement robot or adult solving the whole problem. A successful honest presentation can follow either a repair or a justified alternative; the final solution is not prewritten.

Ages, Turkish language, six scenes, available resources, underlying fault and time pressure are recorded design assumptions. They extend the short synopsis and are not claims about actual production LUMI data. State structures reuse Relay character/object/world contracts; production LUMI integration is not performed.

## State-bound planning

Versioned src/spineforge_seeded_design.py and its prompt extend the previous offline admission without changing its module or historical Relay fingerprints. Planner input v2 supplies the complete frozen seed and both request/seed hashes. StoryDesign v2 must preserve story ID, initial state, character canon, topology and resource policy exactly. Planning creates spine/intent hashes later; the seed has no invented placeholder hashes. Projected changes remain separate from accepted story state.

Preparation: `python -m src.spineforge_seeded_design --request REQUEST --seed SEED --freeze FROZEN --output FRESH_DIRECTORY`. Add `--proposal PROPOSAL` to validate a produced plan. The current recorded experiment is READY_FOR_PLANNER, not a generated plan/story. No paid authority is created.

## End comparison

After a complete accepted story experiment, use `python -m scripts.spineforge_compare_seed_state --seed SEED --freeze FROZEN --fixture FIXTURE --records STORY_RECORDS --output NEW_REPORT.json`. It verifies the frozen seed, checks exact starting-state identity and independently replays the story's requests, guard results, scene freezes and accounting before comparing the last accepted state. A rejected/incomplete story cannot be presented as a final comparison. The new report is exclusive and includes before/after JSON pointers, seed/final hashes and revisions.

Expected areas to inspect are robot operation/diagnosis/presentation, Ada/Bora knowledge and relationship changes, locations, world state, thread resolution and obligations. No robot ending or expected final-state values have been invented. The comparison mechanism is tested with recorded Q12 evidence as a separate adapter control; it does not substitute for the new robot story. State differences are evidence of changes, not literary or semantic quality by themselves.

All ten summaries, selected seed/request/freeze and prepared planner input are committed. No provider calls, production edits or merge.

Latest frozen preparation: SFR-ROBOT-SEED-READY-20261009. Earlier PREPARED/FROZEN source-bound snapshots remain preserved as development records. All three use the same unchanged seed fingerprint. The initial-state template is a deep copy, so a planner modifying its working copy cannot mutate the in-memory baseline.
