import copy
import json
from pathlib import Path
import pytest
from src.audit_citation_projection import project_citations,grounded_decision
from src.lighthouse_experiment import approved_input


def fixture():
    root=Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-READ-AUDIT-01-20261005')
    c=json.loads((root/'calls.json').read_text())[0]
    return c['response'],c['input']['story_segments']


def test_recorded_neighbor_citation_is_projected_without_changing_defects():
    response,rows=fixture();original=copy.deepcopy(response)
    projected,changes=project_citations(response,rows)
    assert response==original and len(changes)==1 and changes[0]['added_span_id']=='S109'
    assert projected['requirement_checks'][1]==response['requirement_checks'][1]
    assert projected['requirement_checks'][2]['assessment']=='SATISFIED'
    d,c=grounded_decision(response,rows,approved_input())
    assert d['status']=='REPAIR' and len(d['findings'])==1


@pytest.mark.parametrize('kind',['MATERIAL_VIOLATION','UNCERTAIN'])
def test_material_or_uncertain_target_is_never_relocated(kind):
    r,rows=fixture();r['requirement_checks'][2]['assessment']=kind
    with pytest.raises(RuntimeError):project_citations(r,rows)


@pytest.mark.parametrize('change',['invented_quote','distant','unknown_id','duplicate_id','different_paragraph','ambiguous_quote'])
def test_unproven_citation_correction_is_rejected(change):
    r,rows=fixture();check=r['requirement_checks'][2]
    if change=='invented_quote':check['exact_text']='Invented evidence'
    if change=='distant':check['span_ids']=['S001']
    if change=='unknown_id':check['span_ids'].append('S999')
    if change=='duplicate_id':check['span_ids'].append(check['span_ids'][0])
    if change=='different_paragraph':next(x for x in rows if x['span_id']=='S109')['paragraph_id']='Different'
    if change=='ambiguous_quote':rows[0]['repaired_text']=check['exact_text']
    with pytest.raises(RuntimeError):project_citations(r,rows)


def test_valid_projection_is_idempotent():
    r,rows=fixture();r,_=project_citations(r,rows)
    again,fixes=project_citations(r,rows)
    assert again==r and fixes==[]
