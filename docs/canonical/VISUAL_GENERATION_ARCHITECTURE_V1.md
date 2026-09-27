# LUMI Visual Generation Architecture v1 — Canonical Contract

Status: **Canonical / architecture baseline**  
Date: 2026-09-27  
Canonical owner: **LUMI Model Lab**  
Scope: **Visual generation, routing, continuity, prompt compilation, validation, and cost/latency lineage**

## 1. Purpose

LUMI treats visual generation as a first-class AI workload.

The system must:
- support multiple image-generation models/providers;
- preserve user-selected visual style independently from the underlying model;
- preserve character/world visual continuity;
- use category-specific prompt structures;
- keep model-specific prompt/runtime behavior inside versioned model profiles;
- capture provider/model/cost/latency/retry lineage for every invocation;
- retain immutable generation evidence;
- qualify routing using measured quality, continuity, latency, and cost.

Governing rule:

> Users choose how their LUMI world should look. LUMI chooses how to realize that style.

## 2. Architecture

```text
AI Orchestrator
  -> Visual Generation Agent
      -> Visual Intent Builder
      -> Visual Model Router
      -> Prompt Compiler
      -> Provider/Model Adapter
      -> Visual Validator
      -> Visual Artifact
      -> Visual Invocation Ledger
```

The global AI Orchestrator owns portfolio-level execution lineage, budgets, retries, and cross-agent accounting. The Visual Generation Agent owns visual workflow semantics.

## 3. Canonical entities

### 3.1 UserVisualPreference

Stores the user's selected visual preference, not a raw provider choice.

Minimum fields:
- profileId
- preferredStyleId
- preferredStyleVersion
- qualityTier
- defaultAspectRatio
- allowAutomaticModelRouting
- customStyleOverrides[]
- customNegativeOverrides[]
- selectionSource
- selectedAt

Long provider-specific prompt text must not be embedded directly in the user profile.

### 3.2 VisualStyleProfile

Model-independent aesthetic identity.

Minimum fields:
- id
- version
- displayName
- status
- baseStyleDirectives[]
- colorPolicy
- lightingPolicy
- globalNegativeDirectives[]
- categoryOverrides

Initial style families:
- LUMI_STORYBOOK_SOFT
- LUMI_CINEMATIC_ADVENTURE
- LUMI_PAINTED_FANTASY
- LUMI_SOFT_3D
- LUMI_WATERCOLOR

Style identity is user-facing. Model identity is implementation-facing.

### 3.3 VisualModelProfile

Every image model has a versioned profile containing runtime facts, LUMI usage policy, capabilities, prompt behavior, known weaknesses, pricing, and qualification evidence.

Minimum metadata:
- provider/model/provider model version/profile version/status
- supported categories/styles
- reference-image, negative-prompt, image-to-image, inpainting, transparent-background capabilities
- aspect-ratio/resolution limits
- strengths/weaknesses
- preferred prompt ordering/detail/length
- model-specific negative-prompt behavior
- retry/timeout policy
- pricing metadata
- qualification metrics

Governance rule inherited from `MODEL_RUNTIME_PROFILE_REGISTRY_V2.md`:

> If behavior changes because the visual model changes, that behavior belongs in the model profile. Shared correctness rules remain model-independent.

### 3.4 CharacterVisualProfile

Canonical visual identity for a character:
- apparent age
- skin/eyes/hair
- signature facial traits
- signature clothing/accessories
- identity mustKeep[]
- softFlexible[]

Scene-local wear, dirt, damage, held objects, weather, or temporary costume state must not overwrite this profile.

### 3.5 WorldVisualProfile

Stable visual DNA for a world/habitat/location family:
- biome
- architecture
- technology level
- dominant materials
- palette
- recurring motifs
- forbidden visual elements
- scale/atmosphere rules

### 3.6 StoryVisualState

Temporary story/scene visual state:
- clothing dirt/damage
- held/visible items
- temporary marks
- time of day
- weather
- scene-local environmental changes

StoryVisualState must never silently mutate CharacterVisualProfile or WorldVisualProfile.

### 3.7 VisualCategoryTemplate

Defines prompt structure and validation expectations per category.

Canonical starting categories:
- CHARACTER_PORTRAIT
- CHARACTER_SCENE
- ITEM
- INVENTORY_CARD
- ENVIRONMENT
- WORLD_KEY_ART
- COVER_ART
- MAP_ART

### 3.8 VisualArtifact

Immutable record of a delivered generation result.

Record at least:
- artifact id
- profile id
- category
- referenced character/world/story/scene ids
- style id + version
- model profile id + version
- category-template id + version
- generated storage reference
- validation status
- creation timestamp
- invocation id(s)

Historical artifacts are not rewritten when the user changes style later.

### 3.9 VisualInvocationLedger

Every provider call records:
- invocation id
- parent workflow/task id when available
- profile id/category
- provider/model/model profile id/version
- startedAt/completedAt/latencyMs
- image count/dimensions
- actual or estimated provider cost + currency + cost source
- retry attempt/status
- artifact ids
- safe/useful provider response metadata

## 4. Category-specific prompt contracts

A single generic image prompt builder is **not** canonical.

### CHARACTER_PORTRAIT
Task -> identity -> appearance -> face/hair/eyes -> apparent age/build -> signature clothing/accessories -> pose -> expression -> framing -> style -> lighting -> negatives.

### CHARACTER_SCENE
Task -> scene context -> character identity -> StoryVisualState -> action -> other characters -> environment -> required objects -> mood -> lighting -> composition -> style -> negatives.

### ITEM
Task -> object identity -> shape -> materials -> colors -> functional details -> condition -> presentation angle -> background -> style -> negatives.

### INVENTORY_CARD
Single-object presentation with clean silhouette, controlled framing, limited background, UI-readable scale, consistent shadow/orientation, optional transparency.

### ENVIRONMENT
Location identity -> canonical landmarks -> architecture/nature -> scale -> time/weather -> atmosphere -> focal point -> camera -> lighting -> style -> negatives.

### WORLD_KEY_ART
World identity -> habitat -> biome -> civilization -> macro landmarks -> scale cues -> narrative atmosphere -> palette -> lighting -> composition -> style -> negatives.

### COVER_ART
Story identity -> main character(s) -> core motif -> narrative mood -> strong focal composition -> title-safe area -> lighting/style -> negatives.

### MAP_ART
Map type -> known locations -> geography -> routes -> exploration state -> label policy -> hierarchy -> map style -> negatives.

## 5. Prompt Compiler

Inputs:
- VisualRequest
- VisualIntent
- UserVisualPreference
- VisualStyleProfile
- VisualModelProfile
- VisualCategoryTemplate
- CharacterVisualProfile
- WorldVisualProfile
- StoryVisualState
- request overrides

Outputs:
- positive prompt
- negative prompt when supported
- provider/model options
- aspect ratio/resolution
- reference-image strategy
- continuity constraints
- compiled profile/template fingerprints

Canonical merge order:
1. task
2. canonical subject identity
3. story/scene context
4. continuity state
5. category rules
6. user style preference
7. style profile
8. model-specific prompt policy
9. output constraints
10. negative constraints

## 6. Negative prompt layering

Negative constraints are layered, not stored as one global string:

```text
GLOBAL STYLE NEGATIVES
+ CATEGORY NEGATIVES
+ MODEL-SPECIFIC NEGATIVES
+ USER OVERRIDES
```

Character examples: extra limbs, duplicate accessories, adult proportions, wrong eye color, identity drift.  
Inventory examples: duplicated objects, busy background, unclear silhouette, hands unless requested, perspective distortion.  
Environment examples: random crowds, forbidden modern objects, incorrect architecture, visual clutter.

## 7. Model routing

Routing considers:
- selected VisualStyleProfile
- category
- model capabilities
- historical quality
- identity/style continuity
- validation pass rate
- latency
- cost
- retry rate

The same user style may route to different models by category.

Example:

```text
Storybook
  CHARACTER_PORTRAIT -> Model A
  CHARACTER_SCENE    -> Model B
  ITEM               -> Model C
  ENVIRONMENT        -> Model D
```

The user still experiences one coherent style family.

## 8. Visual onboarding

On first visual preference selection, LUMI renders the same canonical subject/situation through several controlled style candidates.

Example:
- Soft Storybook
- Cinematic Adventure
- Soft 3D
- Painted Fantasy
- Watercolor

The user selects the visual result/style, not necessarily a model/provider name.

Persist:
- selected style id/version
- selection source/evidence
- successful model profile
- timestamp

The model remains routable later unless the user explicitly disables automatic routing.

## 9. Continuity contract

Visual generation composes:

```text
CharacterVisualProfile
+ WorldVisualProfile
+ StoryVisualState
+ VisualStyleProfile
+ category intent
```

CharacterVisualProfile and WorldVisualProfile contain durable identity. StoryVisualState contains temporary state.

Reference-image support may be used when qualified, but reference images do not replace canonical structured identity.

## 10. Validation

Validation is category-aware.

Character checks:
- identity preserved
- apparent age preserved
- hair/eyes/signature traits correct
- required clothing/accessories present

Story-scene checks:
- required characters/objects present
- action and scene state respected
- environment/world constraints respected

Inventory checks:
- correct object
- single readable silhouette
- usable framing/background

Environment/world checks:
- location/world identity correct
- forbidden elements absent
- style family preserved

Critical failures may trigger bounded retry. Minor style/lighting variation need not.

Every retry is a new invocation and contributes to total cost/latency.

## 11. Versioning and reproducibility

Version at minimum:
- VisualStyleProfile
- VisualModelProfile
- VisualCategoryTemplate
- CharacterVisualProfile
- WorldVisualProfile

Every VisualArtifact stores exact versions/fingerprints used.

Never solve a new model weakness by silently appending model-specific text to a global prompt. Update the appropriate VisualModelProfile, add regression evidence, and requalify.

## 12. Qualification metrics

Canonical evidence space:

```text
model x style x category x resolution/quality tier
```

Track:
- generationSuccessRate
- validationPassRate
- identityConsistencyScore
- styleConsistencyScore
- userSelectionRate
- retryRate
- averageLatency
- p95Latency
- averageCost
- costPerAcceptedImage

These metrics inform VisualModelRouter; they do not rewrite historical user selections or artifacts.

## 13. Cost and latency lineage

Visual calls participate in the same global AI execution accounting principles used by LUMI runtime work.

For every call preserve:
- workflow/task lineage
- provider/model/profile identity
- true started/completed timestamps
- latency
- retry count
- actual/estimated cost
- status
- resulting artifacts

A failed ledger write must never cause a paid inference to be silently repeated.

## 14. P0–P8 implementation roadmap

### P0 — Audit & freeze
Inventory current image calls, storage, provider metadata, existing image state, and cost tracking. Freeze v1 contracts.

### P1 — Core visual domain
Implement entities/schemas for UserVisualPreference, VisualStyleProfile, VisualModelProfile, VisualCategoryTemplate, CharacterVisualProfile, WorldVisualProfile, StoryVisualState, VisualArtifact, and VisualInvocationLedger.

### P2 — Visual Generation Agent
Implement `generateVisual(request)` with context resolution, VisualIntent, model selection, compilation, execution, ledger, and artifact creation.

### P3 — Prompt Compiler
Implement category-specific builders:
- buildCharacterPortraitPrompt
- buildCharacterScenePrompt
- buildItemPrompt
- buildInventoryCardPrompt
- buildEnvironmentPrompt
- buildWorldPrompt
- buildCoverPrompt
- buildMapPrompt

Do not introduce one generic builder containing category conditionals.

### P4 — Model profiles & adapters
Integrate the first 4–5 candidate models. Keep provider/model-specific tuning in profiles/adapters.

### P5 — Visual style system
Implement initial versioned style families, category overrides, and negative-prompt layers.

### P6 — Visual onboarding
Generate controlled comparison candidates, persist the selected style, and allow later style change without rewriting old artifacts.

### P7 — Continuity & validation
Wire CharacterVisualProfile, WorldVisualProfile, StoryVisualState, category validators, and bounded retry policy.

### P8 — Qualification & evidence-based routing
Run model x style x category qualification and feed measured quality/continuity/cost/latency evidence into routing.

## 15. Canonical decisions

1. Visual generation is owned by a dedicated Visual Generation Agent under the AI Orchestrator.
2. Users select visual style; providers/models remain implementation details.
3. Style profiles and model profiles are separate.
4. Every supported image model has versioned metadata and model-specific prompt/runtime policy.
5. Every visual category has its own prompt contract/builder.
6. Style and negative directives are versioned and automatically compiled into requests.
7. Character/world durable identity is separate from temporary StoryVisualState.
8. VisualArtifact is immutable generation evidence.
9. Every invocation records provider/model/cost/latency/retry lineage.
10. Routing may choose different models per category while preserving one user style.
11. Historical artifacts remain unchanged when user preferences or model routing change.
12. Model-specific fixes belong in model profiles, not global prompt accumulation.
13. Qualification evidence, not intuition, should drive future routing.

## 16. Relationship to existing canon

This document extends the same model-profile governance principles defined in:

- `docs/canonical/MODEL_RUNTIME_PROFILE_REGISTRY_V2.md`

It does not authorize weakening shared correctness or continuity constraints for a particular model. Visual models control how a visual request is executed; canonical LUMI visual identity and validation rules define what counts as correct.
