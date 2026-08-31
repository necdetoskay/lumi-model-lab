from src.generator_benchmark_v2 import repeated_ngram_ratio, summarize


def test_repeated_ngram_ratio_detects_repeated_passages() -> None:
    unique = "bir iki üç dört beş altı yedi sekiz dokuz on onbir oniki"
    repeated = "bir iki üç dört beş altı yedi sekiz bir iki üç dört beş altı yedi sekiz"

    assert repeated_ngram_ratio(unique) == 0.0
    assert repeated_ngram_ratio(repeated) > 0.0


def test_summary_counts_failures_and_cost_per_accepted_story() -> None:
    model = "example/model"
    entries = [
        {
            "model": model,
            "generation_status": "complete",
            "technical_pass": True,
            "judge_status": "complete",
            "judge_accepted": True,
            "judge_average": 4.5,
            "judge_scores": {
                "instruction_following": 5,
                "coherence": 5,
                "character_consistency": 4,
                "age_appropriateness": 5,
                "creativity": 4,
                "style_quality": 4,
            },
            "generator_cost_usd": 0.01,
            "judge_cost_usd": 0.005,
            "generator_cost_try": 0.48,
            "judge_cost_try": 0.24,
            "generation_latency_seconds": 2.0,
            "repeat_8gram_ratio": 0.0,
        },
        {
            "model": model,
            "generation_status": "error",
            "technical_pass": False,
        },
    ]

    item = summarize(entries, [model])[model]

    assert item["planned"] == 2
    assert item["generated"] == 1
    assert item["generation_errors"] == 1
    assert item["technical_pass_rate"] == 0.5
    assert item["accepted"] == 1
    assert item["combined_cost_total_usd"] == 0.015
    assert item["cost_per_accepted_story_usd"] == 0.015
    assert item["cost_per_accepted_story_try"] == 0.72
