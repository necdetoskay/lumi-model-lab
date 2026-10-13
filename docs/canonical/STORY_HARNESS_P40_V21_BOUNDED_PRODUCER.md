# Story Harness P4.0 — Genuine v21 bounded-quality producer preflight

**Scope:** experimental, PR #275 Draft; issue #284; zero new API spending.
This is a **real offline test of the original frozen v21 runtime with
synthetic transport replies**. It is **not** an accepted story, not an
English Master seal, and not a paid-E2E release authorization.

## Why reuse rather than rewrite

The original pinned `spineforge-v21` source already has the desired
topology:

```text
Writer source → initial blocking audit
              ├── No blocking findings → simulated 1-call ACCEPT
              └── Blocking findings → at most 1 scene repair
                                   → targeted final audit
                                   → simulated ACCEPT / REJECT_NON_CONVERGENT
```

Maximum three model calls, never a second repair or a full-story final
reaudit. Runtime budget targets are **$0.040 initial**, **$0.035
repair**, **$0.025 final**, and **$0.10 total quality ceiling**.
These are *post-usage STOP gates*, **not a guaranteed provider spend cap**.
The frozen v21 paid boundary has `paid_execution_authorized=false`,
`authorization_consumed=true`, and `authorization_state=NO_GRANT_ISSUED`.
No new grants were issued.

## Exact source / immutable provenance

P4.0 reruns the P3.2 same-island English Master denial. The original
v21 frozen source profile matches that same cycle 10 candidate by
**artifact ID + exact story SHA**. Original historical source code,
frozen profile, v21 contract and the original failed paid attempt are
pinned by **11 SHA-256 checks** plus fixed source commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`.
Manifest:
`configs/story_harness_p40_v21_producer_preflight.json`.
The v21 freeze verifier itself is actually invoked inside the original
Python runtime, not simulated by the Story Harness.

An isolated subprocess executes the **actual**
`src.spineforge_v21_simulation.simulate_case()` with the original
`execute_paid_quality_once(simulation=True)` and original adapter,
runtime, budget and lineage safeguards. Fake callbacks cannot issue
provider network requests. Subprocess environment is sanitized to
exclude provider credentials and blocks socket network access.
Any unpinned source or forged result fails closed.

| Original v21 offline scenario | Expected status | Bounded calls |
| --- | --- | ---: |
| clean | `ACCEPT` **synthetic** | 1 |
| repair_succeeds | `ACCEPT` **synthetic** | 3 |
| non_convergent | `REJECT_NON_CONVERGENT` | 3 |
| initial_cost_ceiling | `REJECT_COST_CEILING` | 1 |
| repair_cost_ceiling | `REJECT_COST_CEILING` | 2 |
| final_cost_ceiling | `REJECT_COST_CEILING` | 3 |

The simulated positive statuses verify that the code can route and
stop correctly with fabricated, machine-defined model replies.
**They provide zero evidence that the English story is actually good**.
No simulated result may produce a signed English Master, Q25 request,
state commit, or even a production accept claim.

### Historic paid run is preserved as a failure

Original archived run `37230896244` completed initial audit and
scene repair, but the targeted final audit hit `AdapterResponseError`.
Exact source status: `REJECT_PROVIDER_FAILURE`, not ACCEPT.
Its historical ledger records **three** API calls, **21,870**
tokens, **$0.057988** cost and **21.023 s** summed call latency.
These are old costs, **not** newly spent money. There was no accepted
story SHA and no authorized canonical state commit.

## Real English Master producer contract — future boundary

P4.0 now pins a separate minimum *future* producer/admission contract
in its manifest. The following are mandatory but do **not** themselves
grant acceptance:

1. Exact same-story immutable source IDs, hash, Spine and ContextPack
   match P3.2; do not substitute an unrelated accepted Lighthouse text.
2. Genuine provider/model evidence must include source/story hash,
   full blocking-finding and repair trace, real usage and three-call
   ledger, final targeted audit or clean fast-path decision; forbid
   failed, missing, unaccounted, duplicated or unbounded stages.
3. A separate semantic/age/canon/causal review must attest that the
   observed real quality outcome is genuinely ACCEPT. A mocked audit
   `status=ACCEPT`, or a different story's ACCEPT, is never sufficient.
4. Only then may a separate **versioned, immutable English Master
   seal producer** freeze the accepted English bytes (text SHA, origin
   artifact ID, audit lineage, verified constraints, accepted receipt
   and token/cost ledger). Seal production is a distinct authorized
   operation, not automatic upon model return.
5. A separate Q25 read-only admission receipt is required; producing
   a seal cannot write production/canonical StoryState or run extraction
   without a new gate.
6. Runtime model slots must be configurable separately from quality
   topology and bounded budgets. Any later paid call requires explicit
   user permission; stage budget profile alone is not permission.

P4.0's current **original real accepted story = none**, English Master
seal = none, Q25 handoff = none. These remain DENY:

```text
stop_reason = REAL_BOUNDED_QUALITY_ACCEPT_MISSING
state = STOPPED_BEFORE_ENGLISH_MASTER_SEAL
synthetic_ACCEPT_is_genuine_story_quality = false
english_master_seal_emitted = false
q25_handoff_emitted = false
bounded_paid_attempt_authorized = false
provider_calls = 0
provider_cost_usd = 0
```

## Reproduce ($0)

```sh
git worktree add --detach /tmp/lumi-p40-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' 'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P40_ROOT=/tmp/lumi-p40-source
python -m unittest discover -s tests -p 'test_story_harness_p40.py' -v
python -m src.story_harness_p40 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P40_ROOT" \
  --verify-report evidence/story_harness_p40/pinned-v21-producer-preflight.json
```

Negative regression checks reject changed historical paid failure to
ACCEPT, synthetic result promoted to a real story, four calls, a
weakened seal contract, unpinned producer source, wrong story,
invented English Master/Q25, relaxed budgets and forged downstream
authority. All source files stay unchanged.

**Next:** P4.1 must implement a separately reviewed, non-production
English Master seal *validation/producer contract* and prepare a
**single bounded real-story quality attempt** proposal. Only explicit
approval allows paid execution. If quality remains rejected, hard STOP.

