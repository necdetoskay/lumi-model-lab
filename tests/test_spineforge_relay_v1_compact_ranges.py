import copy,json
from pathlib import Path
import pytest
from src.spineforge_production_compact_ranges import range_table,resolve_range_guard,strict_range_schema
from src.spineforge_production_source_ranges import range_table as old_table,resolve_range_guard as old_resolver
from tests.test_spineforge_relay_v1_source_ranges import raw
from scripts.spineforge_production_range_budget_audit import verify_story

def test_compaction_preserves_every_unit_choice_and_resolved_unicode_substring():
    prose='😀 Aya watched Mert’s hand. “Wait!”\nFirst. Second. Third. Fourth. Fifth. Sixth. Seventh. Eighth. Ninth.'
    before=old_table(prose);after=range_table(prose)
    assert before['source_sha256']==after['source_sha256'] and before['ranges']==after['ranges']
    assert after['units']==[[s['start'],s['end'],s['text']] for s in before['spans']]
    for row in after['ranges']:
        report=raw(prose,row[0])
        assert resolve_range_guard(report,prose,after)==old_resolver(report,prose)
    schema=strict_range_schema(after)
    assert schema['$defs']['SourceRangeId']['enum']==[r[0] for r in before['ranges']]
    for name in ('RangePredicateV1','RangeFindingV1'):
        assert schema['$defs'][name]['properties']['source_range_id']=={'$ref':'#/$defs/SourceRangeId'}
    assert len(json.dumps(after))<len(json.dumps(before))

@pytest.mark.parametrize('defect',['unknown','stale','offset','text','range','columns'])
def test_compact_binding_or_table_drift_fails_closed(defect):
    prose='First. Second.';table=range_table(prose);report=raw(prose)
    if defect=='unknown':report['event_evidence'][0]['source_range_id']='R9999'
    elif defect=='stale':report['source_sha256']='0'*64
    elif defect=='offset':table['units'][0][0]=1
    elif defect=='text':table['units'][0][2]='Changed'
    elif defect=='range':table['ranges'][0][1:]=[1,0]
    else:table['unit_columns'].reverse()
    with pytest.raises(ValueError):resolve_range_guard(report,prose,table)

def test_q19_original_budget_rejection_still_reproduces():
    root=Path('evidence/spineforge-relay/SFR-V1-Q19-SOURCE-RANGE-ROBOT-20261009')
    proof=verify_story(root/'story',root/'plan-1-fixture.json')
    assert proof['admission_failure']['planned_cost_usd']==.150578 and proof['final_revision']==4
    assert not (root/'story/S5_DecisionMove-1-guard-request.json').exists()
