# Story Judge Prompt v0.2

Evaluate the candidate Turkish children's story against the supplied brief.

The deterministic pipeline separately checks mechanical validity such as exact word-count compliance, truncation/EOS, repetition, malformed output, and other machine-checkable constraints. Do not duplicate those checks unless the failure materially harms the reading experience or violates an explicit story requirement.

Score each criterion from 1 to 5 using the anchors below. A score of 5 is exceptional, not merely acceptable. A solid production-quality story will often contain 4s.

## instruction_following
Judge whether the story fulfills the brief's narrative requirements, premise, required sequence, roles, and explicit constraints.
- 5: fulfills all meaningful narrative instructions cleanly and naturally; no important omission or contradiction.
- 4: fulfills the brief well with only a minor omission, weak execution, or small deviation.
- 3: broadly follows the brief but misses, weakens, or contradicts at least one important requirement.
- 2: multiple important requirements are missed or substantially altered.
- 1: largely ignores or contradicts the brief.
Do not lower this score only because deterministic word-count tolerance failed; word count is scored outside the LLM judge.

## coherence
Judge causal logic, setup/payoff, scene continuity, motivation, and whether introduced elements have a useful role.
- 5: clear causal progression; setups pay off; motivations and transitions feel natural; no meaningful loose or contradictory elements.
- 4: coherent overall with one or two minor conveniences, unused elements, or abrupt transitions.
- 3: understandable but contains noticeable causal gaps, unnecessary setup, weak payoff, or contrivance.
- 2: several confusing or inconsistent developments.
- 1: difficult to follow or substantially self-contradictory.

## character_consistency
Judge whether the protagonist and supporting characters behave consistently with stated traits, knowledge, goals, and prior actions.
- 5: behavior, choices, emotional reactions, and learning are fully consistent and convincingly motivated.
- 4: mostly consistent with only a small convenience or underdeveloped reaction.
- 3: one noticeable inconsistency, unexplained shift, or weakly motivated action.
- 2: repeated or major inconsistency.
- 1: character behavior is fundamentally incoherent.

## age_appropriateness
Judge only developmental fit: language complexity, sentence load, concepts, emotional intensity, fear/danger, and whether the material suits the specified age range.
- 5: exceptionally well calibrated to the target age in language, concepts, emotional safety, and cognitive load.
- 4: appropriate overall with minor complexity, intensity, or simplification issues.
- 3: usable but noticeably too complex, too simple, too intense, or developmentally mismatched in places.
- 2: substantial age mismatch or repeated inappropriate intensity/complexity.
- 1: clearly unsuitable for the target age.
Do not use this criterion to punish generic writing, moralizing, or low creativity; those belong under creativity/style_quality.

## creativity
Judge story-specific imagination, memorable motifs, non-generic choices, and whether the solution/dramatic structure feels particular to this story rather than templated.
- 5: distinctive, memorable, and story-specific without becoming confusing or age-inappropriate.
- 4: contains several fresh or charming choices and avoids feeling generic.
- 3: competent but familiar, predictable, or template-like.
- 2: highly generic or derivative with little story-specific invention.
- 1: almost entirely boilerplate or incoherent imitation.

## style_quality
Judge prose quality for a children's story: natural Turkish, rhythm, imagery, economy, read-aloud quality, emotional subtlety, and avoidance of LLM-like exposition.
Penalize explicit moral-of-the-story sentences, over-explaining what the child should learn, unnecessary adult praise/validation, repetitive lesson statements, inflated language, awkward phrasing, and telling the meaning after the story has already shown it.
- 5: polished, natural, vivid, economical, age-suitable prose with strong read-aloud quality and no notable didactic or LLM-like residue.
- 4: strong prose with minor awkwardness, over-explanation, or generic phrasing.
- 3: readable but noticeably didactic, formulaic, overwritten, flat, or awkward in multiple places.
- 2: frequent style problems that reduce enjoyment or clarity.
- 1: poor or unusable prose.

## Critical failures
Use `critical_failures` only for severe defects that should independently block acceptance, such as unsafe content for the target age, major contradiction with the brief, incoherent/unreadable story, or a missing required ending/structure. Do not use it for ordinary score-level weaknesses.

## Calibration rules
- Use the full 1-5 scale.
- 5 means exceptional evidence in the text, not "no obvious problem."
- Do not reward verbosity.
- Do not infer requirements absent from the brief.
- Keep each reason concise and evidence-based, ideally one sentence and under 30 words.
- Distinguish the criteria: do not move a style problem into age_appropriateness or a mechanical word-count issue into instruction_following.

Return structured JSON only, using this exact shape:

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
