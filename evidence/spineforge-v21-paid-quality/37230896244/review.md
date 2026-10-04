# Single authorized bridge experiment — 37230896244

Outcome: **REJECT_PROVIDER_FAILURE** at FINAL_AUDIT. Not ACCEPT; not a valid
REJECT_NON_CONVERGENT verdict. No additional paid call is authorized by this run.

Authorized commit: cdab9a6da0f55acaf49b7122dd14ef02832436ea.
Runtime: SPINEFORGE-BOUNDED-QUALITY-FROZEN-v21.3. The v21.3 change isolates the
experiment's budget/authorization profile in CI; model prompts and story topology
remain those qualified in v21.2. Production authorization remains false.

| Stage | Input tokens | Output tokens | Reported USD | Wall seconds |
| --- | ---: | ---: | ---: | ---: |
| Initial audit | 9,949 | 298 | 0.022878 | 5.551 |
| Scene repair | 5,034 | 955 | 0.019618 | 9.412 |
| Final audit | 5,106 | 528 | 0.015492 | 6.060 |
| Total | 20,089 | 1,781 | 0.057988 | 21.023 |

All three responses reported usage. Reasoning tokens reported: 0. These are
provider-reported figures, not proof that the provider performed no reasoning.
Latency sums model-call wall times and excludes runner queue/setup time.
This is quality-experiment cost, not accepted-story or complete production cost.

Initial audit found one serious physical_feasibility defect across
S167/S172/S173/S175: the line has both ends attached but a free end is thrown,
and the falling bridge/load/cut chain does not follow. The runtime rewrote the
whole approved S159–S177 cluster once. The repair claimed the exact finding set.
Source SHA and prefix/suffix bytes were independently checked after recovery.

The final adapter raised AdapterResponseError after accounting for a returned
response. Its saved provider_evidence is null. The adapter's schema-validation
error path discards the raw response, while the runtime records only the error
class, losing the specific validation message. Consequently the precise invalid
field and the final auditor's semantic verdict cannot be recovered from this
result. Do not infer final cleanliness from final_blocking_count=0: parsing failed.

No retry, second repair, translation or state commit ran. The candidate remains
rejected and is stored as rejected-candidate-scene.txt, not an accepted story.
GitHub workflow SUCCESS only means the harness completed and uploaded evidence;
it does not mean the story passed.

## Reader review (assistant assessment, no further model API call)

The scene still does not establish Nisa's side of the gap. They arrive together,
then Arda throws the coil across to Nisa, then she hauls herself across. Arda clips
a loop to his harness and later clips on again without explaining the change.
The line's load path and why the one cut releases every bridge connection remain
ambiguous. Arda retains the decisive cut, but preserving its actor is insufficient
to prove physical causality. This candidate should not be called publication-ready.

## Evidence and next decision

Result and envelope were recovered from the completed job log. The result was
serialized using the harness's exact format; SHA-256 matches the envelope's
c15764b82dc2d066d752208ee0bec0c9a5f5749ad5c91eefd859f826246f64cd.
The original JSONL call ledger is in the uploaded GitHub artifact; no replacement
ledger has been synthesized here.

Preserve this failed case. A subsequent offline fix should retain malformed final
response and validation diagnostics. That fix requires no paid retry. Do not
launch another bridge repair or declare this run successful to recover sunk cost.
Any new paid experiment needs a separate user decision.
