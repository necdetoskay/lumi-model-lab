"""Fully orchestrated frozen V3 author/Gate/repair bridge; no real network."""
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.v3_unattended_story_quality import qualify
from src.v3_unattended_quality_model_adapter import (
    CoherenceModelCallbacks, CoherenceSequenceGuard, SEQUENCE,
)

ROOT=Path("evidence/v3-f2-aion-writer-38703469212")
SPINE=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")


def _audit_response(story, *, flag):
    span=next((s for s in segment_story(story)
               if "Three timed readings." in s["text"]),None)
    rows=[]
    for family in DEFECT_FAMILIES:
        present=family=="state_continuity" and flag
        rows.append({
            "family":family, "present":present,
            "severity":"serious" if present else None,
            "repair_scope":"local" if present else None,
            "span_ids":[span["id"]] if present else [],
            "exact_quote":"Three timed readings." if present else None,
            "reason":"Total measurement count contradicts the four narrated readings"
                     if present else "clear",
        })
    return {"evaluations":rows}


class FakeResponse:
    ok=True
    status_code=200
    headers={}
    def __init__(self, n, content):
        self.n=n
        self.content=content
    def json(self):
        return {
            "id":"gen-offline-fully-automated-"+str(self.n),
            "choices":[{"message":{"content":json.dumps(self.content)},
                        "finish_reason":"stop"}],
            "usage":{"prompt_tokens":2300,"completion_tokens":1000,
                     "total_tokens":3300,"cost":0.012},
        }


def test_real_writer_output_is_model_repaired_with_zero_manual_story_edit(tmp_path):
    original=(ROOT/"story-en.txt").read_text()
    writer=json.loads((ROOT/"writer-result.json").read_text())
    approved=json.loads(SPINE.read_text())
    incoming=[
        _audit_response(original,flag=True),
        {"repairs":[{"old":"Three timed readings.",
                     "new":"Four timed readings.",
                     "why":"Four observations were narrated in prior scenes."}]},
        _audit_response(original.replace("Three timed readings.","Four timed readings."),
                        flag=False),
    ]
    models=[]
    def fake_post(url,**kwargs):
        n=len(models)
        models.append(kwargs["json"]["model"])
        return FakeResponse(n+1,incoming[n])
    evidence=tmp_path/"evidence"
    evidence.mkdir()
    guard=CoherenceSequenceGuard(evidence,Decimal("0.08"))
    adapter=CoherenceModelCallbacks(api_key="MOCK_NO_PROVIDER",approved=approved)
    with patch("requests.post",side_effect=fake_post):
        with guard.installed_sequence():
            result=qualify(
                story=original,writer_result=writer,approved=approved,
                audit=adapter.audit,repair=adapter.repair,
            )
    assert models==list(SEQUENCE)
    assert guard.calls==3
    assert guard.spent==Decimal("0.036")
    assert result["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert result["word_count"]==2767
    assert result["length_warning"] is True
    assert result["length_blocking"] is False
    assert len(result["model_generated_repairs"])==1
    assert (ROOT/"story-en.txt").read_text()==original
    assert result["translation_authorized"] is False
    assert result["world_state_commit_authorized"] is False
    events=[json.loads(f.read_text()) for f in evidence.glob("[0-9][0-9][0-9]-*.json")]
    assert len([e for e in events if e["kind"]=="POST_INTENT"])==3
    assert len([e for e in events if e["kind"]=="PROVIDER_OBSERVED"])==3
    assert [x["stage"] for x in adapter.events]==[
        "initial_coherence_audit","bounded_model_repair",
        "post_repair_coherence_reaudit",
    ]
    assert any(x["kind"]=="GUARD_INSTALLED" and x["provider_post_limit"]==3 for x in events)


def test_clean_semantic_result_does_not_call_sol(tmp_path):
    original=(ROOT/"story-en.txt").read_text()
    writer=json.loads((ROOT/"writer-result.json").read_text())
    approved=json.loads(SPINE.read_text())
    called=[]
    def fake_post(url,**kwargs):
        called.append(kwargs["json"]["model"])
        return FakeResponse(1,_audit_response(original,flag=False))
    evidence=tmp_path/"evidence";evidence.mkdir()
    guard=CoherenceSequenceGuard(evidence,Decimal("0.08"))
    adapter=CoherenceModelCallbacks(api_key="OFFLINE_ONLY",approved=approved)
    with patch("requests.post",side_effect=fake_post):
        with guard.installed_sequence():
            out=qualify(story=original,writer_result=writer,approved=approved,
                        audit=adapter.audit,repair=adapter.repair)
    assert called==["openai/gpt-5.6-luna"]
    assert out["model_generated_repairs"]==[]
    assert out["length_warning"] is True
