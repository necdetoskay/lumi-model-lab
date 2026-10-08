import json
from pathlib import Path

import pytest

from src.spineforge_joint_story_runner import build_chain, spatial_for, prepare, execute_story, runner_request_for
from src.spineforge_joint_spatial import CarryGroupV1, JointMoveV1, replay_joint
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialOperationV1
from src.spineforge_relay_v1_contracts import canonical_sha256
from tests.test_spineforge_relay_v1_runner import _guard

FIXTURE = Path('tests/fixtures/spineforge_relay_v1/q11_joint_mosaic_chain.json')


def context():
    f, _, _, _, rows, _ = build_chain(FIXTURE)
    plan, contract, state = rows[3]
    spatial = spatial_for(f, plan, contract, state)
    return spatial, state


def test_joint_move_updates_every_member_atomically_without_mutating_entry():
    contract, state = context()
    before = contract.entry.model_copy(deep=True)
    after = replay_joint(topology=contract.topology,entry=contract.entry,groups=contract.carry_groups,operations=contract.operations,story_state=state)
    assert contract.entry == before
    assert set(after.positions.values()) == {'covered_yard'}
    assert len(contract.operations) == 1


@pytest.mark.parametrize('case', ['split','hold','blocked','permission','edge','individual','duplicate','alias','undeclared'])
def test_invalid_joint_moves_are_denied_without_partial_updates(case):
    contract, state = context()
    entry = contract.entry.model_copy(deep=True)
    groups = [g.model_copy(deep=True) for g in contract.carry_groups]
    topology = contract.topology.model_copy(deep=True)
    ops = [o.model_copy(deep=True) for o in contract.operations]
    if case == 'split':
        entry.positions['Mert'] = 'covered_yard'
    elif case == 'hold':
        state.objects['mosaic_panel'].state['carried_by'] = ['Aya']
    elif case == 'blocked':
        entry.access_constraints[0].active = True
    elif case == 'permission':
        topology.edges[0].allowed_entities.remove('mosaic_panel')
        entry.topology_sha256 = canonical_sha256(topology)
    elif case == 'edge':
        ops[0].edge_id = 'invented_edge'
    elif case == 'individual':
        ops = [SpatialOperationV1(id='split',kind='MOVE',subject='Aya',target='covered_yard',event_id='E',predicate_id='P',edge_id='yard_gate')]
    elif case == 'duplicate':
        groups.append(groups[0].model_copy(deep=True))
    elif case == 'undeclared':
        groups.clear()
    else:
        groups[0].id = 'Aya'
    before = entry.model_copy(deep=True)
    with pytest.raises(ValueError):
        replay_joint(topology=topology,entry=entry,groups=groups,operations=ops,story_state=state)
    assert entry == before


def fake(calls, ambiguous=False):
    def call(**kwargs):
        payload = json.loads(kwargs['user_prompt'])
        calls.append(payload)
        writer = 'gpt-5.6-sol' in kwargs['model']
        stage = 'writer' if writer else 'guard'
        def anchor(e, p):
            if p['action'] == 'JOINT_MOVE':
                return 'Aya and Mert carried the same mosaic panel together into '+p['target']+', maintaining their shared hold.'
            return f"{e} {p['subject']} {p['action']} {p['target']}."
        if writer:
            text = ' '.join([anchor(e['id'],p) for e in payload['scene_contract']['required_events'] for p in e['predicates']] + ['calm']*190)
        else:
            report = _guard(payload,payload['candidate_prose'])
            for row in report['event_evidence']:
                row['exact_text'] = anchor(row['event_id'],row)
                if ambiguous and row['action']=='JOINT_MOVE':
                    row['verdict']='AMBIGUOUS'
            text = json.dumps(report)
        _, request = runner_request_for(stage,payload)
        return text, {'id':'synthetic-'+str(len(calls)), 'choices':[{'finish_reason':'stop','message':{'content':text}}], 'usage':{'prompt_tokens':1200,'completion_tokens':450,'total_tokens':1650,'cost':.01}}, request
    return call


def test_new_engine_completes_same_frozen_route_with_one_shared_anchor(tmp_path):
    calls = []
    result = execute_story(fixture_path=FIXTURE,api_key='synthetic',preflight=prepare(FIXTURE),output=tmp_path/'run',call_fn=fake(calls))
    assert result['status']=='ACCEPT' and result['state_advanced_to_revision']==6
    assert len(calls)==12
    for payload in calls[6::2]:
        ops=payload['spatial_contract']['operations']
        assert len(ops)==1 and ops[0]['kind']=='JOINT_MOVE'
        assert payload['spatial_contract']['carry_groups'][0]['carriers']==['Aya','Mert']
    from scripts.spineforge_relay_story_replay import verify_story
    assert verify_story(tmp_path/'run',FIXTURE)['final_revision']==6
    from src.spineforge_spatial_story_runner import build_chain as old
    previous=old(Path('tests/fixtures/spineforge_relay_v1/q10_mosaic_spatial_chain.json'))
    current=build_chain(FIXTURE)
    assert canonical_sha256(current[3])==canonical_sha256(previous[3])
    assert canonical_sha256(current[-1])==canonical_sha256(previous[-1])


def test_ambiguous_shared_crossing_stops_at_revision_three(tmp_path):
    calls=[]
    result=execute_story(fixture_path=FIXTURE,api_key='synthetic',preflight=prepare(FIXTURE),output=tmp_path/'blocked',call_fn=fake(calls,ambiguous=True))
    assert result['status']=='REJECT_NON_CONVERGENT'
    assert result['state_advanced_to_revision']==3 and result['next_spine_beat']=='S04'
    assert len(calls)==10
    assert not any(p['scene_contract']['scene_id']=='S05' for p in calls)


def test_saved_joint_preflight_is_current_without_new_authorization():
    from src.spineforge_joint_paid_entry import prepare_reserved_story
    root=Path('evidence/spineforge-relay/SFR-V1-Q11-PREFLIGHT-20261008')
    assert json.loads((root/'preflight.json').read_text()) == prepare_reserved_story(FIXTURE)
    assert json.loads((root/'proposal.json').read_text())['paid_execution_authorized'] is False
