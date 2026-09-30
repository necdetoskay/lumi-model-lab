from __future__ import annotations

import json
from pathlib import Path

FINAL=Path("data/specifications/story_lab/age18_cross_age_final_delivery_v1.json")
C61=Path("data/specifications/story_lab/age18_cross_age_c61_fidelity_recovery_evidence.json")


def test_age18_final_delivery_is_publication_ready() -> None:
    final=json.loads(FINAL.read_text())
    assert final["status"]=="publication_ready"
    assert final["publication_ready"] is True
    assert final["exact_age"]==18
    assert final["english_word_count"]==2176
    assert final["api_calls"]==6
    assert final["product_path_cost_usd"]==0.17766185
    assert final["product_path_tokens"]==84747
    assert final["product_path_latency_seconds"]==426.802


def test_age18_final_turkish_restores_title_modality_and_recurrence() -> None:
    final=json.loads(FINAL.read_text())
    tr=final["turkish_delivery"]
    assert "# Kapatılması Gerekebilecek Rota" in tr
    assert "# Kapatılması Gereken Rota" not in tr
    assert "tekrarlanabilirlik bilinmiyor" not in tr
    assert "sapmanın tekrarlanıp tekrarlanmayacağı bilinmiyor" in tr
    assert "sapmanın tekrarlanıp tekrarlanmayacağını veya seyir riskini belirlemek" in tr


def test_c61_is_zero_cost_deterministic_recovery() -> None:
    c61=json.loads(C61.read_text())
    assert c61["status"]=="GREEN"
    assert c61["model_calls"]==0
    assert c61["incremental_cost_usd"]==0.0
    assert c61["decision"]["fidelity_blockers_remaining"]==0
    assert c61["decision"]["publication_ready"] is True
