# Joint movement / Q11 preparation

Q10 accepted six scenes but editorial reading found separate carrier/object crossing sentences mechanical. `CarryGroupV1` and `JointMoveV1` now bind declared carriers and one carried object to a single observed shared crossing. The v4 spatial contract includes the full group definition; one JOINT_MOVE predicate and one grounded passage cover the complete group. Writer/guard receive the same definition, with explicit instructions to reject serial crossings, omitted members, broken hold or independently moving objects.

Local replay requires canonical carrier/object position bindings, exact established `carried_by` membership, co-location, a declared connected edge permitting every participant, and no active constraint blocking any participant. All checks precede one complete position update. Individual MOVE cannot split an active group; overlapping groups, aliases and undeclared established shared carrying fail closed. Quote presence is not semantic proof; the guard assesses whether prose actually describes joint movement.

The v4 engine and entry are versioned separately so recorded Q9/Q10 source fingerprints remain valid. Existing contract, state, semantic guard and shared reservation machinery is reused. The common offline verifier supports v2/v3/v4. The new paid workflow is manual-only and requires a registered explicit grant; it has not run.

Q11 keeps Q10's frozen canon, story intent, initial StoryState, spine route and goal texts. Only movement specifications, coverage references and prompts change. Three individual MOVE events become one JOINT_MOVE on each crossing scene S04–S06. The deterministic expected terminal state matches Q10 exactly. All six scenes would be generated fresh from revision 0; no accepted prose or state is reused or rewritten. Q10 remains immutable accepted evidence with its editorial warnings.

This version requires a shared hold already established in the scene entry state. It does not model starting/ending a hold midway through spatial operations. Q11 establishes the hold in S03, moves jointly in later scenes and places the object after its final movement. More general carry lifecycle operations remain future work.

Prepared evidence: `SFR-V1-Q11-PREFLIGHT-20261008/`. Proposed new envelope: at most 24 OpenRouter calls / USD 0.60, USD 0.15 per call, GPT-5.6 Sol writer + Sonnet 5.5 guard, one rewrite per scene, no retry. No new authority has been registered and no model call made. Prior grants are CLOSED. Fresh explicit budget/data/secret-access approval is required before shared admission.

Synthetic execution, replay and negative controls establish mechanics only. Live qualification still requires paid execution, offline evidence replay and assembled prose review. Production LUMI and PR merging are outside scope; PR #264 remains draft.

Validation: 348 local Relay tests PASS. Joint atomic replay, nine negative movement controls, synthetic six-scene execution/offline replay and ambiguity stop at revision 3 pass. Historical Q9/Q10 replay remains valid. Staged source fingerprints and LF/CRLF simulations match the frozen Q11 preflight. No new provider calls.

## Q11 recorded result — 2026-10-08

Explicit Q11 submission/budget/secret-access approval was received. S01–S03 ACCEPT on attempt 1. S04 exhausted its single bounded rewrite and the run ended **REJECT_NON_CONVERGENT**, revision 3 / next S04. S05–S06 were never generated and S04 was never frozen. **10 calls, USD 0.2376985 / 0.60, 87,681 tokens, 80.604 seconds summed model latency**; one rewrite, no retry or third attempt. Shared scope SETTLED for exact usage and grant CLOSED; saved ledger matches live registry.

Both S04 JOINT_MOVE anchors are verbatim and supported, and both semantic residual reports say PASS. Rejection comes from the separate MATCH_PACE evidence: Sonnet changes Sol's curly apostrophe `Mert’s` into ASCII `Mert's` in both attempts. Exact event/coverage grounding rejects the copied quote. Diagnostic apostrophe-only equivalence is recorded without being used for acceptance, modifying evidence or overriding the rejection. Q11 is not whole-story qualification, despite promising sampled joint crossing prose.

Offline replay now supports complete bounded terminal rejections as well as acceptance; it reconstructs both attempts, preserves the last accepted state and rejects additional calls, fake advancement or retroactive quote repair. Evidence: `SFR-V1-Q11-JOINT-MOSAIC-20261008/`, including raw requests/responses, ledgers, accepted prefix, failed validations, replay and failure analysis. No full assembled story exists.

Next general upgrade: typed trusted source-span IDs, with exact quotes reconstructed locally from original prose, rather than fuzzy matching or model-retyped quotation. The failed Q11 guard/evidence must stay immutable; a new qualification requires fresh frozen inputs/authority. Historical Q10 acceptance is unchanged. Production LUMI and merging remain outside scope.

Post-run validation: 354 local Relay tests PASS, including exact rejection replay and four controls against reclassification, fake advancement, altered spend or retrospective quote repair. All 61 staged raw/diagnostic files preserve original bytes; live shared ledger matches the closed snapshot. No provider calls during validation.
