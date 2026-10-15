"""Isolated Aion Mini Writer guard; never edits the frozen V3 Writer runtime.

Reuses the tested Spine guard's one-use model-post accounting and
fail-closed retry disabling. The model allowlist has exactly ONE Aion call.
"""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from src import v3_single_attempt_guard as base
from src.v3_single_attempt_guard import SingleAttemptSpineGuard, SafetyStop, _safe_cost

WRITER_MODEL = "aion-labs/aion-3.5-mini"


class SingleAttemptAionWriterGuard(SingleAttemptSpineGuard):
    def _observed_writer_call(self, **kwargs):
        output = self._original_writer_call(**kwargs)
        _, body, _ = output
        if not isinstance(body, dict):
            self.event("PROVIDER_FAULT", reason="INVALID_COMPLETION_BODY")
            raise SafetyStop("INVALID_COMPLETION_BODY")
        try:
            cost = _safe_cost(body)
        except SafetyStop:
            self.event("PROVIDER_FAULT", reason="PROVIDER_COST_MISSING_OR_INVALID")
            raise
        generation_id = body.get("id")
        if (
            not isinstance(generation_id, str)
            or not generation_id.startswith("gen-")
            or len(generation_id) > 140
        ):
            self.event("PROVIDER_FAULT", reason="GENERATION_ID_MISSING_OR_INVALID")
            raise SafetyStop("GENERATION_ID_MISSING_OR_INVALID")
        usage = body.get("usage") or {}
        self.event(
            "PROVIDER_OBSERVED",
            call_number=self.calls,
            model=kwargs.get("model"),
            generation_id=generation_id,
            reported_cost_usd=str(cost),
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )
        self.spent += cost
        if self.spent > self.max_cost:
            self.event(
                "POLICY_STOP", reason="CUMULATIVE_COST_CEILING_REACHED",
                observed_cost_usd=str(self.spent),
            )
            raise SafetyStop("CUMULATIVE_COST_CEILING_REACHED")
        return output

    @contextmanager
    def installed_writer(self):
        from src import episode_writer_v2_generate as writer
        self._original_writer_call = writer.call_openrouter
        # Only the guard's external allowlist is changed, for this specific
        # isolated runtime context; original V3 models and prompts are unchanged.
        with patch.object(base, "SPINE_MODELS", (WRITER_MODEL,)):
            with super().installed():
                with patch.object(writer, "call_openrouter", self._observed_writer_call):
                    yield self
