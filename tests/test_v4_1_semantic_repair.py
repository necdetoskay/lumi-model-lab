"""V4.1 epistemic model repair policy, all tests fully offline."""
import copy
import json
from pathlib import Path

import pytest

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.v4_epistemic_repair import apply_epistemic_model_patch,V4EpistemicRepairRejected
from src.v4_logistics import canonical_beat_route

F2=Path("data/specifications/story_lab/age18_forbidden_cartographer_f2_approved_for_aion_20261015.json")

def source():
    return copy.deepcopy(json.loads(F2.read_text(encoding="utf-8"))["episode_spine"])


def test_model_only_narrows_reversal_claim_and_preserves_every_beat_and_choice():
    raw=source()
    old=raw["reversal"]["evidence"][0]["claim"]
    patch={"patches":[
        {"field":"reversal.evidence[0].claim",
         "value":"The instrument readings disagree, but they do not establish the underlying cause."},
        {"field":"reversal.inference_ceiling",
         "value":"Cause, independence and recurrence remain unproved on this record."},
    ]}
    fixed,record=apply_epistemic_model_patch(raw,patch)
    assert len(record)==2
    assert fixed["reversal"]["evidence"][0]["claim"]!=old
    assert fixed["beats"]==raw["beats"]
    assert fixed["decision_point"]==raw["decision_point"]
    assert fixed["logistics_plan"]==raw["logistics_plan"]
    assert canonical_beat_route(fixed["beats"])==canonical_beat_route(raw["beats"])
    EpisodeSpineV2.model_validate(fixed)
    assert raw["reversal"]["evidence"][0]["claim"]==old


@pytest.mark.parametrize("field",[
    "beats[2].new_information","beats[0].location_ref",
    "decision_point.branches[0].option","world_state","logistics_plan.time_window",
    "reversal.evidence[99].claim","reversal.evidence[0].supporting_beat_keys",
    "writer_rules",
])
def test_unsupported_patch_paths_fail(field):
    raw=source()
    with pytest.raises(V4EpistemicRepairRejected):
        apply_epistemic_model_patch(raw,{"patches":[{"field":field,"value":"Changed text"}]})


@pytest.mark.parametrize("change",[
    "OBSERVED","INFERRED","HYPOTHESIS","UNKNOWN",
])
def test_certainty_cannot_be_upgraded_or_same(change):
    raw=source()
    evidence=raw["reversal"]["evidence"]
    prior=evidence[0]["certainty"]
    value={"OBSERVED":"HYPOTHESIS","INFERRED":"OBSERVED","HYPOTHESIS":"OBSERVED","UNKNOWN":"UNKNOWN"}[change]
    evidence[0]["certainty"]=value
    # Increase HYPOTHESIS/INFERRED to OBSERVED or make no-op.
    proposed="OBSERVED"
    with pytest.raises(V4EpistemicRepairRejected):
        apply_epistemic_model_patch(raw,{"patches":[{"field":"reversal.evidence[0].certainty","value":proposed}]})


def test_downgrading_certainty_is_allowed():
    raw=source()
    raw["reversal"]["evidence"][0]["certainty"]="OBSERVED"
    fixed,patch=apply_epistemic_model_patch(raw,{
        "patches":[{"field":"reversal.evidence[0].certainty","value":"INFERRED"}]})
    assert fixed["reversal"]["evidence"][0]["certainty"]=="INFERRED"
    assert len(patch)==1


def test_repeated_same_field_fails():
    raw=source()
    with pytest.raises(V4EpistemicRepairRejected):
        apply_epistemic_model_patch(raw,{"patches":[
            {"field":"reversal.inference_ceiling","value":"A"},
            {"field":"reversal.inference_ceiling","value":"B"},
        ]})


def test_v4_1_code_no_extra_client_output_limit():
    from pathlib import Path
    code=Path("src/episode_spine_v4_1_generate.py").read_text(encoding="utf-8")
    assert "max_tokens=None" in code
    assert "max_tokens=12000" not in code
    assert "apply_epistemic_model_patch" in code
    assert "v4_gate_recheck_call" in code
    assert "gate.decision==\"REPLAN\"" in code
