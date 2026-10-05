import json
from copy import deepcopy
from pathlib import Path
import pytest
from src.lighthouse_audit_decision import decision
from src.spineforge_v20_story_audit_artifact import _segment_story

LEDGER=Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-04-20261005')


def segments(story):
    return [{'span_id':r['id'],'repaired_text':r['text']} for r in _segment_story(story)]


def empty():
    return {'blocking_findings':[], 'advisory_notes':[], 'verified_requirements':[], 'summary':'test'}


@pytest.mark.parametrize('call_index,channel',[(11,'advisory_notes'),(13,'verified_requirements'),(15,'advisory_notes'),(17,'advisory_notes'),(19,'verified_requirements')])
def test_recorded_nondefects_cannot_dispatch_repairs(call_index,channel):
    # Editorially labelled regression fixtures, not automatic legacy-text classification.
    row=json.loads((LEDGER/'calls.json').read_text())[call_index]
    old=row['response']['findings'][0]
    assert old['severity']=='moderate' and old['repair_scope']=='SCENE_REPAIR'
    response=empty();response[channel]=[{'span_ids':old['span_ids'],'note':old['reason']}]
    result=decision(response,segments(row['input']['full_story']))
    assert result['status']=='ACCEPT' and result['findings']==[]


def defect_case():
    root=Path('evidence/lighthouse-editorial/independent-review-03.json')
    old=json.loads(root.read_text())['findings'][0]
    old.update(broken_requirement='Upper door leads directly into the dry upper room.',
               material_impact='An extra tower ascent changes the approved entry and exit route.')
    response=empty();response['blocking_findings']=[old]
    story=Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-03-20261005/accepted-story.txt').read_text()
    return response,segments(story)


def test_actual_plan_violation_still_requires_repair():
    response,rows=defect_case()
    result=decision(response,rows)
    assert result['status']=='REPAIR' and result['findings'][0]['span_ids']==['S054','S060','S061','S183']


@pytest.mark.parametrize('change',['quote','unknown_span','no_repair','minor','missing_requirement','missing_impact','duplicate_span','note_with_severity'])
def test_invalid_audit_must_not_silently_accept_or_repair(change):
    response,rows=defect_case();r=response['blocking_findings'][0]
    if change=='quote':r['exact_text']='invented quotation'
    if change=='unknown_span':r['span_ids']=['S999']
    if change=='no_repair':r['repair_scope']='NO_REPAIR'
    if change=='minor':r['severity']='minor'
    if change=='missing_requirement':r.pop('broken_requirement')
    if change=='missing_impact':r.pop('material_impact')
    if change=='duplicate_span':r['span_ids'].append(r['span_ids'][0])
    if change=='note_with_severity':response['advisory_notes']=[{'span_ids':[], 'note':'test','severity':'moderate'}]
    with pytest.raises(RuntimeError):decision(response,rows)
