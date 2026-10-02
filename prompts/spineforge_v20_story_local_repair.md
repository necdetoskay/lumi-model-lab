# SpineForge v20 — Bounded Finished Story Local Repair

You receive a finished story and confirmed LOCAL_REPAIR findings.

Return one JSON object:
{
  "replacements": [
    {"old": "exact text copied verbatim from the story", "new": "minimal corrected text"}
  ]
}

Hard rules:
- Every "old" string must occur exactly once in the supplied story.
- Make only the smallest wording/span changes needed to fix confirmed findings.
- Do not rewrite surrounding prose.
- Do not add or remove scenes, beats, discoveries, characters, clues, choices, or outcomes.
- Do not alter canon, reveal limits, age target, or the selected Spine path.
- One exact replacement per defect is preferred.
- Never perform structural repair or replanning here.
