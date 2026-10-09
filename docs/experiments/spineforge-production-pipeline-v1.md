# Generic request/state-driven pipeline v1

## Behavior

StoryRequest + immutable StorySeed + RunConfig -> planner -> structural admission -> grounded semantic plan review -> configurable scene writer/guard -> deterministic scene freeze -> assembled story + offline replay + initial/final comparison. All scenario facts enter as data; no character, robot, location or solution-specific runtime branch exists.

RunConfig selects planner, plan guard, scene writer and scene guard independently, with qualified exact runtime profiles, output limits and spend ceilings. Unknown/unqualified models fail before inference. This interface enables future comparisons; no Haiku qualification or model-quality equivalence is claimed. Current structural scope inherits 2–12 scenes and v5 event/coverage/spatial contracts.

A planner has one bounded rewrite for structurally invalid plans or grounded semantic REWRITE. Invalid/mismatched review or transport/usage/finish errors stop without retry. Semantic review is a model judgment: valid evidence pointers do not certify causal or literary truth. Scene writing retains initial + at most one rewrite, source-span guard grounding and fail-closed freeze. Scenario IDs must be safe file identifiers.

## Shared admission

The new production-paid-entry CLI requires an already registered GitHub shared grant/scope bound to the exact root preflight. It never creates consent or reopens an old allowance. One reservation covers planning, review and all calls against the generated plan. Root preflight freezes request/seed/freeze/config bytes and upstream/downstream sources. Generated fixture and scene preflight are recorded derived artifacts; the chosen models and root ceilings remain approved inputs. Client-side enforcement assumes trusted frozen client code, as in the existing reservation system.

Provider dispatch uses single-use capabilities and the unchanged no-retry transport. Raw captures are saved before broker usage settlement, including responses later rejected by usage checks. Unknown dispatch holds the reservation. Total and per-call local admission is not a provider-enforced spend guarantee. Complete calls retain requests/responses, usage, cost and latency. Plan candidates, failures, reviews, final accepted design, every scene/state artifact, output prose and manifest are preserved. Output is exclusive; no continuation/retry of a consumed scope.

The default proposed six-scene envelope is at most 28 calls (4 upstream + 24 scenes), USD 1.20 aggregate, USD 0.30 per call and USD 0.15 per scene call. Q13 was explicitly approved and dispatched once, but failed before any plan response. The Q13 grant is CLOSED and its reservation UNCERTAIN; actual charge is unknown and USD 1.20 remains held. No retry or reopening occurred. Q14 was subsequently explicitly approved and dispatched once; its token-limit rejection is recorded below.

## Controls and limits

Zero-cost synthetic providers exercise the same code for a six-scene joint delivery and a two-scene stationary knowledge/decision story. These are structurally different integration controls, not generated story-quality results or golden semantic labels. Controls cover one structural/semantic planner rewrite, nonconvergence, stale review, grounding failure, unknown model, invalid usage, incomplete response, unsafe IDs, shared reservation settlement/duplicate denial and unreserved transport rejection.

A successful runtime result still requires separate editorial reading. State equality/diffs and fake-provider controls are not proof of universal narrative quality. The next real qualification uses the user's unchanged robot request/seed; its ending is not predetermined. Production LUMI and PR merge remain outside scope.

Historical engines and replayer are untouched. A versioned configurable engine/replayer preserves historical fingerprints while enabling explicit model profiles and shared end-to-end admission. Their duplicated frozen algorithm requires parity/regression checks; this is a versioning tradeoff, not a different story-specific implementation.

Validation: 415 local Relay tests PASS in 214.52 seconds. Complete synthetic controls are saved under SFR-PRODUCTION-ZERO-COST-CONTROLS-20261009 with explicit provenance distinguishing simulated ledger figures from real billing. Q13 proposal/preflight/local proof are prepared under SFR-V1-Q13-GENERIC-PREFLIGHT-20261009; paid authorization remains false.

## Q13 recorded failure and correction

Q13 attempted one planner dispatch, received no complete response/usage and produced no plan, story or state transition. Result is REJECT_NON_CONVERGENT / FAILED_CLOSED_NO_RETRY. Known recorded cost 0 is not actual zero billing; actual cost is unknown. Live registry matches saved CLOSED authority and UNCERTAIN reservation. The baseline seed is unchanged.

The original request selected json_object but contained no JSON instruction/literal in any message. Official OpenAI documentation requires this in JSON mode: https://developers.openai.com/api/docs/guides/structured-outputs . The request defect is confirmed; exact original HTTP cause is unproven because the initial error capture retained only exception type. A read-only key-status check succeeded but does not recover historical response or cost. Do not reinterpret this as a model/story-planning quality failure.

The generic request builder now always includes an explicit single-JSON-object instruction. Transport failure capture now preserves HTTP status/error trace with credentials/header fields removed and the actual key redacted. Regression tests cover planner/reviewer instructions and error redaction. Q13 raw evidence is unchanged; archived source bytes from 715a471 match the approved preflight. Offline failure audit validates this partial dispatch without Git history, supporting shallow CI checkouts, and cannot claim full replay or paid success.

Q14 used its own explicitly approved scope, with the same immutable request/state/config and corrected source fingerprints. It did not consume Q13's held allowance. All synthetic control provenance remains explicit.


## Q14 token-limit rejection

Q14 was authorized, dispatched once and CLOSED / SETTLED at USD 0.1362735. GPT-5.6 Sol returned finish_reason=length: 6510 input tokens, 12000 output tokens, 18510 total, 110.569 seconds. Output includes 1688 reasoning tokens. The raw JSON is incomplete; no plan was parsed/admitted/reviewed, no scene writer ran, and revision stayed 0. No retry, rewrite, repair of partial JSON or continuation was performed. Q13 remains separately CLOSED / UNCERTAIN with USD 1.20 held.

The approved source bytes from commit 33e9eb6df113cd64d23274d3c9c0f4d600a43729 are archived against the preflight hashes. The offline truncation audit verifies request/response captures, incomplete JSON, exact usage/cost, immutable seed, raw manifest, and closed settlement. It does not certify the partial plan's semantics or a generated story. Tamper controls reject reclassification, changed finish/usage/text/source and false settlement.

The current planner boundary requires a fully materialized v5 fixture, including copied immutable state and repeated coverage/spatial/frame fields. The returned fragment also contains apparent protocol mismatches (route/scene identities, RESOLVED obligation status, metadata state writes); it has not undergone structural validation. Increasing the output ceiling alone would not resolve these concerns.

Next proposed change: a versioned compact planner output containing explicit scene/event semantics, predicate bindings, state effects and event-bound thread/obligation resolutions. A deterministic generic compiler would inject frozen state/canon/topology, derive route metadata and repeated control fields, then retain existing structural and semantic admission. The compiler must not invent events/effects, silently close unresolved obligations or contain scenario-specific branches. This change is proposed, not yet implemented or qualified. No Q15 grant exists, and Q14's unused allowance cannot be reused.


## Compact planner boundary (Q15 preparation)

The real planner now returns CompactStoryPlanV1, not a fully materialized fixture. It chooses premise/character arc/resolution, scene purposes/objectives/turns, event predicates, explicit state effects, request/goal/order bindings, spatial operations and predicate-bound thread/obligation resolutions. The first predicate defines each event's principal action; allowed provenance is derived from evidence_mode, with invented rules/clues/lore forbidden. Optional/default fields may be omitted. Frozen seed data is input context, never regenerated output.

The generic compiler injects exact initial seed/canon/topology/resource policy, request preferences, one route beat per unique safe scene ID, next-beat metadata, coverage source text/attribution triples and spatial entry/exit. Only declared operations can change canonical locations. Event effects cannot write compiler metadata, locations, spatial state, closures or world rules, create seed entities, or conflict/overlap. Preconditions are verified, not patched. Existing structural coverage/spatial/state admission remains in force; the semantic review sees the expanded design and exact resolution predicate bindings in story_intent. A binding alone does not prove that an action earns a resolution.

Thread/obligation resolutions must explicitly identify existing open entries and actual scene predicates. The compiler preserves obligation IDs/details/target_scene_id and sets SATISFIED only for declared resolutions. Unresolved terminal entries reject; no auto-closure or scenario-specific ending is invented. The same compiled design feeds existing writer/guard and deterministic accepted-scene freeze. Planning only projects state; actual state advances after accepted scene evidence.

Both raw compact proposal and expanded design are retained for each valid parsed attempt, followed by structural/review/scene records. Transport/truncation still closes without retry; one structural/semantic plan rewrite and one scene rewrite remain the ceiling. Old Q13/Q14 captures and historical engines are unchanged. No backward fallback interprets a full fixture as a new compact proposal.

Two authored synthetic controls traverse the complete new pipeline: six-scene joint delivery and two-scene stationary knowledge/decision. Their projected final state values match the earlier authored controls; intent fingerprints differ because explicit resolution bindings are now retained. Serialized compact control character lengths fall from 45080 to 21010 (53.4%) and 5635 to 1773 (68.5%), excluding default fields. These are character counts, not tokenizer estimates or a paid-call guarantee. The planner output ceiling remains 12000 tokens.

Complete control evidence is recorded in SFR-COMPACT-ZERO-COST-CONTROLS-20261009. Responses and ledger figures are synthetic: actual inference calls/spend are zero. They are not literary-quality verdicts, Haiku qualification or golden labels. Q15 is a fresh proposed run against the unchanged robot request/seed, with new compiler/contract source fingerprints; no grant or paid execution exists until explicit approval.

Compact validation: **448 local Relay tests PASS in 237.85 seconds**. Compiler controls: 18 PASS; pipeline controls: 17 PASS. Q15 prepared preflight SHA-256: `8278b51827ad2616fc8c6b6d282104fa7b1de08cfab2f2a194b296f3181fb13f`. No new real provider calls or grant were made.
