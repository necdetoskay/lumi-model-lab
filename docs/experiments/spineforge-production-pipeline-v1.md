# Generic request/state-driven pipeline v1

## Behavior

StoryRequest + immutable StorySeed + RunConfig -> planner -> structural admission -> grounded semantic plan review -> configurable scene writer/guard -> deterministic scene freeze -> assembled story + offline replay + initial/final comparison. All scenario facts enter as data; no character, robot, location or solution-specific runtime branch exists.

RunConfig selects planner, plan guard, scene writer and scene guard independently, with qualified exact runtime profiles, output limits and spend ceilings. Unknown/unqualified models fail before inference. This interface enables future comparisons; no Haiku qualification or model-quality equivalence is claimed. Current structural scope inherits 2–12 scenes and v5 event/coverage/spatial contracts.

A planner has one bounded rewrite for structurally invalid plans or grounded semantic REWRITE. Invalid/mismatched review or transport/usage/finish errors stop without retry. Semantic review is a model judgment: valid source selections do not certify causal or literary truth. Scene writing retains initial + at most one rewrite, source-span guard grounding and fail-closed freeze. Scenario IDs must be safe file identifiers.

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

Complete control evidence is recorded in SFR-COMPACT-ZERO-COST-CONTROLS-20261009. Responses and ledger figures are synthetic: actual inference calls/spend are zero. They are not literary-quality verdicts, Haiku qualification or golden labels. Q15 was subsequently approved and executed once against the unchanged robot request/seed; its result is recorded below.

Compact validation: **448 local Relay tests PASS in 237.85 seconds**. Compiler controls: 18 PASS; pipeline controls: 17 PASS. Q15 prepared preflight SHA-256: `8278b51827ad2616fc8c6b6d282104fa7b1de08cfab2f2a194b296f3181fb13f`. This was the pre-run preparation; subsequent Q15 dispatch and closure are recorded below.


## Q15 recorded planning rejection and compact v2

After the scoped Q15 approval question, the user directly replied “devam edelim”; the controller records that continuation and the presented limits as authorization. One shared scope dispatched the initial planner and exactly one structural rewrite. Both returned complete JSON (finish_reason=stop), so the Q14 output-size failure did not recur. The initial proposal failed “Order dependencies must be unique distinct covered predicates”; the rewrite failed “Spatial operation requires one exactly attributed predicate”. No Sonnet review, scene writer, story or actual state transition followed. No third attempt or transport retry occurred.

Q15 is CLOSED / SETTLED at USD 0.1550770 for two calls, 26539 total tokens and 119.607 summed latency seconds. Live registry matches the saved closure. Q13 remains separately CLOSED / UNCERTAIN with USD 1.20 held; Q14 remains CLOSED / SETTLED at USD 0.1362735. Approved source bytes from 47db3cb are archived and hash-verified; the offline plan-failure audit reproduces both original v1 structural errors and verifies raw captures, complete usage/cost, frozen seed, manifest and settlement. It does not certify plan semantics or a generated story.

The precise failure is duplicated protocol attribution. The order cited repair/test sub-predicates not selected in goal coverage. Movement declared robot/MOVE/exhibition_hall but cited Bora/CARRIES_TO_EXHIBITION_HALL/robot; character MOVES_TO also differed from typed MOVE. These were complete event proposals, not accepted narrative plans.

CompactStoryPlanV2 removes that duplicate attribution. Each goal explicitly selects whole event IDs; code expands the complete selected predicate specs, retaining order anchors to a principal action or explicit sub-predicate. All required events need explicit goal coverage. Spatial steps declare kind/subject/target/event/edge/constraint, without predicate_id. Code reuses one uniquely matching physical predicate or derives one from the explicit typed declaration. It does not guess aliases or movement from narrative verbs, add undeclared entities' movement, or change the principal narrative action. Unknown entities/events, ambiguous matches, ID collisions, unsupported evidence, invented edges and unbound goals reject. Existing v1 state/coverage/spatial compilers still validate everything. Frozen v1 models/prompt/compiler are unchanged for historical audit; real inference accepts only the v2 boundary, with no v1 fallback.

Both rejected Q15 proposals pass structural checks after an offline test-only format migration to v2. These migrated controls are saved separately; original Q15 JSON/result is unchanged. This is not a retrospective acceptance, semantic review, generated story, state advance or third paid attempt. They are structural regressions, not golden labels. Independent complete synthetic controls still cover joint delivery and stationary knowledge/decision, with actual provider calls/spend zero.

Next real qualification must be a fresh v2 run from the unchanged robot request/seed, with a new source/contract fingerprint and a new shared grant. Q15 is not reusable. Production LUMI and PR merge remain outside scope.

Compact v2 validation: **468 local Relay tests PASS in 294.37 seconds**. Seven Q15 immutable-failure audit controls and thirteen v2 protocol controls are included. Q16 prepared root SHA-256: `3746df9587b2bb67e925281c23c3109bbc83a903a69f31d4a271b9655423d17e`; This was the pre-run Q16 preparation; subsequent authorization and result are recorded below.


## Q16 recorded rejection and compact v3

The user explicitly approved Q16's fresh 28-call / additional USD 1.20 scope. Its frozen source commit 46d8e81 passed isolated zero-cost CI (run 37900137842). The initial planner and one structural rewrite both returned complete JSON but failed RequiredEventSpec validation: first OBSERVES/ACKNOWLEDGES did not satisfy required_observer's canonical OBSERVE/ACKNOWLEDGE contract; then separate_physical_clue_required=true lacked SHOW_PHYSICAL_CLUE. No Sonnet plan review, scene writer, state transition, retry or third attempt followed.

Q16 is CLOSED / SETTLED at USD 0.1744970, two calls, 28820 tokens and 139.518 summed latency seconds, matching live registry. Source archives match the approved preflight. Offline failure audit reproduces the frozen v2 failures, verifies raw usage/cost/manifest/seed/closure, and preserves original diagnostics. Stable ValidationError constraint messages are compared independently of library URL/input-repr formatting; original raw bytes remain hash-checked. Q15 stays rejected at USD 0.1550770, Q14 at USD 0.1362735; Q13's unknown USD 1.20 stays held.

V3 removes the remaining duplicated observer/clue protocol. required_observer declares intent; code adds the canonical OBSERVE requirement when absent, without renaming ordinary narrative verbs or claiming satisfaction. physical_clue explicitly names who shows what when a separate demonstration is actually required. Its compiler adds SHOW_PHYSICAL_CLUE and the derived flag. The ambiguous boolean is absent from the planner schema and rejected as an extra field. Direct observation alone never generates a separate clue. Unknown observers/clue actors, ID collisions and established-knowledge-only physical clues reject. Existing v1/v2 admission, source-span writer/guard evidence, state checks and bounded rewrites remain unchanged. All generated predicates are requirements, never invented guard verdicts or prose evidence.

Both Q16 rejected proposals structurally pass a separate test-only v3 migration. For legacy ambiguous clue booleans, the migration control explicitly authors a subject/target proposal; this is not semantic equivalence, proof of a clue, retrospective acceptance or a third paid attempt. Q16 files remain unchanged. Independent joint-delivery and stationary decision controls run through the same v3 production pipeline, with actual inference/spend zero. These records are not golden semantic labels or production-quality stories.

The remaining real qualification must start fresh from the same immutable robot request/seed under a new v3 fingerprint and shared grant. No old scope can be reopened/reused; production and merge remain out of scope.

Compact v3 validation: **484 local Relay tests PASS in 243.28 seconds**. Q17 was initially prepared at root SHA-256 `a75fcb8501041d279d32e299259d136d9de122e0f6d589fcbcf134c9d708634c`. This was its pre-run proposal; the later approved Q17 outcome is recorded below. Q15+Q16 actual spend this continuation is 4 calls / USD 0.329574; neither generated a story.


## Q17 recorded rejection and bound plan review v2

Q17 was explicitly approved and executed once from frozen commit c7f3c1ffb33cfe758fbd85a54938b99a477c7cd7 (zero-cost CI 37903615221 SUCCESS). The first v3 Sol proposal passed structural admission for all six scenes. Sonnet returned complete REWRITE JSON with six findings, but authored pointers rooted at /design/fixture while legacy admission required /fixture relative to the design object. The invalid review stopped the run before a planner rewrite or any scene call; seed/state remained unchanged. Q17 is immutable REJECT_NON_CONVERGENT, CLOSED / SETTLED, matching the live registry: two calls, USD 0.149573, 41761 tokens, 90.288 summed latency seconds. Q13 USD 1.20 remains separately held and unknown.

Offline failure audit reproduces that boundary rejection and verifies raw requests/responses, usage, frozen sources, manifests and closure. Diagnostic removal of /design shows all six quoted source values actually match; the emotional-transition typo is real. This inspection does not admit the review, adjudicate its other semantic claims, accept the plan or reopen Q17.

The reusable review-v2 boundary supplies code-owned field IDs and planned entry/exit transitions. Strict JSON output constrains the current review ID and allowed field IDs; the guard selects a semantic source field/category, reason and repair instruction. Code binds exact compact pointers/values and frozen request/seed/design hashes. Stale IDs, unknown fields, copied extra values, table/projection drift, decision mismatch and duplicate findings fail closed. Optional compiler metadata is not an editable source field. This prevents pointer-root/copy errors without proving semantic correctness or weakening causal, knowledge, resource, deadline or earned-resolution review. Historical v1 review admission remains available to audit Q17 unchanged.

Two new independently recorded synthetic controls traverse the entire v3 + review-v2 pipeline: six-scene joint delivery and two-scene stationary decision. They preserve full call/state/replay evidence under SFR-REVIEW-V2-ZERO-COST-CONTROLS-20261009; actual provider calls/spend are zero. Synthetic ledger figures are explicitly not billing, model qualification or golden labels.

Fresh Q18 preparation uses the identical frozen robot request/seed/config, planner v3, bound semantic review v2 and a new source fingerprint. It proposes a new 28-call / additional USD 1.20 scope, USD 0.30 per call / 0.15 per scene call, one plan/scene rewrite and no retry. Q17 and prior closed allowances are not reused; no Q18 authority or provider dispatch exists. Production and merge remain disabled.

Bound-review validation: 501 local Relay tests PASS in 253.67 seconds; targeted Q17/review controls 17 PASS and pipeline controls 17 PASS. Q18 proposed root SHA-256: d44574a9cda458c0fc049cd66f6fd84292ce36f597663b84a6b730e02fc298ba.


## Q18 recorded partial-story rejection

The user explicitly approved Q18 and it ran once from f98cada93885624d9011babc092a000dee0faf95, whose isolated zero-cost CI 37911216497 succeeded. The first Sol plan passed structure and the bound Sonnet plan review PASS. Scenes S1-S3 accepted on first attempts, advancing a working state to revision 3. At S4 the raw guard residual PASS selected source spans 0 and 5 for E4_Repair/P4b; frozen source-span admission requires unique ordered contiguous spans, so the invalid reference stopped the chain before any rewrite or later scene. No complete story, terminal state or S4 freeze is claimed.

Q18 is immutable REJECT_NON_CONVERGENT / FAILED_CLOSED_NO_RETRY, CLOSED / SETTLED matching live registry: 10 calls, USD 0.348339, 116646 tokens, 162.237 summed call-latency seconds. Initial seed is unchanged; partial offline replay PASS confirms three accepted scenes, revision 3 and next S4_OnarimVeTest. Exact raw captures, bound plan review, frozen sources, accepted prefix and explicitly partial state comparison are retained under SFR-V1-Q18-BOUND-REVIEW-ROBOT-20261009. The raw S4 guard judgment was not admitted or repaired; no retry, reopening, production write or merge. Q13 USD 1.20 remains separately held.

This exposes a generic evidence-selection protocol limitation: strict JSON bounds individual IDs but cannot enforce contiguity of a selected list. Future work should move permitted evidence ranges to code-owned choices rather than relying on model-selected index sequences. This is an unpaid next design step, not an approved new paid run.
