from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from story_v5_tr_lint_copyedit_benchmark_20260925 import semantic_defect_locator

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "experiments/fixtures/story_defect_locator_regression.tr-age4.v0.1.json"
OUT = ROOT / "runs/story_defect_locator_regression/result.json"


def norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def quote_match(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    return bool(a and b and (a in b or b in a))


def main() -> None:
    api_key = os.environ["OPENROUTER_API_KEY"]
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases_out: list[dict[str, Any]] = []
    tp = fp = fn = known_negative_hits = 0
    by_kind: dict[str, dict[str, int]] = {}

    for idx, case in enumerate(corpus["cases"]):
        run_id = case["run_id"]
        story_path = ROOT / f"experiments/fixtures/story_defect_locator_stories/{run_id}.txt"
        story = story_path.read_text(encoding="utf-8")
        predicted, meta = semantic_defect_locator(api_key=api_key, story=story, seed=202609250 + idx)
        gold = case.get("gold_findings") or []
        negatives = case.get("known_non_defects") or []
        matched_pred: set[int] = set()
        matched_gold: set[int] = set()

        for gi, g in enumerate(gold):
            k = g["kind"]
            by_kind.setdefault(k, {"gold": 0, "tp": 0})
            by_kind[k]["gold"] += 1
            for pi, p in enumerate(predicted):
                if pi in matched_pred:
                    continue
                if p["kind"] == k and quote_match(p["source_quote"], g["quote"]):
                    matched_gold.add(gi); matched_pred.add(pi)
                    by_kind[k]["tp"] += 1
                    break

        case_tp = len(matched_gold)
        case_fn = len(gold) - case_tp
        case_fp = len(predicted) - len(matched_pred)
        negative_hits = [n for n in negatives if any(quote_match(p["source_quote"], n) for p in predicted)]
        tp += case_tp; fn += case_fn; fp += case_fp; known_negative_hits += len(negative_hits)
        cases_out.append({
            "run_id": run_id,
            "case": case["case"],
            "gold": gold,
            "predicted": predicted,
            "tp": case_tp,
            "fp": case_fp,
            "fn": case_fn,
            "known_negative_hits": negative_hits,
            "locator_meta": meta,
        })

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    result = {
        "schema_version": "story-defect-locator-regression-result.v0.1",
        "corpus": str(CORPUS.relative_to(ROOT)),
        "summary": {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "known_negative_hits": known_negative_hits,
            "per_kind_recall": {
                k: round(v["tp"] / v["gold"], 4) if v["gold"] else 0.0
                for k, v in sorted(by_kind.items())
            },
        },
        "cases": cases_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
