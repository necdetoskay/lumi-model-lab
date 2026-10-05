"""Typed audit channels: only grounded material defects may trigger story edits."""
from copy import deepcopy
from pathlib import Path
from src.spineforge_v21_model_adapter import FINDING_SCHEMA, validate_schema, _call
from src.spineforge_v21_bounded_quality import BLOCKING_FAMILIES, split_findings

PROMPT = Path('prompts/lighthouse_decision_audit.md')
DEFECT = deepcopy(FINDING_SCHEMA)
DEFECT['properties']['family']['enum'] = sorted(BLOCKING_FAMILIES)
DEFECT['properties']['severity']['enum'] = ['moderate', 'serious', 'critical']
DEFECT['properties']['repair_scope']['enum'] = ['SCENE_REPAIR','STRUCTURAL_REPAIR','REPLAN']
DEFECT['properties']['exact_text']['minLength'] = 1
DEFECT['properties']['reason']['minLength'] = 1
DEFECT['properties']['reason']['maxLength'] = 2000
for field in ['broken_requirement', 'material_impact']:
    DEFECT['required'].append(field)
    DEFECT['properties'][field] = {'type':'string','minLength':1,'maxLength':1200}
NOTE = {'type':'object','additionalProperties':False,'required':['span_ids','note'],
        'properties':{'span_ids':{'type':'array','maxItems':24,'uniqueItems':True,
            'items':{'type':'string','maxLength':16}},'note':{'type':'string','minLength':1,'maxLength':1500}}}
SCHEMA = {'type':'object','additionalProperties':False,
    'required':['blocking_findings','advisory_notes','verified_requirements','summary'],
    'properties':{'blocking_findings':{'type':'array','maxItems':24,'items':DEFECT},
        'advisory_notes':{'type':'array','maxItems':16,'items':NOTE},
        'verified_requirements':{'type':'array','maxItems':16,'items':NOTE},
        'summary':{'type':'string','maxLength':1500}}}


def decision(response, segments):
    """Reject ungrounded outputs; never infer materiality from keywords in prose."""
    validate_schema({k:response[k] for k in SCHEMA['properties']},SCHEMA)
    rows={r['span_id']:r.get('repaired_text',r.get('text')) for r in segments}
    if len(rows)!=len(segments):raise RuntimeError('Duplicate source span IDs')
    for channel in ['blocking_findings','advisory_notes','verified_requirements']:
        for row in response[channel]:
            if len(set(row['span_ids']))!=len(row['span_ids']):raise RuntimeError('Duplicate audit span IDs')
            if any(s not in rows for s in row['span_ids']):raise RuntimeError('Audit references unknown span')
            if channel=='blocking_findings' and not any(row['exact_text'] in rows[s] for s in row['span_ids']):
                raise RuntimeError('Blocking quote not found in cited spans')
    findings=[{k:r[k] for k in FINDING_SCHEMA['properties']} for r in response['blocking_findings']]
    blocking,_=split_findings(findings)
    if len(blocking)!=len(findings):raise RuntimeError('Non-blocking record in defect channel')
    return {'status':'REPAIR' if findings else 'ACCEPT','findings':findings,
        'advisory_notes':response['advisory_notes'],'verified_requirements':response['verified_requirements']}


def call_audit(api_key,payload):
    return _call(api_key=api_key,payload=payload,prompt_path=PROMPT,
        request_class='spineforge_v21_initial_blocking_audit',schema_name='lighthouse_audit_decision_v2',
        schema=SCHEMA,max_tokens=3500,stage='AUDIT')
