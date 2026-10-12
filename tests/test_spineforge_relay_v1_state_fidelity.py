import copy
import json
from pathlib import Path
import pytest
from src.spineforge_state_fidelity import audit_state_fidelity
from src.spineforge_production_source_ranges import range_table
from src.spineforge_relay_v1_contracts import canonical_sha256


def inputs():
    prose = "Ada placed the key in the box."
    state = {"objects": {"key": {"container": None}}}
    review = dict(schema_name="spineforge.state-fidelity-review.v1",
        source_sha256=range_table(prose)["source_sha256"],
        state_sha256=canonical_sha256(state),reviewer="synthetic control",
        observations=[dict(state_pointer="/objects/key/container",
            observed_value="box",source_range_id="R0000")])
    return dict(prose=prose,state=state,review=review)


def test_divergence_does_not_mutate_inputs():
    data = inputs(); before = copy.deepcopy(data)
    result = audit_state_fidelity(**data)
    assert result["status"] == "FINDINGS_PRESENT"
    assert result["findings"][0]["exact_text"] == data["prose"]
    assert data == before


@pytest.mark.parametrize("kind", ["prose", "state", "range", "duplicate", "escape"])
def test_invalid_evidence_fails_closed(kind):
    data = inputs()
    if kind == "prose": data["prose"] += " Changed."
    if kind == "state": data["state"]["objects"]["key"]["container"] = "box"
    if kind == "range": data["review"]["observations"][0]["source_range_id"] = "R9999"
    if kind == "duplicate": data["review"]["observations"] *= 2
    if kind == "escape": data["review"]["observations"][0]["state_pointer"] = "/objects/key/~2"
    with pytest.raises(ValueError): audit_state_fidelity(**data)


@pytest.mark.parametrize("missing", [False, True])
def test_missing_is_distinct_from_null(missing):
    data = inputs(); data["review"]["observations"][0]["observed_value"] = None
    if missing: del data["state"]["objects"]["key"]["container"]
    data["review"]["state_sha256"] = canonical_sha256(data["state"])
    result = audit_state_fidelity(**data)
    assert bool(result["findings"]) is missing


def test_empty_review_does_not_claim_completeness():
    data=inputs(); data["review"]["observations"] = []
    result=audit_state_fidelity(**data)
    assert result["status"] == "NO_OBSERVED_DIVERGENCE"
    assert result["semantic_completeness_verified"] is False


def test_json_boolean_is_not_number():
    data=inputs(); data["state"]["objects"]["key"]["container"] = True
    data["review"]["state_sha256"] = canonical_sha256(data["state"])
    data["review"]["observations"][0]["observed_value"] = 1
    assert audit_state_fidelity(**data)["findings"]


def test_q22_recorded_container_finding():
    root=Path("evidence/spineforge-relay/SFR-V1-Q22-PLAN-V4-MYSTERY-20261009")
    story=root/"story"; scene="S6_Etkinlik_Baslar"
    prose=json.loads((story/f"{scene}-1-writer-text.json").read_text())["text"]
    state=json.loads((story/f"{scene}-accepted.json").read_text())["state_after"]
    editorial=json.loads((root/"editorial-reading.json").read_text())["findings"][0]
    table=range_table(prose)
    # Human editorial observation, not a fabricated provider extraction.
    choice=next(row for row in table["ranges"] if editorial["quote"] in
        prose[table["spans"][row[1]]["start"]:table["spans"][row[2]]["end"]])
    review=dict(schema_name="spineforge.state-fidelity-review.v1",
        reviewer="recorded Q22 manual editorial review",
        source_sha256=table["source_sha256"],state_sha256=canonical_sha256(state),
        observations=[dict(state_pointer=editorial["state_pointer"],
            observed_value=editorial["observed_prose_container"],source_range_id=choice[0])])
    result=audit_state_fidelity(prose=prose,state=state,review=review)
    assert result["status"] == "FINDINGS_PRESENT"
    assert result["findings"][0]["recorded_value"] is None
    assert result["findings"][0]["observed_value"] == "preparation_notebook"
