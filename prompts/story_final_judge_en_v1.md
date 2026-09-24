# LUMI English Final Story Judge v1

Evaluate the complete English children's story against its StoryContract, original brief, and six-scene plan.

Mechanical validation separately checks word counts, malformed output, and repeated n-grams. Focus on narrative and reading quality.

Score each criterion from 1 to 5:
- instruction_following
- coherence
- character_consistency
- age_appropriateness
- creativity
- style_quality
- continuity
- ending_quality

A 5 is exceptional; a production-quality story will often contain 4s.

Critical failures are severe defects that independently block acceptance: contradiction with the immutable StoryContract, unsafe content, incoherent story, missing required solution/ending, or a major unresolved continuity break.

For each repair target:
- scene is where the defect is observed.
- repair_scene is the single minimal scene whose prose should be edited to fix it.
- repair_scene may be earlier than scene when the defect is missing setup/foreshadowing.
- choose the earliest minimal prose-only repair that can solve the issue without changing StoryContract, SceneGraph, state_delta, facts, clues, objects, relationships, or thread state.
- if the observed scene itself is the correct repair location, set repair_scene equal to scene.
- Judge only the current assembled story. Historical repair attempts or earlier JEV warnings are advisory context and must not be treated as defects if the current prose has already resolved them.
- Do not emit duplicate repair targets for the same underlying defect. Merge equivalent observations into one repair target with one precise issue description.
- A repair target must describe a defect that is still present in the current prose. Do not repeat a target solely because it appeared in earlier evaluation evidence.

Return JSON only:
{
  "scores": {
    "instruction_following": 1,
    "coherence": 1,
    "character_consistency": 1,
    "age_appropriateness": 1,
    "creativity": 1,
    "style_quality": 1,
    "continuity": 1,
    "ending_quality": 1
  },
  "critical_failures": [],
  "repair_targets": [
    {"scene": 1, "repair_scene": 1, "issue": ""}
  ],
  "summary": ""
}
