Evaluate the current English story independently against approved_plan AND binding_requirements.
Write exactly one requirement_check for EACH supplied requirement ID. These are binding,
not stylistic suggestions. Compare the specified actual event/image with the actual text.
FIRST identify evidence and explain what happened; THEN choose the final assessment:
SATISFIED, MATERIAL_VIOLATION or UNCERTAIN. Generate assessment last in each row.
Do not commit to a defect before examining the evidence. If your reasoning discovers
no defect or withdraws a supposed defect, use SATISFIED, not MATERIAL_VIOLATION.
A violated explicit binding requirement is a material defect even if otherwise plausible.
Do not relax required entry/exit topology or the literal actual closing image into broad
plot similarity. Read the last paragraph and all dialogue AFTER any earlier closing image.
For MATERIAL_VIOLATION select ALL necessary repair_span_ids (up to 24) and quote one exact
contiguous excerpt from one cited evidence span. No paraphrases, ellipses or stitched quotes.
For SATISFIED set repair_span_ids=[]; the evidence can cite the relevant actual passage.
UNCERTAIN requires clarification/another audit; it never authorizes a story rewrite.

Then put additional observations in observations. Examine evidence/reason FIRST and choose
classification LAST: DEFECT_SCENE / DEFECT_STRUCTURAL / DEFECT_REPLAN / ADVISORY / VERIFIED.
Only DEFECT_* observations require story edits and must explain actual material_impact.
Never classify a resolved issue, withdrawn defect, positive confirmation or optional prose
polish as DEFECT_*. Advice/verification may have empty material_impact and exact_text.
Do not duplicate binding-requirement violations in observations.
An empty observations array is allowed; you need not invent notes or flaws.

Additional material defects include contradictions breaking causality/continuity or rescue
feasibility; age-inappropriate content; new powers/equipment/rescue routes; altered approved
outcomes. Mild ambiguity whose intended action is clear, style, redundancy, unshown ordinary
movements, and incidental background are advisory. A snapped cord may remain tied to a wrist.
A failed attempt does not imply success. Unspecified dimensions are not constraints.
Ordinary companionship is not a replacement material reward. Earlier findings may be wrong;
judge the current text. Do not invent a new defect to justify an edit. Ignore historical upper
word targets: length is minimum-only. Reader age is 12. Return JSON only.
Wire prose: concatenate whitespace_before + current_text, then trailing_whitespace.
