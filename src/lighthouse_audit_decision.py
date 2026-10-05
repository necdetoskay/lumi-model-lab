"""Evidence precedes classification; all binding plan requirements are checked."""
from pathlib import Path
from src.spineforge_v21_model_adapter import FINDING_SCHEMA, validate_schema, _call
from src.lighthouse_audit_requirements import requirements

PROMPT=Path('prompts/lighthouse_decision_audit.md')
IDS=['ENTRY_ROUTE','ACTUAL_FINAL_IMAGE','MOTHER_LIMITS','IRREVERSIBLE_LOSS','RESCUE_ACTION','SAME_RETURN_ROUTE']
SPAN_IDS={'type':'array','maxItems':24,'uniqueItems':True,'items':{'type':'string','maxLength':16}}
# Classification is generated after evidence and reasoning, avoiding an early defect commitment.
CHECK={'type':'object','additionalProperties':False,
       'required':['requirement_id','span_ids','exact_text','reason','repair_span_ids','assessment'],
       'properties':{'requirement_id':{'type':'string','enum':IDS},'span_ids':SPAN_IDS,
           'exact_text':{'type':'string','maxLength':1200},'reason':{'type':'string','minLength':1,'maxLength':2000},
           'repair_span_ids':SPAN_IDS,'assessment':{'type':'string','enum':['SATISFIED','MATERIAL_VIOLATION','UNCERTAIN']}}}
OBSERVATION={'type':'object','additionalProperties':False,
       'required':['family','span_ids','exact_text','reason','material_impact','classification'],
       'properties':{'family':FINDING_SCHEMA['properties']['family'],'span_ids':SPAN_IDS,
           'exact_text':{'type':'string','maxLength':1200},'reason':{'type':'string','minLength':1,'maxLength':2000},
           'material_impact':{'type':'string','maxLength':1200},
           'classification':{'type':'string','enum':['DEFECT_SCENE','DEFECT_STRUCTURAL','DEFECT_REPLAN','ADVISORY','VERIFIED']}}}
SCHEMA={'type':'object','additionalProperties':False,'required':['requirement_checks','observations','summary'],
        'properties':{'requirement_checks':{'type':'array','minItems':6,'maxItems':6,'items':CHECK},
            'observations':{'type':'array','maxItems':16,'items':OBSERVATION},
            'summary':{'type':'string','maxLength':1500}}}


def decision(response,segments,plan=None):
    validate_schema({k:response[k] for k in SCHEMA['properties']},SCHEMA)
    rows={r['span_id']:r.get('repaired_text',r.get('text')) for r in segments}
    if len(rows)!=len(segments):raise RuntimeError('Duplicate source span IDs')
    checks=response['requirement_checks']
    if sorted(x['requirement_id'] for x in checks)!=sorted(IDS):raise RuntimeError('Missing or duplicate requirement check')
    if plan is None:
        from src.lighthouse_experiment import approved_input
        plan=approved_input()
    req={x['id']:x for x in requirements(plan)}
    findings=[];advisory=[];verified=[];uncertain=[]
    def grounded(row,ids=None,mandatory=False):
        ids=row['span_ids'] if ids is None else ids
        if len(set(ids))!=len(ids) or any(s not in rows for s in ids):raise RuntimeError('Invalid audit span IDs')
        quote=row['exact_text']
        if quote and not any(quote in rows[s] for s in row['span_ids']):raise RuntimeError('Audit quote not found in cited spans')
        if mandatory and (not ids or not quote):raise RuntimeError('Material violation needs exact source evidence and repair spans')
    for row in checks:
        grounded(row,mandatory=True);grounded(row,row['repair_span_ids'])
        note={'span_ids':row['span_ids'],'note':row['reason']}
        if row['assessment']=='MATERIAL_VIOLATION':
            grounded(row,row['repair_span_ids'],True)
            findings.append({'family':req[row['requirement_id']]['family'],'severity':'moderate',
                'repair_scope':'SCENE_REPAIR','span_ids':row['repair_span_ids'],
                'exact_text':row['exact_text'],'reason':row['reason']})
        elif row['assessment']=='UNCERTAIN':uncertain.append(row['requirement_id'])
        else:verified.append(note)
    for row in response['observations']:
        grounded(row);kind=row['classification'];note={'span_ids':row['span_ids'],'note':row['reason']}
        if kind.startswith('DEFECT_'):
            grounded(row,mandatory=True)
            if not row['material_impact'].strip() or row['material_impact'].strip().lower() in {'none','n/a'}:
                raise RuntimeError('Defect without material impact')
            findings.append({'family':row['family'],'severity':'moderate',
                'repair_scope':{'DEFECT_SCENE':'SCENE_REPAIR','DEFECT_STRUCTURAL':'STRUCTURAL_REPAIR','DEFECT_REPLAN':'REPLAN'}[kind],
                'span_ids':row['span_ids'],'exact_text':row['exact_text'],'reason':row['reason']})
        elif kind=='ADVISORY':advisory.append(note)
        else:verified.append(note)
    if uncertain:raise RuntimeError('Unresolved requirement assessments: '+','.join(uncertain))
    return {'status':'REPAIR' if findings else 'ACCEPT','findings':findings,
            'advisory_notes':advisory,'verified_requirements':verified}


def call_audit(api_key,payload):
    data={**payload,'binding_requirements':requirements(payload['approved_plan'])}
    return _call(api_key=api_key,payload=data,prompt_path=PROMPT,
        request_class='spineforge_v21_initial_blocking_audit',schema_name='lighthouse_audit_decision_v3',
        schema=SCHEMA,max_tokens=3500,stage='AUDIT')
