# NOVA independent pilot protocol v1

Status: preregistered experiment design; real benefit **NOT ESTABLISHED**.
No production integration is authorized by any result of this protocol.

## Analyze and source quality gates

Every candidate must carry all twelve analysis fields, epistemic status,
limitations, source ID, source SHA-256, UTF-8 byte boundaries and span SHA-256.
Each mechanic has a second source for an explicit analogy/difference. A source
hash proves document integrity, not truth or semantic support. The current 18
records retain the predecessor's broad evidence spans; independent readers must
narrow and verify those spans before a source-quality PASS can be awarded.

Two independent source readers score each supported axis 0–3: 0 unsupported,
1 broad/plausible, 2 explicit local evidence, 3 explicit evidence plus a checked
counterexample/boundary. Require every claimed axis ≥2 from both, or mark it
UNKNOWN/WITHHELD. Actual opening vs summary opening, outcome vs durable state,
and local closure vs series-arc promise must be distinguished. Disagreement
requires adjudication; original records are retained with a new version.
This review has not occurred and is not simulated by the fixture run.

## Sampling and controls

Development pilot: 16 fixed briefs × 3 matched generation repetitions = 48 pairs,
96 stories. Each age has 12 pairs; each age/topic cell has three. The fixture
smoke uses only one repetition: 16 pairs / 32 short synthetic stories.

The same model revision, runtime settings, word budget, state, brief and paired
seed must be used for OFF/ON. Do not revise prompts after viewing early scores.
Randomize generation order; reset context between stories. Export only abstract
advice to ON. Do not pass sources, examples or answers. OFF receives no advice.
No selective reroll or replacement after poor prose. Missing stories/reviews
block the result rather than silently reducing the denominator. Operational
failures and retry costs must be reported separately for any real run.

Within each age, A/B position is exactly balanced and shuffled using a recorded
seed. Reviewers see story text, sample ID, frozen context and brief, never arm,
selected mechanics, model prompts or source evidence. Same-model judging and
author self-scoring are not independent evidence. Two human reviewers must cover
every story; their identities are operator-attested, not verified by software.
Record disagreement and any accidental unblinding. Text quality may itself reveal
the treatment; allocation concealment cannot guarantee perceptual blinding.

## Scoring and non-negotiable red gates

Rate **interest, causality, decision/cost, character, closure, originality** 1–5.
For every dimension: 1 absent/contradictory; 2 weak or generic; 3 coherent and
adequate; 4 specific, earned and engaging; 5 unusually strong without breaking
constraints. Average dimensions and then reviewers for each story; pair delta
is ON minus OFF. Reviewers justify their scores in notes.

| Gate | Failure examples |
|---|---|
| Age | Preschool fear, loss, violence, unsafe imitation; complexity unsuitable for target reader |
| Canon | New powers, altered established abilities, unauthorized characters or world rules |
| State | Established facts contradicted; unearned knowledge; outcome silently persisted |
| Originality | Franchise character/scene/technology copying or distinctive source event chain reskinned |

Any reviewer red gate FAIL blocks a successful real pilot. Lexical proper-name
and eight-token source-copy checks are only a first screen, not full semantic
canon/age/originality validation. A score disagreement >1 in any dimension
requires adjudication before success. Unresolved disagreement blocks acceptance.

## Objective pilot threshold

All of these must hold for the numeric `PILOT_THRESHOLD_MET` result:

1. ≥48 complete matched pairs with the entire 16-brief matrix, equal repeat coverage.
2. Exactly two complete, independent, blinded reviewers; no missing/duplicate ballots.
3. Zero red gate failures and zero unresolved >1-point disagreements.
4. Overall mean paired improvement ≥0.30 on the 1–5 scale; no age stratum mean <0.
5. The lower 95% Wilson bound for positive **brief-cluster** means is >0.50.
   Repeats of the same brief are not independent samples. Pair-level Wilson
   statistics are descriptive only. Ties count against benefit.

This is a conservative pilot decision rule, **not a power analysis or proof of
generalization**. There are only 16 brief clusters, four topics and a narrow LAB
world. Tune no thresholds from observed results. If the pilot succeeds, require
a separately preregistered replication with at least 16 new balanced briefs ×
3 repetitions, new allocation and independent readers. Broad-span source review,
age-qualified state review and replication remain external maturity gates.

Even numeric success leaves `integration_authorized=false`,
`state_commit_authorized=false` and `overall_maturity=NOT_ESTABLISHED` until actual
source/replication reviews exist. Integration would still require a distinct
future user decision. This task never proceeds to Story Harness integration.

## Cost and failure reporting

Fixture provider calls: 0; paid model expense: 0. This does not measure the cost
of the assistant's current chat. A real external bundle identifies generator,
authorization reference, approved budget and actual cost in integer micro-USD.
Booleans, negative costs, cost above budget and model mode without authorization
are rejected. These are declared external accounting, not provider-authenticated
receipts, and do not authorize any new dispatch.

Current smoke success rates distinguish selection (16/16), engineering tests,
and quality (unknown). Equal synthetic ratings are intentionally used so the
fixtures cannot manufacture an improvement. `NOT_ESTABLISHED_FIXTURE` is required
even if somebody changes synthetic scores to favor ON.

## External file contracts

`nova.story-bundle.v1` has exactly these fields:

```json
{
  "schema": "nova.story-bundle.v1",
  "mode": "HUMAN_MANUAL",
  "generator": "actual-independent-author-identity",
  "authorization_reference": "",
  "approved_budget_microusd": 0,
  "actual_cost_microusd": 0,
  "stories": [{"sample_id": "B04-exploration-R1-A", "text": "Complete original story text goes here."}]
}
```

This illustrative one-story object is intentionally incomplete and cannot pass
coverage. `EXTERNAL_AUTHORIZED_MODEL` additionally requires a real authorization
reference and accurate cost declaration. Do not replace those with invented data.

Ballots are a JSON array conforming to `schemas/ballot.schema.json`, one per story
per reviewer, bound to the exact story hash. `kind=HUMAN`, `independent=true`,
`saw_allocation=false`, `is_story_author=false`, all six scores and all four gates
are mandatory. A reviewer ID equal to generator ID is rejected. Changing the
story after rating invalidates its ballot. Reports preserve ballot, packet and
allocation hashes plus immutable ballot artifacts.

## Import hardening follow-up

Exact story hashes produced by the shipped fixture renderer are rejected even
when a bundle relabels them HUMAN_MANUAL or EXTERNAL_AUTHORIZED_MODEL. This only
detects known exact fixture text; edited or unrelated synthetic prose cannot be
reliably classified by this check. Honest provenance and independent reviewers
are still required. Tests using modified synthetic prose exercise plumbing only
and do not create quality evidence.

The import receipt now also binds `review/context.json`. Changing a reviewer's
state or age brief after import invalidates scoring, just as changing story text
does. Reports include the review-context hash. Old external import receipts that
lack this field fail closed and require a fresh import in a new trial directory;
they are never silently upgraded or overwritten. The checked-in fixture pilot
does not use the external importer and remains an unchanged historical artifact.
