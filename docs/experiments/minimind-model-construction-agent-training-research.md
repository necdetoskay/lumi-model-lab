# MiniMind Model Construction & Agent Training Research

Status: Backlog / Research candidate  
Priority: High learning value, not production adoption  
Created: 2026-09-03  
Source video: https://www.youtube.com/watch?v=LA2tuPk2Y-I  
Upstream project: https://github.com/jingyaogong/minimind

## Decision

Adopt MiniMind as an **experimental learning and model-construction platform** inside LUMI Model Lab.

Do **not** adopt MiniMind 64M as a production story-generation model for LUMI.

The primary value is to expose and measure the full model-development chain below the normal LoRA/fine-tuning layer:

`raw data -> tokenizer -> pretraining -> SFT -> preference optimization -> RL -> tool use -> agentic RL -> distillation -> serving/evaluation`

This research remains isolated from the authoritative LUMI production runtime until an experiment separately proves a production-relevant capability.

## Why this belongs in LUMI Model Lab

LUMI Model Lab already evaluates teacher/student models, synthetic data, fine-tuning, judge quality and inference economics. MiniMind adds a lower-level construction curriculum in which the Lab can observe exactly where behavior changes during training.

The goal is therefore not to build a competitive general-purpose LLM. The goal is to make model behavior, training stages and architecture trade-offs measurable and understandable.

## Research tracks

### 1. Model Construction Lab

Build a reproducible staged pipeline:

1. tokenizer training
2. small dense base model
3. pretraining
4. supervised fine-tuning
5. LoRA comparison
6. preference optimization
7. evaluation after every stage

The same qualification set should be run after each stage so the Lab can show behavior deltas instead of only final scores.

### 2. Dense vs MoE Lab

Compare the MiniMind dense model with its MoE variant using controlled datasets and evaluation gates.

Measure at minimum:

- active vs total parameters
- VRAM usage
- training throughput
- inference latency
- loss / convergence
- task quality
- specialization behavior
- routing stability where observable

This is an education/research comparison, not a claim that the MoE variant should replace a LUMI production model.

### 3. Distillation Lab

Evaluate whether a small MiniMind-family student can learn narrow LUMI-oriented tasks from stronger teacher models.

Candidate tasks:

- request classification
- complexity estimation
- safety pre-filtering
- tool routing
- scene/type classification
- state-mutation classification
- context relevance scoring
- Progressive Reasoning Gate routing signals

A distilled student must only be considered for production after task-specific qualification proves that it is safer/economically useful than the existing route.

### 4. Adaptive Thinking / Progressive Reasoning Research

Use MiniMind's thinking controls as a sandbox for questions relevant to LUMI's Progressive Reasoning Gate:

- Which task classes actually benefit from explicit reasoning?
- What quality gain is obtained from thinking-on vs thinking-off?
- What are latency and token/compute costs?
- Can a small routing model predict when deeper reasoning is necessary?

Results may inform PRG design, but do not automatically change LUMI architecture.

### 5. Agentic RL Lab

Study multi-turn tool-use training with GRPO/CISPO-style approaches after the basic construction pipeline is understood and stable.

Possible future LUMI-derived sandbox tasks:

- choose the correct tool for a bounded task
- retrieve authoritative state before mutation
- reject an invalid state transition
- minimize unnecessary tool calls
- obey canonical-state constraints
- complete a short multi-step plan

Example reward dimensions:

- correct tool selection
- correct final result
- canonical-state compliance
- invalid-action rejection
- unnecessary-call penalty
- replay/idempotency correctness where applicable

This track must remain a sandbox. No agentic-RL-trained model is allowed into LUMI runtime without independent safety, correctness and regression qualification.

## Initial hardware target

Primary local experiment target:

- NVIDIA RTX 4060 Laptop GPU
- 8 GB VRAM

The upstream project's headline timing/cost numbers are not treated as a local performance guarantee. They were reported under different hardware/settings. Our own measurements are authoritative for LUMI Model Lab.

## First experiment: 64M Dense Baseline

The first implementation should deliberately remain small.

### Goal

Prove that the Lab can execute and observe a minimal end-to-end model-construction pipeline on the local RTX 4060-class environment.

### Scope

1. pin upstream MiniMind revision
2. record license and dependency snapshot
3. create a small controlled training dataset
4. train/prepare tokenizer
5. run a minimal 64M dense pretraining experiment
6. run SFT
7. evaluate before and after SFT using the same qualification set
8. record VRAM, wall-clock duration, throughput and artifact sizes
9. save checkpoints and experiment metadata in reproducible form

### Non-goals for the first experiment

- full upstream dataset reproduction
- production-quality story generation
- MoE training
- Agentic RL
- production LUMI integration
- replacing current API models

## Qualification evidence

Every experiment should retain:

- source revision / commit
- exact config
- dataset fingerprint
- tokenizer fingerprint
- seed where applicable
- hardware information
- dependency/environment snapshot
- start/end timestamps
- peak VRAM
- training loss history
- checkpoint references
- evaluation inputs/outputs
- judge/metric results
- failure notes
- estimated compute/economic cost

A result without reproducible evidence is an observation, not a Lab baseline.

## Comparison strategy

At each model stage, preserve a stable micro qualification suite containing at least:

- language coherence
- instruction following
- factual restraint / hallucination tendency
- structured-output compliance
- simple reasoning
- tool-call formatting when relevant

Later LUMI-specific suites may be added for routing, state classification and PRG decisions.

## Promotion gates

Research findings may progress through these states:

`observed -> reproducible -> qualified -> candidate for LUMI-specific experiment -> architecture review -> production consideration`

No finding skips directly from upstream/demo evidence to production adoption.

## Relationship to current LUMI work

This research is intentionally deferred. It should not interrupt current authoritative LUMI / EPES / PRG implementation work.

When resumed, start only with the **64M Dense Baseline**. Complete its evidence and learning report before opening MoE, distillation or Agentic RL implementation slices.

## Expected learning outcome

After the baseline and subsequent tracks, LUMI Model Lab should be able to explain and experimentally demonstrate:

- what the tokenizer contributes
- what pretraining changes
- what SFT changes
- what preference optimization changes
- how dense and MoE compute differ
- where small-model distillation is useful
- when reasoning should be gated
- how tool-using agent behavior can be trained and evaluated

That learning value is the primary success criterion of this research item.
