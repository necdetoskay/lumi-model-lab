from __future__ import annotations

import base64
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

from src.visual_contracts import (
    CompiledPromptPackage,
    VisualModelProfile,
    VisualProviderImage,
    VisualProviderResult,
)


class VisualProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class VisualProviderAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        *,
        model: VisualModelProfile,
        compiled: CompiledPromptPackage,
    ) -> VisualProviderResult:
        raise NotImplementedError


class FixtureVisualProviderAdapter(VisualProviderAdapter):
    def __init__(self, *, image_bytes: bytes = b"LUMI_VISUAL_FIXTURE") -> None:
        self.image_bytes = image_bytes

    def generate(
        self,
        *,
        model: VisualModelProfile,
        compiled: CompiledPromptPackage,
    ) -> VisualProviderResult:
        return VisualProviderResult(
            images=[
                VisualProviderImage(
                    b64_json=base64.b64encode(self.image_bytes).decode("ascii"),
                    media_type="image/png",
                )
            ],
            usage={"cost": 0.0},
            response_id="fixture-image-response",
            resolved_model=model.model_id,
            provider="fixture",
            response_meta={"fixture": True},
        )


class OpenRouterImageAdapter(VisualProviderAdapter):
    def __init__(self, *, api_key: str) -> None:
        if not api_key:
            raise ValueError("OpenRouter image adapter requires api_key")
        self.api_key = api_key

    def _payload(
        self,
        *,
        model: VisualModelProfile,
        compiled: CompiledPromptPackage,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model.model_id,
            "prompt": compiled.positive_prompt,
        }
        supported = set(model.capabilities.aspect_ratios)
        aspect_ratio = compiled.provider_options.get("aspect_ratio")
        if aspect_ratio and (not supported or aspect_ratio in supported):
            payload["aspect_ratio"] = aspect_ratio
        n = int(compiled.provider_options.get("n") or 1)
        if n > model.capabilities.max_images_per_call:
            raise ValueError(
                f"{model.model_id} supports at most {model.capabilities.max_images_per_call} images/call"
            )
        if n != 1:
            payload["n"] = n
        if compiled.input_references:
            if not model.capabilities.reference_images:
                raise ValueError(f"{model.model_id} does not support reference images")
            if len(compiled.input_references) > model.capabilities.max_reference_images:
                raise ValueError(
                    f"{model.model_id} supports at most {model.capabilities.max_reference_images} references"
                )
            payload["input_references"] = [
                {"type": "image_url", "image_url": {"url": ref}}
                for ref in compiled.input_references
            ]
        if (
            compiled.negative_prompt
            and model.prompt_policy.supports_separate_negative_prompt
            and model.prompt_policy.negative_prompt_parameter
        ):
            payload[model.prompt_policy.negative_prompt_parameter] = compiled.negative_prompt
        return payload

    def generate(
        self,
        *,
        model: VisualModelProfile,
        compiled: CompiledPromptPackage,
    ) -> VisualProviderResult:
        payload = self._payload(model=model, compiled=compiled)
        attempts = 0
        while True:
            try:
                response = requests.post(
                    model.endpoint,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
                        "X-Title": "LUMI Model Lab Visual",
                    },
                    json=payload,
                    timeout=model.runtime_policy.timeout_seconds,
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempts >= model.runtime_policy.max_retries:
                    raise VisualProviderError(f"OpenRouter image transport error: {exc}") from exc
                attempts += 1
                time.sleep(min(2**attempts, 8))
                continue

            if response.ok:
                break
            status = response.status_code
            if (
                status in model.runtime_policy.transient_status_codes
                and attempts < model.runtime_policy.max_retries
            ):
                attempts += 1
                time.sleep(min(2**attempts, 8))
                continue
            raise VisualProviderError(
                f"OpenRouter image HTTP {status}: {response.text[:2000]}",
                status_code=status,
            )

        body = response.json()
        raw_images = body.get("data") or []
        images = [
            VisualProviderImage(
                b64_json=str(item.get("b64_json") or ""),
                media_type=str(item.get("media_type") or "image/png"),
            )
            for item in raw_images
            if item.get("b64_json")
        ]
        if not images:
            raise VisualProviderError("OpenRouter image response contained no image data")
        return VisualProviderResult(
            images=images,
            usage=body.get("usage") or {},
            response_id=body.get("id"),
            resolved_model=body.get("model") or model.model_id,
            provider=body.get("provider") or "openrouter",
            response_meta={
                "attempts": attempts + 1,
                "media_types": [item.media_type for item in images],
            },
        )
