# Story Judge Prompt v0.1

Evaluate the candidate Turkish children's story against the supplied brief.

Score each criterion from 1 to 5:

- instruction_following
- coherence
- character_consistency
- age_appropriateness
- creativity
- style_quality

For every score, provide one concise justification based on observable text evidence. Do not reward verbosity. Do not infer requirements that are absent from the brief.

Return structured JSON only, using this shape:

```json
{
  "scores": {
    "instruction_following": 1,
    "coherence": 1,
    "character_consistency": 1,
    "age_appropriateness": 1,
    "creativity": 1,
    "style_quality": 1
  },
  "reasons": {
    "instruction_following": "",
    "coherence": "",
    "character_consistency": "",
    "age_appropriateness": "",
    "creativity": "",
    "style_quality": ""
  },
  "critical_failures": []
}
```

This prompt is versioned and must remain fixed within one experiment comparison.
