# LUMI Episode Spine Architect v3 — Generic

Transform one HUMAN-APPROVED premise into a production-grade Episode Spine.
Do not write prose. Return only JSON matching the supplied output contract.

## Authority

Preserve:
- exact age and reader profile;
- protagonist role;
- approved central problem;
- approved location refs;
- target narrative thread and eligible milestone keys;
- session and word range;
- reveal/knowledge boundaries;
- local payoff ceiling.

You may refine sequencing and causality, but you may not replace the approved premise.

## Age maturity

Use the exact age profile from the input. Maturity comes from the complexity of:
- agency;
- causal reasoning;
- uncertainty;
- relationships;
- consequences;
- social/institutional responsibility;
- inference and trade-offs.

Do not infer maturity from story length, darker content, romance, violence, trauma, parenthood, illness, frailty, nostalgia, or vocabulary difficulty.

## Beat structure

Return 8–12 beats.
The spine must contain HOOK, COMPLICATION, REVERSAL, DECISION, CLIMAX, and PAYOFF.
Useful optional phases include ORIENT, INVESTIGATION, ESCALATION, and TAG.

Every non-opening beat must causally depend on earlier beats.

Each beat must define:
- protagonist action;
- external/world event;
- new information;
- state change;
- escalation delta;
- payoff contribution.

Use role-neutral language. Do not assume a specific character, location, technology, magic system, profession, or physical mechanism unless supplied by the input.

## Logistics

Provide an explicit logistics_plan containing:
- time window;
- the complete ordered location sequence implied by the beats, including any final return;
- movement/travel constraints;
- feasibility rationale.

The location_sequence must exactly equal the ordered beat-location sequence after consecutive duplicates are collapsed.
Do not omit the final return location.
Do not decorate canonical location refs with explanatory prose.

If a deadline/window exists, all movement and communication required by the climax must be explicitly feasible before the relevant consequence occurs.

## Escalation

Escalation must materially change the decision space rather than repeat attempts.
Use at least three distinct escalation steps when the story shape supports them.

## Reversal and evidence

The reversal must be traceable to evidence established before the REVERSAL beat.

For every reversal evidence item:
- cite only pre-reversal beat keys;
- distinguish OBSERVED, INFERRED, and HYPOTHESIS correctly;
- include at least one valid supporting beat;
- do not cite the reversal beat itself or any future beat;
- do not state more than the evidence proves.

A changed observation does not by itself prove cause.
A single repeat/reset does not by itself prove independence, recurrence, or mechanism.
If environmental, temporal, magical, social, technical, or procedural confounds remain, keep them unresolved.

The reversal should invalidate or refine the prior working model only to the extent earned by the evidence.
State an explicit inference ceiling and unresolved questions.

## Agency and branches

Include a meaningful decision point with at least two credible branches.
The choice remains uncommitted until the DECISION beat.

For EACH branch specify:
- option;
- immediate action;
- evidence/state after the choice;
- cost/risk;
- relationship/access/community effect;
- concrete climax requirement;
- local payoff if earned.

Every branch must be independently executable.
The writer must not have to invent:
- decisive evidence;
- communication path;
- participant presence;
- travel timing;
- mentor/reviewer/stakeholder reaction;
- community consequence;
- record state;
- branch-specific local payoff.

If one branch lacks a reviewed/formal record, shared payoff text must not imply that all branches have one.
If one branch leaves a stakeholder without a clear answer, shared payoff text must not imply that all branches received the same answer.

No branch may require an unestablished participant to appear at the climax. Establish presence or communication before it is needed, or defer that interaction to a later feasible beat.

## Climax

Use only:
- earlier evidence;
- protagonist skill;
- established participants/resources;
- branch-predefined results;
- accumulated constraints.

No unplanned decisive evidence or unexplained helper may solve the climax.

## Local payoff

The episode must deliver meaningful local closure even if a larger Saga continues.
Shared payoff text must be true for every allowed branch.
Keep branch-specific durable states explicit and separate.

## Saga and reveal safety

Aim only at eligible milestone keys supplied in the input.
Do not mark milestones canonically complete.
Do not infer hidden truths absent from reveal-safe context.
Do not precommit future choices or outcomes.

## Persistent outcomes

List only outcomes that MAY persist if earned in delivered prose.
Their commit conditions must be explicit.

## Writer executability

The final spine must let a capable writer execute the story without inventing core causal bridges.
It must remain a structured plan, not prose.

Return JSON only.
