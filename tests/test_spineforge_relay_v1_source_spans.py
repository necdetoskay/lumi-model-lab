import json
from pathlib import Path

import pytest

from src.spineforge_source_spans import source_table, resolve_span_guard, strict_span_schema
from src.spineforge_span_story_runner import prepare, execute_story, runner_request_for
from tests.test_spineforge_relay_v1_joint_movement import fake as prior_fake

FIXTURE=Path('tests/fixtures/spineforge_relay_v1/q12_span_mosaic_chain.json')


def raw(prose,ids=None):
    table=source_table(prose)
    row=dict(event_id='E',predicate_id='P',subject='Aya',action='MATCH_PACE',target='carry',verdict='SUPPORTED',provenance='DIRECT_OBSERVATION',source_span_ids=ids or [table['spans'][0]['id']],evidence_subject='Aya',state_pointer=None,reason='Observed')
    return dict(source_sha256=table['source_sha256'],event_evidence=[row],residual=dict(schema_name='spineforge-relay.semantic-guard.v1',decision='PASS',findings=[],summary='Clear'))


def test_unicode_quotes_and_offsets_are_preserved_without_retyping():
    prose='😀 Aya matched Mert’s pace. “Together?”\nShe waited.'
    table=source_table(prose)
    assert all(prose[s['start']:s['end']]==s['text'] for s in table['spans'])
    resolved=resolve_span_guard(raw(prose),prose)
    assert resolved.event_evidence[0].exact_text=='😀 Aya matched Mert’s pace.'
    assert 'Mert’s' in resolved.event_evidence[0].exact_text
    schema=strict_span_schema(table)
    assert schema['properties']['source_sha256']['const']==table['source_sha256']
    assert schema['$defs']['SpanPredicateV1']['properties']['source_span_ids']['items']['enum']==[s['id'] for s in table['spans']]


@pytest.mark.parametrize('case',['unknown','stale','duplicate','reversed','noncontiguous','retyped'])
def test_bad_references_fail_closed(case):
    prose='First. Second. Third.';value=raw(prose);ids=[s['id'] for s in source_table(prose)['spans']]
    if case=='unknown':value['event_evidence'][0]['source_span_ids']=['unknown']
    elif case=='stale':value['source_sha256']='0'*64
    elif case=='duplicate':value['event_evidence'][0]['source_span_ids']=[ids[0],ids[0]]
    elif case=='reversed':value['event_evidence'][0]['source_span_ids']=[ids[1],ids[0]]
    elif case=='noncontiguous':value['event_evidence'][0]['source_span_ids']=[ids[0],ids[2]]
    else:value['event_evidence'][0]['exact_text']='Invented quote'
    with pytest.raises(ValueError):resolve_span_guard(value,prose)


def test_contiguous_selection_and_residual_findings_copy_original_text():
    prose='First.\nSecond.';table=source_table(prose);value=raw(prose,[s['id'] for s in table['spans']])
    value['residual'].update(decision='REWRITE',findings=[dict(code='X',family='physical',severity='BLOCKING',source_span_ids=[table['spans'][1]['id']],reason='Physical issue',repair_instruction='Repair')])
    resolved=resolve_span_guard(value,prose)
    assert resolved.event_evidence[0].exact_text==prose
    assert resolved.residual.findings[0].exact_text=='Second.'


def test_q11_apostrophe_example_can_be_referenced_without_changing_records():
    root=Path('evidence/spineforge-relay/SFR-V1-Q11-JOINT-MOSAIC-20261008')
    prose=json.loads((root/'S04-2-writer-text.json').read_text())['text']
    analysis=json.loads((root/'failure-analysis.json').read_text())
    original=analysis['attempts'][1]['original_quote']
    span=next(s for s in source_table(prose)['spans'] if s['text']==original)
    assert resolve_span_guard(raw(prose,[span['id']]),prose).event_evidence[0].exact_text==original
    assert json.loads((root/'result.json').read_text())['status']=='REJECT_NON_CONVERGENT'


@pytest.mark.parametrize('bad_reference',[False,True])
def test_new_engine_resolves_event_spans_and_replays_six_scenes(tmp_path,bad_reference):
    calls=[];provider=prior_fake(calls)
    def fake(**kwargs):
        text,body,_=provider(**kwargs)
        payload=json.loads(kwargs['user_prompt']);stage='writer' if 'gpt-5.6-sol' in kwargs['model'] else 'guard'
        if stage=='guard':
            report=json.loads(text);table=payload['source_span_table']
            report['source_sha256']=table['source_sha256']
            for row in report['event_evidence']:
                quote=row.pop('exact_text');row['source_span_ids']=[next(s['id'] for s in table['spans'] if s['text']==quote)]
            if bad_reference:report['event_evidence'][0]['source_span_ids']=['unknown']
            text=json.dumps(report);body['choices'][0]['message']['content']=text
        return text,body,runner_request_for(stage,payload)[1]
    result=execute_story(fixture_path=FIXTURE,api_key='synthetic',preflight=prepare(FIXTURE),output=tmp_path/'run',call_fn=fake)
    from scripts.spineforge_relay_story_replay import verify_story
    proof=verify_story(tmp_path/'run',FIXTURE)
    if bad_reference:
        assert result['status']=='REJECT_NON_CONVERGENT' and result['reason']=='FAILED_CLOSED_NO_RETRY'
        assert len(calls)==2 and proof['final_revision']==0
    else:
        assert result['status']=='ACCEPT' and len(calls)==12
        assert proof['final_revision']==6


def test_saved_span_preflight_is_current_without_paid_authority():
    from src.spineforge_span_paid_entry import prepare_reserved_story
    root=Path('evidence/spineforge-relay/SFR-V1-Q12-PREFLIGHT-20261008')
    assert json.loads((root/'preflight.json').read_text())==prepare_reserved_story(FIXTURE)
    assert json.loads((root/'proposal.json').read_text())['paid_execution_authorized'] is False
