"""Bounded OpenRouter model adapter for coherence / local repair / re-audit.

DO NOT instantiate for an unapproved paid stage. The caller must hold
explicit per-stage authorization and a durable one-use run-bound grant.
Frozen V3 is untouched. No automatic retry or alternate model is allowed.
"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from src import english_story_pipeline as english
from src import v3_single_attempt_guard as guard_base
from src.story_defect_detection import segment_story
from src.storyforge.runtime import AUDIT_SYSTEM, REPAIR_SYSTEM
from src.v3_single_attempt_guard import SafetyStop, SingleAttemptSpineGuard
from src.v3_unattended_story_quality import AUDIT_INSTRUCTIONS, AUDIT_MODEL, REPAIR_MODEL

SEQUENCE=(AUDIT_MODEL,REPAIR_MODEL,AUDIT_MODEL)


class CoherenceSequenceGuard(SingleAttemptSpineGuard):
    def event(self, kind, **safe_fields):
        if kind == "GUARD_INSTALLED":
            safe_fields["provider_post_limit"]=3
            safe_fields["permitted_models"]=list(SEQUENCE)
        return super().event(kind, **safe_fields)

    @contextmanager
    def installed_sequence(self):
        # The original single-post safety primitive dynamically consults
        # SPINE_MODELS; scope is restored on exit and no frozen file changes.
        with patch.object(guard_base,"SPINE_MODELS",SEQUENCE):
            with super().installed():
                yield self


class CoherenceModelCallbacks:
    def __init__(self, *, api_key: str, approved: dict, evidence_dir: Path | None = None):
        if not api_key:
            raise SafetyStop("OPENROUTER_API_KEY_REQUIRED")
        if (approved.get("human_review") or {}).get("verdict") != "APPROVE":
            raise SafetyStop("APPROVED_SPINE_REQUIRED")
        self.api_key=api_key
        self.approved=approved
        self.stage_index=0
        self.events=[]
        self.evidence_dir=evidence_dir

    def _model_call(self, *, stage: str, model: str, system: str,
                    payload: dict, max_tokens: int) -> dict:
        if self.stage_index >= len(SEQUENCE) or SEQUENCE[self.stage_index]!=model:
            raise SafetyStop("UNEXPECTED_MODEL_STAGE_SEQUENCE")
        # Charge intent is consumed BEFORE contacting provider. This
        # instance must be used within installed_sequence and externally
        # authorized by the call site.
        self.stage_index+=1
        parsed, body, _request, _parse_failures = english.call_structured_json_with_retry(
            api_key=self.api_key,model=model,system_prompt=system,
            user_prompt=json.dumps(payload,ensure_ascii=False),
            temperature=0.0,max_tokens=max_tokens,seed=2026101501+self.stage_index,
            request_class="editorial_audit",max_parse_attempts=1,
        )
        record = {
            "schema":"lumi.v3.quality.model-stage-evidence.v1",
            "stage":stage,"model":model,
            "call_number":self.stage_index,
            "generation_id":body.get("id"),
            "prompt_tokens":(body.get("usage") or {}).get("prompt_tokens"),
            "completion_tokens":(body.get("usage") or {}).get("completion_tokens"),
            "reported_cost_usd":(body.get("usage") or {}).get("cost"),
            "model_json":parsed,
        }
        if self.evidence_dir is not None:
            if not self.evidence_dir.is_dir():
                raise SafetyStop("MODEL_EVIDENCE_DIR_MISSING")
            path=self.evidence_dir / (f"model-{self.stage_index:02d}-{stage}.json")
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,"wb") as stream:
                stream.write((json.dumps(record,ensure_ascii=False,indent=2)+"\n").encode())
                stream.flush()
                os.fsync(stream.fileno())
        self.events.append({k:v for k,v in record.items() if k!="model_json"})
        return parsed

    def audit(self, *, story: str, authority_packet: dict,
              families: list, audit_policy: str) -> dict:
        if set(families) != {
            "physical_feasibility","causal_logic","state_continuity",
            "epistemic_order","spatial_consistency","temporal_consistency",
            "response_causality","closure_integrity","canon_integrity",
        }:
            raise SafetyStop("AUDIT_FAMILIES_INCOMPLETE")
        if audit_policy != AUDIT_INSTRUCTIONS:
            raise SafetyStop("AUDIT_POLICY_CHANGED")
        return self._model_call(
            stage="initial_coherence_audit" if self.stage_index==0
                  else "post_repair_coherence_reaudit",
            model=AUDIT_MODEL,system=AUDIT_SYSTEM+"\n"+AUDIT_INSTRUCTIONS,
            payload={
                "story_intent":self.approved["approved_premise"]["premise"],
                "authority_packet":authority_packet,
                "validated_spine":self.approved["episode_spine"],
                "story_segments":segment_story(story),
            },max_tokens=4200,
        )

    def repair(self, *, story: str, authority_packet: dict,
               confirmed_local_defects: list, policy: dict) -> dict:
        if self.stage_index != 1:
            raise SafetyStop("REPAIR_STAGE_UNEXPECTED")
        if not confirmed_local_defects or any(
            f.get("repair_scope")!="local" for f in confirmed_local_defects
        ):
            raise SafetyStop("REPAIR_REQUIRES_CONFIRMED_LOCAL_FINDINGS")
        return self._model_call(
            stage="bounded_model_repair",model=REPAIR_MODEL,
            system=REPAIR_SYSTEM,
            payload={
                "story_intent":self.approved["approved_premise"]["premise"],
                "authority_packet":authority_packet,
                "validated_spine":self.approved["episode_spine"],
                "story":story,
                "confirmed_local_defects":confirmed_local_defects,
                "repair_policy":{
                    "minimal_exact_replacements_only":True,
                    "do_not_rewrite_unaffected_prose":True,
                    "fix_only_confirmed_defects":True,
                    "do_not_change_branch_choice":True,
                    "length_is_nonblocking":True,
                },
            },max_tokens=2400,
        )
