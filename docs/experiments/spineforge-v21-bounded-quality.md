# SpineForge v21 — Bounded Scene Quality

## Purpose

v21 preserves the proven v20 artifact, lineage, authorization, accounting, and fail-closed foundations while replacing the non-convergent Story Quality Loop.

v20 evidence showed that sentence-span patching could keep a story inside an audit/repair loop even with strong models. v21 treats that as an architecture defect, not a reason to add more repair cycles.

## Production topology

Writer -> Initial Blocking Audit -> [0 or 1 Scene Repair] -> Final Blocking Audit -> ACCEPT | REJECT_NON_CONVERGENT

Hard limits:

- initial audit: exactly one production auditor call;
- scene repair: zero or one call;
- final audit: zero or one call, required after repair; it audits only the repaired scene plus immutable boundaries;
- no second repair;
- no automatic loop;
- final audit may return only ACCEPT or REJECT_NON_CONVERGENT;
- translation and state commit are forbidden before ACCEPT.

An optional shadow auditor belongs to Model Lab evaluation only and is not part of the production cost path.

## Blocking policy

Routing is driven by material defects, not editorial perfection.

Blocking categories are physical/causal/state/spatial/temporal/knowledge/canon/spine/narrative defects at moderate or greater severity.

Language/style findings are advisory and do not independently trigger repair. Minor findings do not independently trigger repair.

## Repair unit

The repair unit is one contiguous semantic scene cluster, not individual sentence spans.

The handoff contains:

- immutable source story artifact/hash;
- blocking findings;
- non-blocking advisories;
- exact source scene cluster;
- immutable entry/exit boundary context;
- approved Spine hash;
- canon invariants.

The repair model rewrites the whole bounded scene. Text outside the cluster must remain identical.

v21 does not require the replacement scene to preserve the old sentence count. After rewrite, the new immutable story revision receives fresh deterministic segmentation with lineage back to the source cluster.

## Model substitution

The topology does not encode a permanent model choice. Writer, blocking auditor, scene repairer, translation, and fidelity are model slots.

After the topology is stable, Model Lab may replace one slot at a time against frozen inputs and compare pass rate, blocking-defect recall, repair success, latency, tokens, and actual API cost.

The initial English-pipeline optimization target is <= $0.10 per accepted story. The provisional quality budgets are $0.040 initial audit, $0.035 scene repair, and $0.025 targeted final audit. Cost optimization must not change topology or artifact contracts.

## v20 bridge regression

The v20 bridge/rope failure is retained as a permanent regression case.

The 13 v20 findings classify as 4 blocking findings and 9 advisory findings. The blocking defects collapse into one bounded bridge-climax scene cluster rather than multiple sentence patches.

This case must never be allowed to create an unbounded repair loop again.

## v21.1 zero-cost freeze

The canonical profile is `data/specifications/story_lab/spineforge_runtime_profile_v21_bounded_quality_frozen.json`.
It binds the runtime source commit, dependency SHA-256 values, prompts, contracts,
adapter, harness, tests, workflow, immutable source story, approved Spine,
reader profile, model slots, authorization state, and cost policy. Historical v20
files and its verifier remain unchanged. Paid authorization is false; consumed
is true because no grant has been issued.

Approved constraints are deterministic projections of exact JSON-pointer fields
from the human-approved Spine. Each quote retains its source pointer and hash.
The selected text establishes Arda's decisive cut, route-line use and loss,
rescue, exit state, and reveal limits. This extracts approved instructions; it
does not mechanically prove that generated prose obeys them.

This first fixture fixes repair scope at S159–S177, with S158/S178 boundaries.
Blocking findings outside that approved scope fail closed. Supporting arbitrary
new stories still requires a separately derived and qualified scene selection.
The older 13-finding audit is routing regression evidence, not a fresh audit of
the current c10 story revision.

The repair handoff includes actual source scene text. Replacement prose receives
fresh segmentation while prefix/suffix bytes remain unchanged. The final auditor
receives only scene, boundaries, original findings, reader profile and approved
constraints. Initial, repair and final calls cannot repeat. Persisted call events
contain exact inputs/responses and their hashes; STARTED is flushed before dispatch.
Missing provider accounting remains unknown, never zero, and stops the run.
Provider failures do not trigger retries. Local exclusive authorization claims
and workflow rerun guards are not a distributed, cross-checkout exactly-once store.

Run without API credentials:

```sh
python -m src.spineforge_v21_freeze
python -m pytest -q tests/test_spineforge_v21_*.py
python -m src.spineforge_v21_zero_cost_qualification
python -m src.spineforge_v21_simulation
```

Fake transport exercises the real adapter and guarded harness: clean ACCEPT/1,
repaired ACCEPT/3, non-convergent rejection/3, and budget rejection after calls
1, 2 and 3 respectively. Synthetic prose and fake auditor verdicts validate
control flow only; they do not demonstrate real story quality or model ability.

Stage ceilings stop subsequent calls after actual provider cost is reported.
They cannot cap the already completed provider request. Current pricing and
request-budget review plus explicit user authorization remain required before
the first paid run. Quality's $0.10 worst-case allowance does not establish the
whole English pipeline's $0.10-per-accepted-story target: Spine, Writer and
rejected attempts must also be included. Translation has a separate ledger.

## v21.2 lossless wire projection

v21.1 remains available at freeze commit
`7c1ae41e70fdd30775738a779a65e9778d3e38d8`. The active canonical profile now
identifies v21.2; this is a new freeze, not a claim that v21.1 hashes still match.

Only the adapter's model-facing projection changes. Full runtime artifacts,
topology, model slots, output token limits and stage cost ceilings are retained.
Current prose is sent once as rows of span ID, preceding whitespace and current
text. Trailing whitespace is retained. Concatenation reconstructs the exact
original prose; models see text adjacent to its ID rather than needing to count
character offsets. Historical source prose and repair bookkeeping are omitted
from the wire payload. Only exact duplicate canon-invariant quotes are removed;
extra invariants, approved quotes, findings and immutable boundaries survive.
The actual projected payload and its digest are recorded in the adapter result.

69 zero-cost tests include complete current-span recovery, repeated/Unicode text,
whitespace preservation, constraint/boundary preservation and rejection of
incomplete mappings. The six harness scenarios retain their original outcomes.
This proves data preservation and control flow, not real-model audit quality.

The fixture's measured prompt/schema character count falls from 84,818 to 25,320
for initial audit (70.1%), 24,685 to 16,104 for repair (34.8%), and 13,309 to
10,553 for final audit (20.7%). Final measurement uses synthetic two-sentence
prose and is not a prediction of the live final request. See
`evidence/spineforge-v21-zero-cost/wire-payload-measurement.json`.

Budget qualification remains open: at full configured output allowances, rough
chars/4 planning estimates still exceed the initial and repair ceilings. No
paid run is authorized. Input reduction must not be presented as proof of the
$0.10 accepted-story target; request/output budgeting is the next separate step.
