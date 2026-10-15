"""Models (mocked only here), never humans, author narrative edits."""
import json
from pathlib import Path
import pytest
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.v3_unattended_story_quality import qualify, QualityStop, _safe_hard
from src.story_authority_packet_v2 import build_story_authority_packet_v2

ROOT=Path("evidence/v3-f2-aion-writer-38703469212")
APPROVED=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")
ORIGINAL=ROOT/"story-en.txt"


def source():
    return ORIGINAL.read_text(), json.loads((ROOT/"writer-result.json").read_text()), json.loads(APPROVED.read_text())


def all_family_findings(story, with_mismatch=False):
    seg=next(s for s in segment_story(story) if "Three timed readings." in s["text"]) if with_mismatch else None
    rows=[]
    for family in DEFECT_FAMILIES:
        flagged=with_mismatch and family=="state_continuity"
        rows.append({
            "family":family,
            "present":bool(flagged),
            "severity":"serious" if flagged else None,
            "repair_scope":"local" if flagged else None,
            "span_ids":[seg["id"]] if flagged else [],
            "exact_quote":"Three timed readings." if flagged else None,
            "reason":"Inconsistent with the four events in the previous scenes" if flagged else "none",
        })
    return {"evaluations":rows}


def test_mocked_model_audit_repairs_actual_original_via_pipeline_without_human_edit():
    text,writer,approved=source()
    calls=[]
    def audit(**kw):
        calls.append("Luna")
        assert kw["audit_policy"].find("numerical")>=0
        return all_family_findings(kw["story"], "Three timed readings." in kw["story"])
    def sol(**kw):
        calls.append("Sol")
        assert kw["confirmed_local_defects"][0]["exact_quote"]=="Three timed readings."
        return {"repairs":[{
            "old":"Three timed readings.",
            "new":"Four timed readings.",
            "why":"The preceding narrative logs four Gate readings.",
        }]}
    result=qualify(story=text,writer_result=writer,approved=approved,
                   audit=audit,repair=sol)
    assert calls==["Luna","Sol","Luna"]
    assert result["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert result["length_warning"] is True
    assert result["length_blocking"] is False
    assert result["word_count"]==2767
    assert result["confirmed_findings"]==1
    assert result["false_positive_negations"]==2
    assert len(result["model_generated_repairs"])==1
    assert "Four timed readings." in result["accepted_english_story"]
    assert "Three timed readings." in ORIGINAL.read_text()
    assert result["source_story_sha256"]!=result["accepted_story_sha256"]
    assert result["world_state_commit_authorized"] is False


def test_coherent_out_of_range_story_is_not_rejected_for_length():
    text,writer,approved=source()
    calls=[]
    def no_findings(**kwargs):
        calls.append("Luna")
        return all_family_findings(kwargs["story"],False)
    def no_repair(**kwargs):
        raise AssertionError("REPAIR_MUST_NOT_RUN_ON_CLEAN_STORY")
    result=qualify(story=text,writer_result=writer,approved=approved,
                   audit=no_findings,repair=no_repair)
    assert calls==["Luna"]
    assert result["status"]=="AUTOMATED_ENGLISH_COHERENCE_ACCEPTED"
    assert result["length_warning"]
    assert result["model_generated_repairs"]==[]


def test_unfixed_inconsistency_stops_after_single_bounded_repair():
    text,writer,approved=source()
    seen=[]
    def audit(**kw):
        seen.append("Luna")
        if len(seen)==1:
            return all_family_findings(kw["story"],True)
        # Negative test: the re-auditor flags another extant exact phrase.
        rows=all_family_findings(kw["story"],False)
        quote="A control stone that never moved."
        segment=next(x for x in segment_story(kw["story"]) if quote in x["text"])
        item=next(x for x in rows["evaluations"] if x["family"]=="state_continuity")
        item.update({"present":True,"severity":"serious","repair_scope":"local",
                     "span_ids":[segment["id"]],"exact_quote":quote,
                     "reason":"A second problem found on recheck"})
        return rows
    def repair(**kw):
        seen.append("Sol")
        return {"repairs":[{"old":"Three timed readings.",
                            "new":"Four timed readings.",
                            "why":"reported count differs"}]}
    with pytest.raises(QualityStop,match="POST_REPAIR_SEMANTIC_FINDINGS"):
        qualify(story=text,writer_result=writer,approved=approved,
                audit=audit,repair=repair)
    assert seen==["Luna","Sol","Luna"]


def test_model_repair_unflagged_story_region_is_rejected():
    text,writer,approved=source()
    def audit(**kw):return all_family_findings(kw["story"],True)
    def bad_model(**kw):
        return {"repairs":[{"old":"Dessa signed beneath the record.",
                            "new":"Dessa burned the record.",
                            "why":"not allowed"}]}
    with pytest.raises(QualityStop,match="MODEL_REPAIR_NOT_IN_FLAGGED_SPAN"):
        qualify(story=text,writer_result=writer,approved=approved,
                audit=audit,repair=bad_model)


def test_structural_findings_stop_without_repair():
    text,writer,approved=source()
    done=[]
    def audit(**kw):
        p=all_family_findings(kw["story"],True)
        next(r for r in p["evaluations"] if r["family"]=="state_continuity")["repair_scope"]="structural"
        return p
    def repair(**kw):done.append("Sol")
    with pytest.raises(QualityStop,match="NONLOCAL_DEFECT_REQUIRES_REPLAN"):
        qualify(story=text,writer_result=writer,approved=approved,audit=audit,repair=repair)
    assert done==[]


def test_original_source_cannot_be_substituted():
    text,writer,approved=source()
    with pytest.raises(QualityStop,match="STORY_SOURCE_MISMATCH"):
        qualify(story=text+"faked",writer_result=writer,approved=approved,
                audit=lambda **kw:{},repair=lambda **kw:{})


def test_negation_dismissal_is_anchored_not_blanket():
    text,_,approved=source()
    packet=build_story_authority_packet_v2(approved)
    active,ignored=_safe_hard(text,packet)
    assert active==[]
    assert len(ignored)==2
    altered=text.replace("Not established: cause.", "Established: cause.",1)
    active,ignored=_safe_hard(altered,packet)
    assert any(x["guard_id"]=="unresolved_cause_overclaim" for x in active)


def test_bad_audit_schema_fails_closed():
    text,writer,approved=source()
    with pytest.raises(QualityStop,match="INVALID_AUDIT_CONTRACT"):
        qualify(story=text,writer_result=writer,approved=approved,
                audit=lambda **kw:{"evaluations":[]},repair=lambda **kw:{})


def test_frozen_source_integrity():
    from src.frozen_lane_verify import verify_frozen_lane
    assert verify_frozen_lane(Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json"))["verified_files"]==43
