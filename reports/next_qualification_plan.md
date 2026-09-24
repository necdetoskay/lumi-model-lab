# Next Adaptive Qualification Plan

Scope wave: `configs/qualification_waves/age-relative-standard-v2.yaml`
Active generation protocol: `english-story-production.v3`

Executable scope: **24** cases; canonical STANDARD scope: **80**; fixture-backed out-of-scope: **56**.
Current protocol inside executable scope: observed **20**, unknown **4**, thin **18**, provisional **2**, established **0**.

| Lane | Case | Age tier | Family | Target | Current | Current repairs/run | Current attempts/run | Family age coverage | Historical repairs/run |
|---|---|---|---|---:|---|---:|---:|---:|---:|
| SENTINEL_REPEAT | early-child--exploration-mystery | EARLY_CHILD | exploration_mystery | 500 | THIN (1) | 2.00 | 12.00 | 5/8 | 0.67 |
| COVERAGE_EXPANSION | child--exploration-mystery | CHILD | exploration_mystery | 1500 | THIN (1) | 0.00 | 6.00 | 5/8 | 0.67 |
| COVERAGE_EXPANSION | middle-child--puzzle-problem-solving | MIDDLE_CHILD | puzzle_problem_solving | 2800 | UNKNOWN (0) | 0.00 | 0.00 | 7/8 | 0.00 |
| COVERAGE_EXPANSION | teen--exploration-mystery | TEEN | exploration_mystery | 3800 | THIN (1) | 0.00 | 7.00 | 5/8 | 1.00 |
| COVERAGE_EXPANSION | young-adult--exploration-mystery | YOUNG_ADULT | exploration_mystery | 4200 | UNKNOWN (0) | 0.00 | 0.00 | 5/8 | 0.00 |
| COVERAGE_EXPANSION | adult--exploration-mystery | ADULT | exploration_mystery | 4200 | THIN (1) | 0.00 | 8.00 | 5/8 | 0.67 |
| COVERAGE_EXPANSION | mature-adult--exploration-mystery | MATURE_ADULT | exploration_mystery | 4200 | UNKNOWN (0) | 0.00 | 0.00 | 5/8 | 0.00 |
| COVERAGE_EXPANSION | senior--exploration-mystery | SENIOR | exploration_mystery | 4200 | UNKNOWN (0) | 0.00 | 0.00 | 5/8 | 1.00 |

> Production-frequency weighting is intentionally disabled until real LUMI telemetry exists. The planner does not invent popularity.
