# Joint movement / Q11 preparation

Q10 accepted six scenes but editorial reading found separate carrier/object crossing sentences mechanical. `CarryGroupV1` and `JointMoveV1` now bind declared carriers and one carried object to a single observed shared crossing. The v4 spatial contract includes the full group definition; one JOINT_MOVE predicate and one grounded passage cover the complete group. Writer/guard receive the same definition, with explicit instructions to reject serial crossings, omitted members, broken hold or independently moving objects.

Local replay requires canonical carrier/object position bindings, exact established `carried_by` membership, co-location, a declared connected edge permitting every participant, and no active constraint blocking any participant. All checks precede one complete position update. Individual MOVE cannot split an active group; overlapping groups, aliases and undeclared established shared carrying fail closed. Quote presence is not semantic proof; the guard assesses whether prose actually describes joint movement.

The v4 engine and entry are versioned separately so recorded Q9/Q10 source fingerprints remain valid. Existing contract, state, semantic guard and shared reservation machinery is reused. The common offline verifier supports v2/v3/v4. The new paid workflow is manual-only and requires a registered explicit grant; it has not run.

Q11 keeps Q10's frozen canon, story intent, initial StoryState, spine route and goal texts. Only movement specifications, coverage references and prompts change. Three individual MOVE events become one JOINT_MOVE on each crossing scene S04–S06. The deterministic expected terminal state matches Q10 exactly. All six scenes would be generated fresh from revision 0; no accepted prose or state is reused or rewritten. Q10 remains immutable accepted evidence with its editorial warnings.

This version requires a shared hold already established in the scene entry state. It does not model starting/ending a hold midway through spatial operations. Q11 establishes the hold in S03, moves jointly in later scenes and places the object after its final movement. More general carry lifecycle operations remain future work.

Prepared evidence: `SFR-V1-Q11-PREFLIGHT-20261008/`. Proposed new envelope: at most 24 OpenRouter calls / USD 0.60, USD 0.15 per call, GPT-5.6 Sol writer + Sonnet 5.5 guard, one rewrite per scene, no retry. No new authority has been registered and no model call made. Prior grants are CLOSED. Fresh explicit budget/data/secret-access approval is required before shared admission.

Synthetic execution, replay and negative controls establish mechanics only. Live qualification still requires paid execution, offline evidence replay and assembled prose review. Production LUMI and PR merging are outside scope; PR #264 remains draft.

Validation: 348 local Relay tests PASS. Joint atomic replay, nine negative movement controls, synthetic six-scene execution/offline replay and ambiguity stop at revision 3 pass. Historical Q9/Q10 replay remains valid. Staged source fingerprints and LF/CRLF simulations match the frozen Q11 preflight. No new provider calls.
