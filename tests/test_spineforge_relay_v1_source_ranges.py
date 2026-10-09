import copy,json
from pathlib import Path
import pytest
from src.spineforge_production_source_ranges import range_table,resolve_range_guard,strict_range_schema
from scripts.spineforge_production_replay import verify_story

def raw(prose,choice=None):
    table=range_table(prose)
    return dict(source_sha256=table['source_sha256'],event_evidence=[dict(event_id='E',predicate_id='P',subject='Aya',action='OBSERVE',target='repair',verdict='SUPPORTED',provenance='DIRECT_OBSERVATION',evidence_subject='Aya',state_pointer=None,reason='Synthetic selection only',source_range_id=choice or table['ranges'][0][0])],residual=dict(schema_name='spineforge-relay.semantic-guard.v1',decision='PASS',findings=[],summary='Control'))

def test_all_offered_choices_are_bounded_contiguous_original_substrings():
    prose='😀 Aya watched Mert’s hand. “Wait!”\nFirst. Second. Third. Fourth. Fifth. Sixth. Seventh. Eighth. Ninth.'
    table=range_table(prose)
    assert len({r[0] for r in table['ranges']})==len(table['ranges'])
    for choice,first,last in table['ranges']:
        assert 0<=first<=last<len(table['spans']) and last-first<8
        resolved=resolve_range_guard(raw(prose,choice),prose,table)
        assert resolved.event_evidence[0].exact_text==prose[table['spans'][first]['start']:table['spans'][last]['end']]
    schema=strict_range_schema(table)
    assert schema['properties']['source_sha256']['enum']==[table['source_sha256']]
    assert schema['$defs']['RangePredicateV1']['properties']['source_range_id']['enum']==[r[0] for r in table['ranges']]
    assert 'source_span_ids' not in str(schema) and 'exact_text' not in str(schema)

@pytest.mark.parametrize('defect',['unknown','stale','list','copied','table_order','table_offset','table_prose'])
def test_invalid_selection_or_tampered_table_fails_closed(defect):
    prose='First. Second. Third.';table=range_table(prose);value=raw(prose)
    if defect=='unknown':value['event_evidence'][0]['source_range_id']='R9999'
    elif defect=='stale':value['source_sha256']='0'*64
    elif defect=='list':value['event_evidence'][0]['source_span_ids']=[table['spans'][0]['id'],table['spans'][2]['id']]
    elif defect=='copied':value['event_evidence'][0]['exact_text']='Invented'
    elif defect=='table_order':table['ranges'][0][1:]=[2,0]
    elif defect=='table_offset':table['spans'][0]['start']=1
    else:table['spans'][0]['text']='Altered'
    with pytest.raises(ValueError):resolve_range_guard(value,prose,table)

def test_q18_original_rejection_and_partial_state_stay_immutable():
    root=Path('evidence/spineforge-relay/SFR-V1-Q18-BOUND-REVIEW-ROBOT-20261009')
    proof=verify_story(root/'story',root/'plan-1-fixture.json')
    assert proof['recorded_decision']=='REJECT_NON_CONVERGENT' and proof['final_revision']==3
    prose=json.loads((root/'story/S4_OnarimVeTest-1-writer-text.json').read_text(encoding='utf8'))['text']
    old=json.loads(json.loads((root/'story/S4_OnarimVeTest-1-guard-text.json').read_text())['text'])
    assert old['event_evidence'][1]['source_span_ids']==[range_table(prose)['spans'][i]['id'] for i in [0,5]]
    table=range_table(prose);choice=next(r[0] for r in table['ranges'] if r[1:]==[0,5])
    example=raw(prose,choice)
    resolved=resolve_range_guard(example,prose)
    expected=prose[table['spans'][0]['start']:table['spans'][5]['end']]
    assert resolved.event_evidence[0].exact_text==expected
    assert table['spans'][2]['text'] in expected
    assert not (root/'story/S4_OnarimVeTest-accepted.json').exists()
    # A separately authored range example is not repaired Q18/model evidence.
