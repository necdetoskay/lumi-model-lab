from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load_story(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def repeated_ngrams(words: list[str], n: int = 8) -> tuple[int, int, list[tuple[str, int]]]:
    if len(words) < n:
        return 0, 0, []
    grams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
    counts = Counter(grams)
    repeated = [(" ".join(gram), count) for gram, count in counts.items() if count > 1]
    repeated.sort(key=lambda item: (-item[1], item[0]))
    repeated_instances = sum(count - 1 for _, count in repeated)
    return len(grams), repeated_instances, repeated[:10]


def inspect(path: Path, tail_chars: int) -> None:
    item = load_story(path)
    story = str(item.get("story") or "")
    words = story.split()
    total_grams, repeated_instances, top = repeated_ngrams(words, 8)
    ratio = (repeated_instances / total_grams) if total_grams else 0.0

    print("LUMI generation diagnostic")
    print(f"path               = {path}")
    print(f"words              = {len(words)}")
    print(f"output_tokens      = {item.get('output_tokens')}")
    print(f"max_new_tokens     = {item.get('max_new_tokens')}")
    print(f"ended_with_eos     = {item.get('ended_with_eos')}")
    print(f"last_token_id      = {item.get('last_token_id')}")
    print(f"8gram_repeat_ratio = {ratio:.4f}")
    print("top repeated 8-grams:")
    if top:
        for text, count in top:
            print(f"  x{count}: {text}")
    else:
        print("  none")
    print("\n--- STORY TAIL ---")
    print(story[-tail_chars:])
    print("--- END TAIL ---")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a generated local baseline story for repetition and termination behavior.")
    parser.add_argument(
        "path",
        nargs="?",
        default="runs/model_baseline/pre_finetune_qwen35_4b_4060_nonthinking_v3/story_01.json",
    )
    parser.add_argument("--tail-chars", type=int, default=3000)
    args = parser.parse_args()
    inspect(Path(args.path), args.tail_chars)


if __name__ == "__main__":
    main()
