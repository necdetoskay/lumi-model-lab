import copy
import pytest
from src.q25_offline_diagnostic import diagnose,digest

PROSE='Ela ayracı kitaba koydu.'
def finding(category='EDITORIAL_DEFECT'):
    return dict(id='F1',category=category,reason='Test claim',source_sha256=digest(PROSE),span=dict(start=0,end=len(PROSE),text=PROSE),authority_ref=None)
def run(f=None,assessments=None,gaps=None):
    return diagnose(prose=PROSE,findings=[f or finding()],assessments=assessments or [],gaps=gaps or [],authority_refs=['seed#/rules/0'])

@pytest.mark.parametrize('damage',['hash','text','bounds'])
def test_bad_citation_is_review_failure_not_story_failure(damage):
    f=finding()
    if damage=='hash':f['source_sha256']='0'*64
    if damage=='text':f['span']['text']='Başka metin'
    if damage=='bounds':f['span']['end']=999
    r=run(f);assert r['review_status']=='INVALID_REVIEW'
    assert r['narrative_status']=='UNVERIFIED' and not r['story_rejection_authorized'] and not r['state_commit_authorized']

def test_existing_quote_does_not_certify_semantic_support():
    r=run(assessments=[dict(finding_id='F1',support='UNSUPPORTED',note='Draft reading, claim unrelated')])
    assert r['review_status']=='DISPUTED_REVIEW' and r['independent_adjudication_required']

def test_hard_claim_needs_authority_but_reference_is_not_semantic_proof():
    f=finding('HARD_INVALID');assert run(f)['review_status']=='INVALID_REVIEW'
    f['authority_ref']='seed#/rules/0';r=run(f)
    assert r['review_status']=='ADJUDICATION_REQUIRED' and not r['story_rejection_authorized']

def test_preference_and_supported_draft_never_grant_acceptance():
    r=run(finding('EDITORIAL_PREFERENCE'),[dict(finding_id='F1',support='SUPPORTED',note='Taste only')])
    assert not r['findings'][0]['blocking_story'] and not r['semantic_quality_pass']

def test_gap_keeps_prose_and_blocks_state_even_without_review_findings():
    gap=dict(kind='UNREPRESENTED_ENTITY',description='Book has no canonical identity',source_sha256=digest(PROSE),span=dict(start=0,end=len(PROSE),text=PROSE));before=copy.deepcopy(gap)
    r=diagnose(prose=PROSE,findings=[],assessments=[],gaps=[gap],authority_refs=[])
    assert r['state_status']=='STATE_MODEL_GAP' and r['persistence_status']=='BLOCKED' and gap==before

def test_invalid_gap_cannot_be_laundered_as_valid_observation():
    with pytest.raises(ValueError):run(gaps=[dict(kind='UNREPRESENTED_ENTITY',description='Gap',source_sha256='wrong',span=dict(start=0,end=len(PROSE),text=PROSE))])

@pytest.mark.parametrize('assessment',[dict(finding_id='UNKNOWN',support='SUPPORTED',note='unknown'),dict(finding_id='F1',support='SUPPORTED',note='self-certified',independently_adjudicated=True)])
def test_unknown_or_self_certified_assessment_rejected(assessment):
    with pytest.raises(ValueError):run(assessments=[assessment])
