# LUMI Story Corpus v1

Status: DESIGN-FROZEN FOR SPEC GENERATION
Owner repo: `lumi-model-lab`
Product safety/release contracts: `Project_LUMI`

## Purpose

Create a reusable, model-agnostic corpus of 100 high-quality Turkish child stories. The corpus is not a Gemma-specific dataset. It is a durable source dataset for SFT/QLoRA, distillation, model comparison, judge calibration, preference learning, failure analysis, and future training experiments.

The first intended student experiment is Gemma 4 E4B, but exports must remain derived artifacts.

## Non-negotiable rules

1. Raw generation artifacts are immutable and retained even when rejected.
2. Accepted, rejected, curated, and exported views are separate from raw evidence.
3. Frozen benchmark specifications are never included in training/validation/holdout corpus generation.
4. Safety and quality are separate gates. A high quality score never overrides safety.
5. Every story keeps stable provenance: corpus id, spec id/version, teacher model, prompt version, generation request, token usage, cost, technical evidence, safety evidence, judge evidence, and content fingerprint.
6. Production safety/red-team cases are not training stories.
7. Exports such as Unsloth/ChatML/Alpaca are generated from the canonical corpus; they are never the source of truth.

## Corpus size and length distribution

Total: 100 stories, approximately 200,000 Turkish words.

| Target words | Count |
|---:|---:|
| 1500 | 10 |
| 1800 | 15 |
| 2000 | 50 |
| 2200 | 15 |
| 2500 | 10 |

The training goal is length conditioning rather than memorizing one fixed story length. Technical validation for each target will use a versioned tolerance policy; the formal policy must be stored with the record.

## Age distribution

| Age band | Count |
|---|---:|
| 4–5 | 10 |
| 6–8 | 60 |
| 9–10 | 25 |
| 11–12 | 5 |

The 6–8 band remains the primary LUMI story target while the other bands teach controlled vocabulary, sentence complexity, explanation density, and narrative complexity.

## Narrative-family distribution

| Family | Count |
|---|---:|
| exploration_mystery | 12 |
| friendship_social | 12 |
| puzzle_problem_solving | 12 |
| nature_environment | 10 |
| scientific_curiosity | 10 |
| adventure_journey | 10 |
| emotional_growth | 10 |
| teamwork_collaboration | 8 |
| everyday_fantastical_discovery | 8 |
| world_lore_discovery | 8 |

## Story diversity dimensions

Each unique specification must intentionally vary multiple dimensions rather than only changing names or scenery:

- setting and environment
- protagonist archetype
- central problem
- reasoning pattern
- emotional dimension
- educational dimension
- dialogue density
- narrative structure
- ending type
- required elements
- forbidden elements
- age-appropriate vocabulary level

Repeated motif concentration must be reviewed between batches. A corpus dominated by one skeleton (for example mysterious light -> cave -> map) is a diversity failure even when individual stories score well.

## Reasoning/constraint coverage

Coverage targets may overlap across stories:

- 30 stories: wrong hypothesis corrected by observation/evidence
- 25 stories: combine at least two clues
- 20 stories: plan -> attempt -> failure -> correction
- 20 stories: character disagreement resolved constructively
- 15 stories: emotional misunderstanding
- 20 stories: multiple solution alternatives considered
- 10 stories: quiet/observational narrative
- 15 stories: dialogue-forward narrative
- 10 stories: explicit world/lore discovery

These are corpus-level coverage goals, not universal requirements. No single pattern should appear in every story.

## Unique specifications and alternate generations

The corpus contains:

- 80 unique story specifications
- 20 alternate generations created from selected unique specifications

Alternate generations provide controlled same-spec comparison data for future preference/ranking work. They must retain the same `spec_id` while receiving unique `story_id`, generation seed/request metadata, and content fingerprint.

## Batch plan

Generate in four batches of 25.

After each batch, stop and review:

- technical pass rate
- target-length distribution and deviation
- EOS/completion behavior
- repetition metrics
- safety failures
- quality score distribution
- age-band failures
- motif/setting/structure duplication
- teacher failure patterns
- total cost

The next batch may not begin until the review is recorded. Prompt/spec policy changes after a batch require a new version; previous artifacts are not rewritten.

## Canonical lifecycle

`SPEC_CREATED -> GENERATED -> TECHNICAL_PASS/FAIL -> SAFETY_PASS/FAIL -> JUDGED -> ACCEPTED/REJECTED -> CURATED -> SPLIT_ASSIGNED -> EXPORTED`

A rejected generation remains permanently available for failure analysis, judge calibration, and future preference-pair experiments.

## Canonical repository layout

```text
data/
  corpus/
    lumi_story_corpus_v1/
      manifest.json
      specifications/
      raw/
      safety/
      judgments/
      accepted/
      rejected/
      curated/
      exports/
```

Suggested stable identifiers:

- `LUMI-CORPUS-V1-SPEC-0001`
- `LUMI-CORPUS-V1-STORY-0001-A`
- `LUMI-CORPUS-V1-STORY-0001-B` for an alternate generation

## Canonical metadata minimum

Each story record must make the following recoverable without relying on filenames:

- `corpus_version`
- `story_id`
- `spec_id`
- `spec_version`
- `teacher_model`
- `provider`
- `prompt_version`
- `target_words`
- `actual_words`
- `age_min`, `age_max`, `age_band`
- `story_family`
- `difficulty`
- `setting_tags`
- `theme_tags`
- `reasoning_tags`
- `narrative_tags`
- `technical_validation`
- `safety_evaluation` reference/version
- `quality_judgment` reference/version
- `corpus_status`
- `split`
- `request` / reproducibility metadata
- `usage` and `cost`
- `content_fingerprint`

## Split policy

Final curated corpus target:

- 80 train
- 10 validation
- 10 holdout

Split assignment is deterministic and leakage-checked. Alternate generations from one specification must not be allowed to leak a near-identical prompt/story family instance across train and holdout in a way that invalidates evaluation.

The production frozen benchmark remains completely separate from all three corpus splits.

## Safety dependency

Planning and specification generation may proceed immediately.

Paid generation may begin after the minimum safety/release metadata contract is fixed in Project_LUMI so generated artifacts do not need destructive migration later. Full production implementation of the Story Safety/Release epics is not required before corpus generation.

Every generated story must at minimum pass:

`technical gate -> child-safety evaluation -> quality judge -> corpus curator`

before being eligible for `curated` status.

## Generation teacher

Initial corpus teacher: GPT Luna.

Teacher identity is evidence, not part of the corpus schema. Future corpus versions may use another teacher while preserving the same canonical data principles.

## Acceptance criteria for starting Batch 1

Before the first paid 25-story batch:

- [ ] 100-slot design matrix is generated and reviewed.
- [ ] 80 unique spec slots and 20 alternate-generation slots are explicitly identified.
- [ ] Frozen benchmark leakage check passes.
- [ ] StorySpec v2 / corpus metadata schema is implemented.
- [ ] Technical validator records target-length policy and repetition evidence.
- [ ] Safety result schema/version is available.
- [ ] Quality judge configuration is scoped and does not overwrite prior evidence.
- [ ] Batch manifest records exact prompt/model/config versions.

Only after these checks do we spend on Batch 1.