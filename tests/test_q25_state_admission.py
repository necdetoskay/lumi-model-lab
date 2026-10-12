import copy,json
from pathlib import Path
import pytest
from src.q25_state_admission import build_draft,AdmissionPolicy
from src.q25_entity_candidates import fingerprint
from tests.test_q25_entity_candidates import case,PROSE

def run(seed,p,policy=None):return build_draft(seed=seed,prose=PROSE,proposal=p,policy=policy or {})

def test_default_policy_cannot_admit_new_object():
    seed,p=case();r=run(seed,p)
    assert r['structural_admission']=='BLOCKED_BY_POLICY' and r['draft_state'] is None

def test_draft_preserves_unknown_owner_and_resolves_mutually_consistent_relations():
    seed,p=case();before=copy.deepcopy(seed);r=run(seed,p,dict(allow_new_ordinary_objects=True));draft=r['draft_state'];new=[k for k in draft['objects'] if k.startswith('new_')][0]
    assert draft['objects']['marker']['container']==dict(status='KNOWN',ref=new)
    assert draft['objects'][new]['contains']==['marker']
    assert draft['objects']['marker']['owner']==dict(status='KNOWN',ref='Ela')
    assert draft['objects'][new]['owner']==dict(status='UNKNOWN',ref=None)
    assert draft['characters']['Ela']['inventory']=={} and seed==before
    assert r['structural_admission']=='ELIGIBLE_DRAFT' and not r['state_commit_authorized']
    assert r==run(seed,p,dict(allow_new_ordinary_objects=True))

@pytest.mark.parametrize('field',['owner','location'])
def test_policy_can_require_resolved_fields_without_inventing_values(field):
    seed,p=case();r=run(seed,p,dict(allow_new_ordinary_objects=True,**{'allow_unknown_'+field:False}))
    assert r['structural_admission']=='BLOCKED_BY_POLICY' and r['draft_state'] is None

def test_library_ownership_and_world_are_preserved():
    seed,p=case();seed['objects']['marker']['owner']='library';seed['world']=dict(rules=['no magic']);p['seed_sha256']=fingerprint(seed)
    r=run(seed,p,dict(allow_new_ordinary_objects=True))
    assert r['draft_state']['objects']['marker']['owner']==dict(status='KNOWN',ref='library')
    assert r['draft_state']['world']==seed['world']

def test_policy_cannot_claim_production_or_model_semantic_approval():
    for extra in (dict(scope='PRODUCTION'),dict(semantic_support_certified=True)):
        with pytest.raises(ValueError):AdmissionPolicy.model_validate(extra)

def test_original_seed_container_and_contents_are_not_modified():
    root=Path('evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24');seed=json.loads((root/'seed-input.json').read_text(encoding='utf8'));before=copy.deepcopy(seed)
    prose=json.loads((root/'writer-2-text.json').read_text(encoding='utf8'))['text'];proposal=json.loads(Path('evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json').read_text(encoding='utf8'))
    r=build_draft(seed=seed,prose=prose,proposal=proposal,policy=dict(allow_new_ordinary_objects=True));draft=r['draft_state']
    assert draft['objects']['blue_atlas']['contains']==[] and seed==before
    assert seed['objects']['red_bookmark']['state']['container']=='blue_atlas'
    assert draft['objects']['red_bookmark']['container']['ref'].startswith('new_')
    assert 'revision' not in draft and not r['state_commit_authorized']
