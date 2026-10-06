Audit the current story against the entire approved native-language plan. Read each
numbered source requirement in parent context, and the complete story through its last
sentence. Return reviewed_requirements containing each requirement number exactly once.
Coverage is a commitment to having checked the whole requirement, including subordinate
clauses, NOT a positive verdict. Multiple facts in one requirement must all be checked.

Look first for explicit differences in quantities, relative positions, possessions, causal
actions, and simultaneous actions. For every action involving two characters compare WHO,
WHERE, distance/direction, and WHEN with the corresponding story event. Do not substitute
"the general rescue works" for the exact required relative position. Read both the rescue
and the subsequent movement; a later movement may contradict a required position.

For important objects, trace the object and any surviving fragments separately: before,
transfer/break, after, last appearance. Quote both source states for an internal conflict.
Do not invent an unstated destination or physical impossibility. A broken object can leave
a fragment attached to a person. "Stayed behind" is relative to the departing object unless
the text explicitly establishes a different location. Do not infer "long" from "spiral", or
infer a dropped object merely from "let go" when the surrounding prose locates it in a pocket.
An action may be performed while moving without the literal word "while". Ordinary coherent
prose is not a defect. Require a real contradiction, not a stricter story of your own invention.

For each material finding provide:
- source_requirements: numbered plan requirements actually contradicted (empty for a wholly
  internal continuity contradiction).
- evidence: short EXACT story quotes with their own source span IDs. The quoted states and
  source requirement must support the claimed contradiction. Search for any intervening
  bridge that resolves it before deciding it is a defect.
- span_ids: ONLY sentences that need editing, not every sentence used as evidence. Preserve
  valid earlier setup when a later conflicting sentence can be fixed. exact_text must be
  an exact quote within one repair target AND one evidence witness for that target.
- reason: explain the incompatible facts and their consequence, including the absent bridge.

Read the ACTUAL last image for required closure actions. Earlier nearby prose cannot
substitute for it, but do not reject a last sentence that actually carries out the action.
Background facts need not be stated. Stylistic preferences belong in advisory_notes only.
If material evidence is genuinely ambiguous, use unresolved_material_issues; it authorizes
neither acceptance nor repair. Do not invent findings to satisfy the request. Use the JSON
schema. The story is reconstructed from whitespace_before + current_text in span order,
then trailing_whitespace. Prior model conclusions are deliberately not supplied.
