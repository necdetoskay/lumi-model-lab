"""New Final V3 revision: do not impose client output-token ceilings.

The old V3 freeze is intentionally not silently rebaselined: this is a separate
43-file verified revision with a new profile. No provider calls in this suite.
"""
import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src import generate
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest


PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v3_uncapped.json")
LEGACY=Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
ROLE_STAGES=(
    "src/episode_spine_v2_generate.py",
    "src/episode_writer_v2_generate.py",
    "src/episode_authority_gate_v1.py",
    "src/episode_authority_adjudication_v1.py",
    "src/episode_bounded_repair_v1.py",
    "src/episode_translation_v1.py",
    "src/episode_translation_repair_v1.py",
    "src/episode_fidelity_v1.py",
    "src/episode_fidelity_adjudication_v1.py",
)
MODEL_ROUTES=(
    ("anthropic/claude-sonnet-5.5", "saga_architect"),
    ("openai/gpt-5.6-luna", "editorial_audit"),
    ("aion-labs/aion-3.5-mini", "teacher_story_medium_reasoning"),
    ("openai/gpt-5.6-luna", "defect_locator"),
    ("openai/gpt-5.6-sol", "editorial_audit"),
    ("google/gemini-3.8-flash", "translation"),
)


@pytest.mark.parametrize("path",ROLE_STAGES)
def test_no_hard_output_cap_in_active_stage_call_sites(path):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"),filename=path)
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            for kw in node.keywords:
                if kw.arg in {"max_tokens","max_completion_tokens"}:
                    assert isinstance(kw.value,ast.Constant) and kw.value.value is None, (
                        path, kw.arg, getattr(kw,"lineno",None)
                    )


@pytest.mark.parametrize("model,request_class",MODEL_ROUTES)
def test_real_openrouter_payload_omits_output_token_ceiling(model,request_class):
    observed=[]
    class FakeResponse:
        ok=True
        status_code=200
        headers={}
        def json(self):
            return {
                "id":"gen-offline-mock",
                "choices":[{"message":{"content":"{\"status\":\"ok\"}"},"finish_reason":"stop"}],
                "usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2,"cost":0},
            }
    def fake_post(url,**kwargs):
        observed.append(kwargs["json"])
        return FakeResponse()
    with patch.object(generate.requests,"post",side_effect=fake_post):
        _raw,_body,wire=generate.call_openrouter(
            api_key="OFFLINE-FAKE-NOT-SECRET",
            model=model,
            system_prompt="System test",
            user_prompt="Structured test",
            temperature=0,
            max_tokens=None,
            seed=123,
            request_class=request_class,
            structured_output=True,
        )
    assert len(observed)==1
    assert "max_tokens" not in observed[0]
    assert "max_completion_tokens" not in observed[0]
    assert "max_tokens" not in wire


def test_43_file_uncapped_revision_hashes_match():
    result=verify_frozen_lane(PROFILE)
    assert result["verified_files"]==43
    assert result["verified"] is True
    assert result["runtime_revision"]=="AGE18-V3-UNCAPPED-v1"


def test_prior_frozen_v2_hashes_are_not_silently_reused():
    with pytest.raises(RuntimeError,match="Frozen lane runtime changed"):
        verify_frozen_lane(LEGACY)


@pytest.mark.parametrize("slug",[
    "closed_platform","orbit_rescue","council_seal","mirror_marsh"
])
def test_four_cases_point_to_uncapped_profile_and_block_paid_dispatch(slug):
    path=Path("data/specifications/story_lab/four_genre_v3_inputs")/f"{slug}_case_manifest_v1.json"
    case=load_case_manifest(path)
    assert case["lane_profile"]==str(PROFILE)
    assert case["paid_spine_authorized"] is False
    assert case["human_spine_approval"] is False


def test_old_paid_grant_cannot_be_reused_for_new_revision():
    old=json.loads(Path("experiments/triggers/v3-four-spine-once-20261015.json").read_text())
    new=json.loads(PROFILE.read_text())
    assert old["frozen_v3_sha"] != "NEW_UNCAPPED_REVISION"
    assert new["uncapped_output_policy"]["previous_paid_claim_invalid_for_this_revision"] is True


@pytest.mark.parametrize("ceiling_key",["max_tokens","max_completion_tokens","max_output_tokens"])
def test_paid_guard_blocks_reintroduced_ceiling_before_provider_post(tmp_path,ceiling_key):
    from decimal import Decimal
    from src.v3_single_attempt_guard import SafetyStop,SingleAttemptSpineGuard
    guard=SingleAttemptSpineGuard(tmp_path,Decimal("0.50"))
    actual=[]
    guard._post=lambda *args,**kwargs: actual.append(kwargs)
    payload={"model":"anthropic/claude-sonnet-5.5",ceiling_key:12000}
    with pytest.raises(SafetyStop,match="EXPLICIT_OUTPUT_TOKEN_CEILING_FORBIDDEN"):
        guard._one_post(generate.OPENROUTER_URL,json=payload)
    assert guard.calls==0
    assert actual==[]
