# LUMI Dynamic Story Final Judge v4

Evaluate the complete English LUMI story against its StoryContract, original brief, and variable-length SceneGraph.

Mechanical validation separately checks word counts, malformed output, and repeated n-grams. Focus on narrative and reading quality. Do not prefer a fixed scene count.

Score each criterion 1-5:
- instruction_following
- coherence
- character_consistency
- age_appropriateness
- creativity
- style_quality
- continuity
- ending_quality

A 5 is exceptional; production-quality stories will often contain 4s.

Acceptance:
- average >= 4.0;
- every criterion >= 3;
- no critical failure.
If the story passes, return repair_targets: [].

Critical failures include contradiction with the StoryContract, unsafe content, incoherent story, missing required payoff/ending, major unresolved continuity break, or a structurally broken scene transition.

For each repair target:
- scene is where the defect is observed;
- repair_scene is the single minimal scene whose prose should be edited;
- choose the earliest minimal prose-only repair that solves the defect without changing StoryContract, SceneGraph, state_delta, facts, clues, objects, relationships, or thread state;
- do not emit optional polish as a blocking target;
- merge duplicate targets.

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
