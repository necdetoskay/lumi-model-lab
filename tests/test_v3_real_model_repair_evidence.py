"""Replay real Luna/Sol evidence, only the future re-audit is mocked.

No assistant-written fiction or provider requests are used by these tests.
"""
import hashlib
import json
from pathlib import Path

import pytest

from src.generate import count_words
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.storyforge.runtime import _apply_local_repairs, _normalize_audit
from src.v3_unattended_story_quality import (
    QualityStop, _model_patch_is_within_reported_quote, qualify,
)

ROOT=Path("evidence/v3-f2-aion-writer-38703469212")
RUN=Path("evidence/v3-f2-autonomous-quality-38709109136")
APPROVED=Path(
    "data/specifications/story_lab/"
    "age18_forbidden_cartographer_f2_approved_for_aion_20261015.json"
)
LUNA_SHA="7d2a67f89372fe1c65868b8f3dd64dea946685c161536e0af2cc45af958ac189"
SOL_SHA="3865c48f43929da6f10b577a72a00d2d81cc0d7a4bee3219c74b3e775946d0b3"


def real():
    story=(ROOT/"story-en.txt").read_text()
    writer=json.loads((ROOT/"writer-result.json").read_text())
    approved=json.loads(APPROVED.read_text())
    luna=json.loads((RUN/"model-01-initial_coherence_audit.json").read_text())
    sol=json.loads((RUN/"model-02-bounded_model_repair.json").read_text())
    return story,writer,approved,luna,sol


def test_real_model_evidence_is_unchanged_and_verified():
    story,writer,approved,luna,sol=real()
    assert hashlib.sha256(
        (RUN/"model-01-initial_coherence_audit.json").read_bytes()
    ).hexdigest()==LUNA_SHA
    assert hashlib.sha256(
        (RUN/"model-02-bounded_model_repair.json").read_bytes()
    ).hexdigest()==SOL_SHA
    assert luna["model"]=="openai/gpt-5.6-luna"
    assert sol["model"]=="openai/gpt-5.6-sol"
    assert luna["call_number"]==1 and sol["call_number"]==2
    assert len([x for x in luna["model_json"]["evaluations"] if x["present"]])==1
    assert writer["status"]=="writer_generated_deterministic_check_failed"
    assert count_words(story)==2767


def test_real_sol_exact_model_proposal_is_scoped_and_applies_mechanically():
    story,writer,approved,luna,sol=real()
    findings=_normalize_audit(luna["model_json"],segment_story(story))
    assert len(findings)==1
    proposal=sol["model_json"]
    assert len(proposal["repairs"])==1
    row=proposal["repairs"][0]
    assert _model_patch_is_within_reported_quote(
        story=story,row=row,findings=findings,segments=segment_story(story)
    )
    repaired,applied=_apply_local_repairs(story,proposal)
    assert applied==proposal["repairs"]
    assert repaired==story.replace(row["old"],row["new"],1)
    assert repaired!=story
    assert count_words(repaired)==2767
    assert (ROOT/"story-en.txt").read_text()==story


@pytest.mark.parametrize("mutation",[
    lambda row: row.update({"new":row["new"].replace("never moved","moved")}),
    lambda row: row.update({"new":"Made-up witness said "+row["new"]}),
    lambda row: row.update({"old":"Three timed readings."}),
])
def test_unapproved_extra_text_or_wrong_old_span_rejected(mutation):
    story,writer,approved,luna,sol=real()
    findings=_normalize_audit(luna["model_json"],segment_story(story))
    original=sol["model_json"]["repairs"][0]
    proposal=dict(original)
    mutation(proposal)
    if proposal["old"]=="Three timed readings.":
        # This narrow edit is safe if it changes ONLY the model-reported
        # quote. Ensure a malicious additional edit is rejected instead.
        proposal["new"]="Four timed readings. A control stone was moved."
    assert not _model_patch_is_within_reported_quote(
        story=story,row=proposal,findings=findings,segments=segment_story(story)
    )


def test_archived_luna_and_sol_can_replay_until_mocked_final_recheck():
    story,writer,approved,luna,sol=real()
    calls=[]
    def audit(**kwargs):
        calls.append("Luna")
        if len(calls)==1:
            return luna["model_json"]
        # Only this third model reply is synthetic; this MUST NOT be
        # described as real successful production acceptance.
        return {"evaluations":[{
            "family":family,"present":False,"severity":None,
            "repair_scope":None,"span_ids":[],"exact_quote":None,
            "reason":"OFFLINE_SIMULATION_ONLY",
        } for family in DEFECT_FAMILIES]}
    def repair(**kwargs):
        calls.append("Sol")
        assert len(kwargs["confirmed_local_defects"])==1
        return sol["model_json"]
    out=qualify(story=story,writer_result=writer,approved=approved,
                audit=audit,repair=repair)
    assert calls==["Luna","Sol","Luna"]
    assert out["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert out["length_warning"] is True
    assert out["length_blocking"] is False
    assert out["source_story_sha256"]!=out["accepted_story_sha256"]
    assert len(out["model_generated_repairs"])==1


def test_live_first_attempt_stopped_and_no_final_model_was_charged():
    events=[json.loads(p.read_text()) for p in sorted(RUN.glob("[0-9][0-9][0-9]-*.json"))]
    observed=[e for e in events if e["kind"]=="PROVIDER_OBSERVED"]
    assert len(observed)==2
    assert [x["model"] for x in observed]==[
        "openai/gpt-5.6-luna","openai/gpt-5.6-sol",
    ]
    assert [x["reported_cost_usd"] for x in observed]==["0.0086508","0.075847"]
    assert any(e["kind"]=="STAGE_STOP" and e["model_posts"]==2 for e in events)
    assert not any(e["kind"]=="STAGE_FINISHED" for e in events)
    assert not any(RUN.glob("model-03-*.json"))
