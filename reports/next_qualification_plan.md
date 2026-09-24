# Next Adaptive Qualification Plan

Scope wave: `configs/qualification_waves/age-relative-standard-v2.yaml`
Active generation protocol: `english-story-production.v3`

Executable scope: **24** cases; canonical STANDARD scope: **80**; fixture-backed out-of-scope: **56**.
Current protocol inside executable scope: observed **24**, unknown **0**, thin **17**, provisional **7**, established **0**.

| Lane | Case | Age tier | Family | Target | Current | Current repairs/run | Current attempts/run | Family age coverage | Historical repairs/run |
|---|---|---|---|---:|---|---:|---:|---:|---:|
| SENTINEL_REPEAT | adult--puzzle-problem-solving | ADULT | puzzle_problem_solving | 4200 | THIN (1) | 2.00 | 9.00 | 8/8 | 0.00 |
| COVERAGE_EXPANSION | early-child--puzzle-problem-solving | EARLY_CHILD | puzzle_problem_solving | 500 | THIN (1) | 1.00 | 7.00 | 8/8 | 1.33 |
| COVERAGE_EXPANSION | child--emotional-development | CHILD | emotional_development | 1500 | THIN (1) | 0.00 | 6.00 | 8/8 | 1.50 |
| COVERAGE_EXPANSION | middle-child--exploration-mystery | MIDDLE_CHILD | exploration_mystery | 2800 | THIN (1) | 0.00 | 6.00 | 8/8 | 0.00 |
| COVERAGE_EXPANSION | teen--emotional-development | TEEN | emotional_development | 3800 | THIN (1) | 1.00 | 7.00 | 8/8 | 0.00 |
| COVERAGE_EXPANSION | young-adult--puzzle-problem-solving | YOUNG_ADULT | puzzle_problem_solving | 4200 | THIN (1) | 0.00 | 6.00 | 8/8 | 1.00 |
| COVERAGE_EXPANSION | mature-adult--emotional-development | MATURE_ADULT | emotional_development | 4200 | THIN (1) | 1.00 | 7.00 | 8/8 | 1.00 |
| COVERAGE_EXPANSION | senior--puzzle-problem-solving | SENIOR | puzzle_problem_solving | 4200 | THIN (1) | 0.00 | 8.00 | 8/8 | 1.00 |

> Production-frequency weighting is intentionally disabled until real LUMI telemetry exists. The planner does not invent popularity.
