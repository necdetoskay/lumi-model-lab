from __future__ import annotations

import unittest

from src.model_registry import (
    normalize_openrouter_request,
    require_qualification_runtime_profile,
    resolve_model_request_behavior,
    resolve_model_runtime_profile,
    runtime_profile_identity,
)


class ModelRuntimeProfileTests(unittest.TestCase):
    def test_aion_mini_large_structured_request_matches_production_contract(self) -> None:
        payload = normalize_openrouter_request(
            "aion-labs/aion-3.0-mini",
            {
                "model": "aion-labs/aion-3.0-mini",
                "temperature": 0.8,
                "max_tokens": 16000,
                "seed": 17,
                "reasoning": {"enabled": False, "effort": "none"},
            },
            request_class="structured_large",
            structured_output=True,
        )

        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("reasoning", payload)
        self.assertNotIn("seed", payload)
        self.assertEqual(payload["temperature"], 0.8)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_aion_mini_small_structured_request_caps_tokens(self) -> None:
        payload = normalize_openrouter_request(
            "aion-labs/aion-3.0-mini",
            {"max_tokens": 5000},
            request_class="structured_small",
            structured_output=True,
        )
        self.assertEqual(payload["max_tokens"], 1200)
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_luna_omits_temperature_and_pins_provider_routing(self) -> None:
        payload = normalize_openrouter_request(
            "openai/gpt-5.6-luna",
            {
                "temperature": 0.7,
                "max_tokens": 4000,
                "seed": 42,
            },
        )
        self.assertNotIn("temperature", payload)
        self.assertEqual(payload["max_tokens"], 4000)
        self.assertEqual(
            payload["provider"],
            {
                "order": ["openai"],
                "allow_fallbacks": False,
                "require_parameters": True,
                "sort": "latency",
            },
        )

    def test_glm_flash_preserves_lab_verified_reasoning_and_budget(self) -> None:
        payload = normalize_openrouter_request(
            "z-ai/glm-5.3-flash",
            {"max_tokens": 7000, "seed": 42},
            request_class="teacher_story",
        )
        self.assertEqual(payload["max_tokens"], 10000)
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(
            payload["reasoning"],
            {"enabled": True, "effort": "low", "exclude": True},
        )

    def test_qwen38_flash_uses_verified_teacher_story_contract(self) -> None:
        profile = require_qualification_runtime_profile("qwen/qwen3.8-flash")
        payload = normalize_openrouter_request(
            "qwen/qwen3.8-flash",
            {"temperature": 0.8, "max_tokens": 7000, "seed": 42},
            request_class="teacher_story",
        )
        self.assertEqual(profile["match"]["type"], "exact")
        self.assertEqual(profile["metadata"]["max_output_tokens"], 131072)
        self.assertEqual(profile["metadata"]["reasoning"]["default_effort"], "xhigh")
        self.assertEqual(payload["max_tokens"], 7000)
        self.assertEqual(payload["temperature"], 0.8)
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["reasoning"], {"effort": "none", "exclude": True})
        self.assertNotIn("reasoning_effort", payload)
        self.assertNotIn("provider", payload)
        self.assertIs(payload["stream"], True)

    def test_qwen38_story_plan_has_separate_output_budget(self) -> None:
        payload = normalize_openrouter_request(
            "qwen/qwen3.8-flash",
            {"temperature": 0.2, "max_tokens": 5000, "seed": 42},
            request_class="story_plan",
            structured_output=True,
        )
        self.assertEqual(payload["max_tokens"], 5000)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["seed"], 42)
        self.assertEqual(payload["reasoning"], {"effort": "none", "exclude": True})
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("stream", payload)

    def test_qwen38_default_request_keeps_provider_defaults(self) -> None:
        payload = normalize_openrouter_request(
            "qwen/qwen3.8-flash",
            {"temperature": 0.8, "max_tokens": 7000, "seed": 42},
            request_class="default",
        )
        self.assertNotIn("temperature", payload)
        self.assertNotIn("max_tokens", payload)
        self.assertNotIn("seed", payload)
        self.assertNotIn("reasoning", payload)
        self.assertNotIn("stream", payload)

    def test_paid_qualification_profile_gate_rejects_fallback_and_family(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "MODEL_RUNTIME_PROFILE_MISSING"):
            require_qualification_runtime_profile("vendor/new-model")
        with self.assertRaisesRegex(RuntimeError, "MODEL_RUNTIME_PROFILE_MISSING"):
            require_qualification_runtime_profile("minimax/minimax-m2.5-fast")
        with self.assertRaisesRegex(RuntimeError, "MODEL_RUNTIME_PROFILE_MISSING"):
            require_qualification_runtime_profile("qwen/qwen3.6-flash")

    def test_family_prefix_profile_is_resolved(self) -> None:
        profile = resolve_model_runtime_profile("minimax/minimax-m2.5-fast")
        behavior = resolve_model_request_behavior("minimax/minimax-m2.5-fast")
        self.assertEqual(profile["match"]["type"], "prefix")
        self.assertEqual(profile["match"]["value"], "minimax/minimax-m2.5")
        self.assertEqual(
            behavior["reasoning"]["mode"],
            "provider_managed_required",
        )

    def test_unknown_model_uses_explicit_generic_profile(self) -> None:
        profile = resolve_model_runtime_profile("vendor/new-model")
        identity = runtime_profile_identity("vendor/new-model")
        self.assertEqual(profile["match"]["type"], "fallback")
        self.assertEqual(profile["transport"]["reasoning"]["mode"], "provider_default")
        self.assertEqual(len(identity["profile_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
