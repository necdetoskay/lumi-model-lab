# SpineForge v8 — Durable Evidence Hardening

Status: ZERO-COST IMPLEMENTATION CANDIDATE

## Purpose

v8 does not change the v7 generation topology, models, prompts, contracts, ContextPack authority, strict transport, or retry semantics.

v7 Attempt 1 reached Sonnet Structural Frame and returned `structural_frame_contract_rejected`, but the exact result/revision feedback/usage checkpoint was lost when GitHub Actions artifact storage quota rejected the upload.

v8 exists only to remove artifact quota as a single point of evidence loss.

## Inherited generation topology

`SpineContextPack.v1`
→ Aion Creative Blueprint
→ Sonnet strict Structural Frame
→ Sonnet strict Structural Beats
→ Sonnet strict Structural Resolution
→ deterministic EpisodeSpine assembly
→ local Pydantic + ContextPack validation
→ Luna strict Product Gate
→ STOP / human review.

The implementation is inherited directly from `src/spineforge_v7.py`.

## Evidence channels

1. Runtime result.json remains checkpointed after every completed model call.
2. A compact sanitized summary prints exact failure, usage totals, stage coverage and retry target to immutable Actions logs. Preserved creative payloads are represented only by SHA-256 in logs.
3. Full run evidence will be persisted into a repository result path by the paid workflow.
4. Actions artifact upload is best-effort only and cannot turn a completed qualification into an evidence-loss failure.

No paid v8 inference is authorized before zero-cost tests and a new freeze are GREEN.
