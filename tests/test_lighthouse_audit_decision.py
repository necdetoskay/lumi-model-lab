import json
from pathlib import Path
import pytest
from src.lighthouse_audit_decision import decision, IDS
from src.spineforge_v20_story_audit_artifact import _segment_story

LEDGER=Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-04-20261005')


def segments(story):
    return [{'span_id':r['id'],'repaired_text':r['text']} for r in _segment_story(story)]


def empty(rows):
    return {'requirement_checks':[{'requirement_id':i,'span_ids':[rows[1]['span_id']],
        'exact_text':rows[1]['repaired_text'],'reason':'Synthetic verified requirement',
        'repair_span_ids':[],'assessment':'SATISFIED'} for i in IDS], 'observations':[], 'summary':'test'}


@pytest.mark.parametrize('call_index,kind',[(11,'ADVISORY'),(13,'VERIFIED'),(15,'ADVISORY'),(17,'ADVISORY'),(19,'VERIFIED')])
def test_recorded_nondefects_cannot_dispatch_repairs(call_index,kind):
    row=json.loads((LEDGER/'calls.json').read_text())[call_index];old=row['response']['findings'][0]
    assert old['severity']=='moderate' and old['repair_scope']=='SCENE_REPAIR'
    rows=segments(row['input']['full_story']);response=empty(rows)
    response['observations']=[{'family':old['family'],'span_ids':old['span_ids'],'exact_text':'',
        'reason':old['reason'],'material_impact':'','classification':kind}]
    result=decision(response,rows);assert result['status']=='ACCEPT' and result['findings']==[]


def defect_case():
    old=json.loads(Path('evidence/lighthouse-editorial/independent-review-03.json').read_text())['findings'][0]
    story=Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-03-20261005/accepted-story.txt').read_text()
    rows=segments(story);response=empty(rows);response['requirement_checks'][0].update(
        span_ids=old['span_ids'],exact_text=old['exact_text'],reason=old['reason'],
        repair_span_ids=old['span_ids'],assessment='MATERIAL_VIOLATION')
    return response,rows


def test_actual_plan_violation_still_requires_repair():
    response,rows=defect_case();result=decision(response,rows)
    assert result['status']=='REPAIR' and result['findings'][0]['span_ids']==['S054','S060','S061','S183']


@pytest.mark.parametrize('change',['quote','unknown_span','unknown_repair_span','missing_requirement','duplicate_requirement','uncertain','missing_evidence','duplicate_span'])
def test_invalid_or_uncertain_audit_cannot_silently_accept_or_repair(change):
    response,rows=defect_case();r=response['requirement_checks'][0]
    if change=='quote':r['exact_text']='invented quotation'
    if change=='unknown_span':r['span_ids']=['S999']
    if change=='unknown_repair_span':r['repair_span_ids']=['S999']
    if change=='missing_requirement':response['requirement_checks'].pop()
    if change=='duplicate_requirement':response['requirement_checks'][1]['requirement_id']=r['requirement_id']
    if change=='uncertain':r['assessment']='UNCERTAIN'
    if change=='missing_evidence':r['exact_text']=''
    if change=='duplicate_span':r['span_ids'].append(r['span_ids'][0])
    with pytest.raises(RuntimeError):decision(response,rows)


def test_withdrawn_observation_cannot_trigger_repair():
    response,rows=defect_case();response=empty(rows)
    response['observations']=[{'family':'closure_integrity','span_ids':['S197'],'exact_text':'',
        'reason':'No defect found; this entry is withdrawn.','material_impact':'none','classification':'VERIFIED'}]
    assert decision(response,rows)['status']=='ACCEPT'


def test_additional_actual_defect_still_blocks():
    response,rows=defect_case();response=empty(rows)
    response['observations']=[{'family':'state_continuity','span_ids':[rows[1]['span_id']],
        'exact_text':rows[1]['repaired_text'],'reason':'Synthetic contradiction with material consequence',
        'material_impact':'Makes the rescue impossible','classification':'DEFECT_SCENE'}]
    assert decision(response,rows)['status']=='REPAIR'
