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
    {"scene": 1, "issue": ""}
  ],
  "summary": ""
}
