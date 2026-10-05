Audit the current story against approved_plan and audit_contract. Source quotes are
authoritative in their original language. Do not translate them into extra requirements.
Return exactly one requirement_check for every supplied ID, with evidence and reasoning
FIRST and assessment LAST. Do not infer defects from the mere existence of a check.

Obligation meanings:
- PRESERVE_FACTS: do not contradict established facts, powers, geography or limits.
  Background context need not be mentioned on stage merely because it is supplied.
- PRESERVE_OUTCOMES: preserve approved outcomes and prohibitions. Do not invent rewards,
  routes, equipment, powers or resolutions that bypass the approved causal chain.
- SHOW_APPROVED_ACTION: enact the approved causal action in its scene order. Incidental
  wording can vary; omissions of required causal actions are material, prose polish is not.
- SCENE_END_STATE: the scene reaches its required state before later approved events.
  A later state change explicitly planned in the next scene is not a contradiction.
- ACTUAL_STORY_END: compare the ACTUAL last paragraph/image with the approved final state.
  An earlier closing image followed by a different ending does not satisfy this check.

Use supplied reader_age and output_language; do not assume a fixed age or language.
Length is minimum-only. Reader guidance is not a checklist of mandatory background mentions.
An explicit contradiction or missed causal action is MATERIAL_VIOLATION; optional style
advice is ADVISORY. A failed attempt does not imply success. Unspecified details are not
constraints. Never invent a flaw to justify an edit or relax a required event into plot similarity.

SATISFIED needs exact contiguous evidence from one cited story span, no repair spans.
MATERIAL_VIOLATION needs exact evidence and all necessary repair span IDs (maximum 24).
Do not stitch quotations, paraphrase evidence or invent span IDs. If the required event is
absent and you cannot cite grounding evidence or classify confidently, use UNCERTAIN,
with no repair spans. Uncertainty never authorizes rewrite or acceptance.
Put additional real defects, advice or verification in observations; classification LAST.
DEFECT_* requires actual material impact. A withdrawn defect or positive confirmation is
VERIFIED, not a defect. Do not duplicate requirement violations in observations.
Before classification, trace each plot-important object and surviving fragment across
possession, transfer, loss and the ending. A late assertion that a fragment "somehow"
remained does not establish continuity if earlier prose transferred that same fragment.
Distinguish a plausible incidental detail from a missing causal link required to explain
an object used in the approved ending. Report an independent object-state defect in
observations as state_continuity, even when a separate ending requirement also fails.

For every SHOW_APPROVED_ACTION, compare ALL binding sub-actions in its source quote:
relative positions, direction of transfer, physical assistance and access limits matter
when explicitly specified. A broadly similar rescue does not satisfy a different
required position or omitted handoff. Do not manufacture constraints not in the source.

Keep reasons concise (one or two sentences). Copy a short literal quote from EXACTLY
one span and copy that span's ID from the same wire-table row. Do not cite a neighboring
sentence instead. A single excerpt can ground a contradiction, but include every
necessary bounded repair target, including an earlier setup span if continuity needs it.
Return only JSON matching the supplied schema. The prose wire is reconstructed from each
span's whitespace_before + current_text, followed by trailing_whitespace.

Requirements now split source scene text at punctuation; parent_source_quote supplies
context only. Assess EACH source_quote independently, not whether its parent scene
generally works. SATISFIED requires the specific stated action/condition to hold. A
wrong explicit quantity, relative position, location or direction is a material
contradiction even if the broader outcome is similar. Never downgrade an explicit
contradiction because the ending or rescue still works emotionally. Guidance, negative
constraints and rhetorical choices retain their original meaning; do not turn them
into literal spoken lines or force background mentions. For ACTUAL_STORY_END clauses,
follow the source's meaning: a stated final image must itself be the actual last image;
other ending outcomes can be established nearby without every clause appearing in
the last sentence. A past mention cannot satisfy a simultaneous condition required
in the actual final image. Keep each reason to ONE short sentence and quote to a
short exact substring, typically fewer than 20 words. Check source span IDs carefully.
