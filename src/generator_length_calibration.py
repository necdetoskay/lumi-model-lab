from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

import src.generate as generation
from src.generator_benchmark_v2 import generation_phase, load_config


CALIBRATION_PROMPT_VERSION = "story_teacher_v0.3"
BENCHMARK_CONFIG = Path("configs/generator_length_calibration.yaml")
GENERATION_CONFIG = Path("configs/generation_benchmark_v2.yaml")


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    generation.PROMPT_VERSION = CALIBRATION_PROMPT_VERSION
    config = load_config(BENCHMARK_CONFIG)
    output_dir = Path(str(config["output_dir"]))
    manifest_path = output_dir / "manifest.json"
    generation_phase(config, GENERATION_CONFIG, manifest_path, force=False)


if __name__ == "__main__":
    main()
