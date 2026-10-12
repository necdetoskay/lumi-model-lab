import copy
import pytest
from src.q25_entity_candidates import represent,fingerprint
from src.q25_offline_diagnostic import digest

PROSE='Ela ayracı kitaba koydu.'
def case():
    seed=dict(characters={'Ela':dict(inventory={'marker':1})},objects={'marker':dict(owner='Ela',location='room',state={})},topology=dict(locations=['room']))
    span=dict(start=0,end=len(PROSE),text=PROSE)
    proposal=dict(seed_sha256=fingerprint(seed),source_sha256=digest(PROSE),objects=[dict(key='book',description='Reading book',role='ORDINARY_OBJECT',mention=span)],terminal_relations=[dict(subject='object:marker',kind='IN_CONTAINER',target='new:book',evidence=span),dict(subject='object:marker',kind='HELD_BY',target=None,evidence=span)])
    return seed,proposal
def run(seed,proposal):return represent(seed=seed,prose=PROSE,proposal=proposal)

def test_terminal_containment_replaces_hand_holding_and_preserves_ownership():
    seed,p=case();before=copy.deepcopy(seed);r=run(seed,p);identity=r['candidate_objects'][0]['id']
    assert r['container_contents']=={identity:['object:marker']} and r['directly_held_objects']=={}
    assert any(e['kind']=='OWNED_BY' and e['target']=='character:Ela' for e in r['relations'])
    assert seed==before and not r['state_commit_authorized'] and not r['semantic_support_certified']
    assert r==run(seed,p)

@pytest.mark.parametrize('damage',['source','seed','mention','clue','unknown_subject','unknown_target','wrong_target_type','duplicate_object','duplicate_relation','held_conflict','self_container','cycle'])
def test_invalid_or_unauthorized_proposals_cannot_be_laundered(damage):
    seed,p=case();span=p['objects'][0]['mention']
    if damage=='source':p['source_sha256']='0'*64
    elif damage=='seed':p['seed_sha256']='0'*64
    elif damage=='mention':p['objects'][0]['mention']['text']='Not present'
    elif damage=='clue':p['objects'][0]['role']='DECISIVE_CLUE'
    elif damage=='unknown_subject':p['terminal_relations'][0]['subject']='object:invented'
    elif damage=='unknown_target':p['terminal_relations'][0]['target']='new:missing'
    elif damage=='wrong_target_type':p['terminal_relations'][0]['target']='character:Ela'
    elif damage=='duplicate_object':p['objects'].append(copy.deepcopy(p['objects'][0]))
    elif damage=='duplicate_relation':p['terminal_relations'].append(copy.deepcopy(p['terminal_relations'][0]))
    elif damage=='held_conflict':p['terminal_relations']=p['terminal_relations'][:1]
    elif damage=='self_container':p['terminal_relations'][0]['target']='object:marker'
    elif damage=='cycle':p['terminal_relations'].append(dict(subject='new:book',kind='IN_CONTAINER',target='object:marker',evidence=span))
    before=copy.deepcopy(seed)
    with pytest.raises(ValueError):run(seed,p)
    assert seed==before

def test_new_owner_is_unknown_and_is_not_inferred_from_reading():
    seed,p=case();r=run(seed,p);identity=r['candidate_objects'][0]['id']
    assert not any(e['subject']==identity and e['kind']=='OWNED_BY' for e in r['relations'])

def test_multiple_entities_need_explicit_identity_resolution_not_descriptor_merging():
    seed,p=case();second=copy.deepcopy(p['objects'][0]);second['key']='another_book';p['objects'].append(second)
    r=run(seed,p)
    assert len({c['id'] for c in r['candidate_objects']})==2
