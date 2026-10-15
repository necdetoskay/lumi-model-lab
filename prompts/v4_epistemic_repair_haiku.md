# LUMI V4.1 — Evidence-Calibrated Reversal Repair (Haiku 4.5)

You receive an Episode Spine already valid under the complete deterministic
contract, and a separate Luna reviewer verdict REPLAN. Your goal is NOT
to rewrite the narrative; it is to remove unearned epistemic certainty
from the reversal using the exact source beats as evidence.

Return ONLY:
{"patches":[{"field":"reversal.evidence[0].claim","value":"corrected claim"}, ...]}

Permitted fields ONLY:
- reversal.evidence[N].claim (existing N; revise source-backed meaning)
- reversal.evidence[N].certainty (only weaken OBSERVED -> INFERRED/HYPOTHESIS, or INFERRED -> HYPOTHESIS)
- reversal.reinterpretation
- reversal.inference_ceiling
- reversal.unresolved_after_reversal

Produce between 1 and 6 patches. Each field at most once.
Never claim that a hypothesis has been proved by a missing observation.
Never introduce a new fact, location, timeline, participant, cause, record,
physical mechanism, instrument outcome, branch, world state or evidence item.
Never move a beat, rename a key or alter its meaning. Do not add false evidence
to make a strong claim true. Weaken the claim to match existing cited beats.
Do not alter branch choices, decision outcomes, or story facts.
If a Luna concern cannot be resolved within these fields, do not invent a
solution; return a patch which explicitly states the limit of knowledge.
Luna will independently re-evaluate the whole result, and can still reject.

Do not mark PASS. A model-authored patch is a proposal, not verification.
