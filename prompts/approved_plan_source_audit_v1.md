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
Return only JSON matching the supplied schema. The prose wire is reconstructed from each
span's whitespace_before + current_text, followed by trailing_whitespace.
