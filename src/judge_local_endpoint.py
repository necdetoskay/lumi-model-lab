from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console

from src.judge import call_judge, load_yaml, make_decision
from src.schemas import JUDGE_CRITERIA

console = Console()


def load_local_story(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"Local story file must contain a JSON object: {path}")
    story = data.get("story")
    spec_path = data.get("spec_path")
    if not isinstance(story, str) or not story.strip():
        raise RuntimeError(f"Local story file has no story text: {path}")
    if not isinstance(spec_path, str) or not spec_path.strip():
        raise RuntimeError(f"Local story file has no spec_path: {path}")
    return data


def build_local_judge_input(local_record: dict[str, Any], spec: dict[str, Any]) -> str:
    constraints = spec.get("constraints") or []
    constraint_text = "\n".join(f"- {item}" for item in constraints) or "- None"
    technical = local_record.get("technical") or {}
    return f"""Evaluate this candidate story against the brief.

BRIEF
Language: {spec.get('language', 'tr')}
Age range: {spec.get('age_min')}-{spec.get('age_max')}
Target words: {spec.get('target_words', 2000)}
Title hint: {spec.get('title_hint') or 'None'}
Protagonist: {spec.get('protagonist', '')}
Setting: {spec.get('setting', '')}
Theme: {spec.get('theme', '')}
Premise: {spec.get('premise', '')}
Constraints:
{constraint_text}

TECHNICAL CONTEXT
Word count: {technical.get('word_count')}
Technical length pass: {technical.get('pass')}

CANDIDATE STORY
{local_record['story']}
"""


def judge_local_story(input_path: Path, config_path: Path) -> tuple[Path, dict[str, Any]]:
    config = load_yaml(config_path)
    judge_config = config.get("judge") or {}
    local_record = load_local_story(input_path)
    spec = load_yaml(Path(str(local_record["spec_path"])))

    model_env = str(judge_config.get("model_env", "JUDGE_MODEL"))
    model = os.getenv(model_env)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not model:
        raise RuntimeError(f"Missing judge model in environment variable {model_env}.")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    system_prompt = Path("prompts/story_judge.md").read_text(encoding="utf-8").strip()
    result, body = call_judge(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=build_local_judge_input(local_record, spec),
        temperature=float(judge_config.get("temperature", 0.0)),
        max_tokens=int(judge_config.get("max_tokens", 3000)),
    )
    decision = make_decision(
        result,
        acceptance_threshold=float(judge_config.get("acceptance_threshold", 4.0)),
        minimum_criterion_score=int(judge_config.get("minimum_criterion_score", 3)),
    )

    choice = (body.get("choices") or [{}])[0]
    output = {
        "source_path": str(input_path),
        "source_model": local_record.get("model"),
        "spec_path": local_record.get("spec_path"),
        "title_hint": local_record.get("title_hint"),
        "technical": local_record.get("technical"),
        "judge_model": model,
        "scores": result.scores,
        "reasons": result.reasons,
        "critical_failures": result.critical_failures,
        "decision": decision.model_dump(mode="json"),
        "usage": body.get("usage") or {},
        "response_meta": {
            "openrouter_id": body.get("id"),
            "model": body.get("model"),
            "provider": body.get("provider"),
            "finish_reason": choice.get("finish_reason"),
        },
    }

    output_dir = Path(judge_config.get("output_dir", "runs/judgments")) / "local_endpoint"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}.judge.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path, output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge a LUMI local-endpoint baseline story.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--config", default="configs/evaluation.yaml")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    output_path, output = judge_local_story(Path(args.input), Path(args.config))
    decision = output["decision"]
    style = "green" if decision["accepted"] else "yellow"
    console.print(f"[{style}]Judged[/{style}] {args.input} -> {output_path}")
    console.print(
        f"Decision: [{style}]{'ACCEPTED' if decision['accepted'] else 'REJECTED'}[/{style}] | "
        f"average={decision['average_score']:.2f}/5 | minimum={decision['minimum_score']}/5"
    )
    for criterion in JUDGE_CRITERIA:
        console.print(f"  {criterion}: {output['scores'][criterion]}/5")
    if output["critical_failures"]:
        console.print(f"Critical failures: {output['critical_failures']}")


if __name__ == "__main__":
    main()
