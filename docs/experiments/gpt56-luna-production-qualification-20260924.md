# GPT-5.6 Luna Production Qualification — 2026-09-24

Status: **PASS**
Canonical main SHA: `96619dece56c0c7c84a9ae59abc8e08a618698c7`

## Qualification contract

Generator:

`openai/gpt-5.6-luna`

Continuity evaluator:

`typesafe/jev-1.13`

Final judge:

`anthropic/claude-haiku-4.5`

Runtime registry:

`model-runtime-profile.v2`

Luna profile identities:

- profile SHA-256: `a938538d68df16de6bf5c0a2e9302f07e86595d5e807b94a248a269108d1027b`
- runtime-contract SHA-256: `ef8ad486f139c2885915203135c81e8eab3ed449ad507e20a133018461e1df0b`
- production-policy SHA-256: `d2cb13b2b9c09749cf7c47f76efe941fd7b41504882c705464c0b1036826e9d7`

Frozen benchmark cases:

1. Exploration / Mystery
2. Friendship / Social
3. Puzzle / Problem Solving
4. Fantasy Adventure
5. Emotional Calm

Each case was run twice on the same canonical main SHA.

## FX for user-facing cost reporting

Report-time FX:

**1 USD = 48.85 TRY**

Rate timestamp: 2026-09-24 03:32 UTC.

The CI evidence stores provider-native raw USD amounts. The table below converts full pipeline totals to TRY for reporting.

## Canonical 10-run stability matrix

| Case | Repeat | GitHub run | Accepted | Words | Final Haiku avg | Final min | Scene attempts | Semantic repairs | Full pipeline cost |
|---|:---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| 01 Exploration / Mystery | A | 35954755234 | yes | 2163 | 4.000 | 4 | 6 | 0 | ~2.05 TL |
| 01 Exploration / Mystery | B | 35955518973 | yes | 2127 | 4.125 | 3 | 8 | 2 | ~2.46 TL |
| 02 Friendship / Social | A | 35954760932 | yes | 2204 | 4.000 | 4 | 6 | 0 | ~2.07 TL |
| 02 Friendship / Social | B | 35955158555 | yes | 2199 | 4.000 | 4 | 6 | 0 | ~2.10 TL |
| 03 Puzzle / Problem Solving | A | 35954766614 | yes | 1946 | 4.750 | 4 | 9 | 0 | ~2.27 TL |
| 03 Puzzle / Problem Solving | B | 35955164751 | yes | 2080 | 4.000 | 4 | 6 | 0 | ~1.94 TL |
| 04 Fantasy Adventure | A | 35954772289 | yes | 2103 | 4.000 | 4 | 6 | 0 | ~1.96 TL |
| 04 Fantasy Adventure | B | 35955170754 | yes | 2210 | 4.000 | 4 | 6 | 0 | ~1.96 TL |
| 05 Emotional Calm | A | 35954778085 | yes | 2134 | 4.000 | 4 | 6 | 0 | ~2.06 TL |
| 05 Emotional Calm | B | 35955176790 | yes | 2118 | 4.000 | 4 | 6 | 0 | ~2.01 TL |

## Aggregate result

- accepted stories: **10 / 10**
- frozen cases with two successful repeats: **5 / 5**
- average word count: **2128.4**
- observed word range: **1946–2210**
- average final Haiku score: **4.0875 / 5**
- lowest observed final criterion score: **3**
- total accepted scenes: **60 / 60**
- total scene-generation attempts: **65**
- semantic scene repairs: **2**
- average full pipeline cost: **~2.09 TL/story**
- observed full pipeline cost range: **~1.94–2.46 TL/story**
- total cost of this 10-run canonical matrix: **~20.90 TL**

## Reliability observations

### Case 01

Repeat A accepted all six scenes on the first attempt.

Repeat B required two semantic repairs in Scene 5. JEV advisory evidence remained slightly below threshold for `no_contradiction` after the accepted scene, causing continuity escalation. The final Haiku judge still accepted the whole story with average 4.125, minimum 3, and no critical failures.

The final judge retained one prose-level repair target: clarify that Ada is confirming a beam path partially observed earlier rather than discovering it for the first time.

This is important evidence: Luna is not treated as repair-free. The shared repair and acceptance machinery remains necessary.

### Case 03

Repeat A required four generation attempts for Scene 2 but no semantic repair. Repeat B accepted all six scenes on the first attempt. The extra attempts did not reproduce, so this is not currently classified as a persistent Luna production-policy defect.

### Cases 02, 04, and 05

Both repeats accepted all six scenes on the first attempt with zero semantic repairs.

## Gate interpretation

The matrix is a **production qualification pass**, not a claim that every generated story is defect-free.

The evidence supports the following narrower conclusion:

- Luna can repeatedly complete the current story production contract across all five frozen scenario classes;
- the shared JEV/Haiku/deterministic repair architecture is sufficient to absorb the observed variability;
- no recurring failure signature currently justifies a Luna-specific pipeline fork or weaker acceptance thresholds;
- cost remains inside the LUMI target envelope by a wide margin.

The Case 01-B prose-level continuity advisory is preserved as evidence and must not be silently edited out of the qualification record.

## Supporting pre-promotion evidence

Before the canonical 10-run matrix:

- English Scene Plan Smoke run `35953125353` passed;
- full story Case 01 run `35953321695` passed on the initial verified Luna profile;
- profile-v2 full story Case 01 run `35954123070` passed with six scenes accepted on first attempt and final Haiku average 4.875.

These supporting runs are not counted in the canonical 10-run aggregate because they were produced before the final main promotion SHA.

## Qualification outcome

**PASS — promote GPT-5.6 Luna as the active Model Lab generator baseline and LUMI integration candidate.**

This outcome is bound to the exact runtime and production-policy identities listed above. Changing the profile invalidates direct reuse of this qualification.

Application production deployment remains a separate integration gate.
