# Q5T structured required events

Q5S remains immutable rejected evidence. Q5T is a fresh writer qualification
against the same frozen canon, story intent, initial state and spine route, with
a new structured ScenePlan/SceneContract fingerprint. Production LUMI is outside
this experiment. PR #264 remains draft; no merge is authorized.

`RequiredEventSpecV1` defines actor, action, target, required observer, ALL_PREDICATES
satisfaction, evidence mode, provenance allow/deny lists, optional physical clue
requirement, forbidden evidence subjects and resulting state. The compiler refuses
natural-language event strings and objective fallback. Resulting state must agree
with the contract's authorized exit state. Event IDs and predicate IDs are unique.

The writer and guard consume exactly the same compiled specification. The guard
extracts evidence for each predicate and audits residual continuity/meaning. Local
checks enforce exact coverage, actor/action/target attribution, allowed provenance,
literal prose anchors, and character-specific established-knowledge references.
Natural-language entailment remains a semantic judgment: an exact quote is not
proof by itself. There is no keyword-based automatic satisfaction or story-name
branch in the evaluator. Unsupported or ambiguous predicates block acceptance.

SC01 E03 specifies a visible dragon heading toward the lighthouse, Duru indicating
that destination, and Ekin acknowledging that observation. It requires no separate
physical clue. Invented rules, clues and lore are forbidden; weed/shell/cave evidence
is forbidden in the fixture. The generic schema supports unrelated stories too.

Historical string schemas/compiler are explicitly isolated as legacy readers for
old Q5 input replay. Historical state/compiler regression scenarios now use explicit
structured test fixtures; their assertions remain intact. Old evidence is not
rewritten to match new hashes. The consumed automatic Q5SF job has been retired from
the zero-cost workflow, which now has read-only permissions and no paid credential.

Q5T allows at most two Sol writer calls and two Sonnet guard calls. A failed,
truncated, invalid, over-budget or uncertain call stops without retry. One semantic
rewrite is permitted; a second blocker ends in REJECT_NON_CONVERGENT. A durable
exclusive claim prevents reuse even with a different output directory under the
same evidence root. Never delete that claim or rerun a rejected Q5T authorization.

Each call saves its normalized request, response, input/output/total tokens,
reported cost and latency. A conservative UTF-8-byte input allowance and maximum
output budget are checked before dispatch. Local ceilings are $0.15 per call and
$0.60 total; these are local fail-closed checks, not a provider-side hard spend cap.
Unknown usage is explicitly recorded as incomplete, never silently treated as free.

Only all-event satisfaction plus residual guard PASS permits a freeze. The existing
deterministic reducer derives SceneDelta from authorized exit state and produces
revision 1 / next beat SC02. The accepted scene, delta and state are saved together
in a single evidence bundle. Failed runs never emit an accepted-state bundle.

Zero-cost command: `python -m pytest -q tests/test_spineforge_relay_v1_*.py`.
On Windows use PowerShell file enumeration and `python -X utf8`; choose a writable
pytest basetemp. Fake providers test plumbing only, not actual model qualification.
Paid execution uses `python -m src.spineforge_relay_v1_q5t execute` with an exact
saved preflight and authorization, and the lab's existing OpenRouter credential.

## Q5T result — 2026-10-07

After 122 Relay tests, 23 runtime-profile tests and self-hosted CI passed,
the user explicitly approved transmitting the frozen story inputs through OpenRouter.
The fresh run accepted attempt 1: all six predicate evidence rows were supported,
local checks passed, and Sonnet's residual report returned PASS with no findings.
No rewrite or retry was used. Sol cost $0.008901 (1,941 input / 405 output tokens,
9.444 seconds); Sonnet cost $0.024146 (5,968 input / 1,221 output tokens,
11.308 seconds). Total: $0.033047, 9,535 tokens, 20.752 seconds of call latency.

SC01 is frozen in `evidence/spineforge-relay/SFR-V1-Q5T-STRUCTURED-20261007/accepted-scene.json`.
The deterministic delta moves the compass from Ekin's hands to the dragon;
StoryState advances from revision 0 to 1 and next_spine_beat becomes SC02.
The bundle was independently reproduced from saved evidence without another model
call. All 43 historical evidence files retain their original Git content hashes.
This qualifies this single scene and contract, not long-horizon production readiness.
