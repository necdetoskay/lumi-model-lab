"""Evidence-grounded verdict separated from prior per-requirement model labels."""
from copy import deepcopy
import hashlib
from src.spineforge_v21_model_adapter import FINDING_SCHEMA, validate_schema

finding = deepcopy(FINDING_SCHEMA)
finding['properties']['reason']['maxLength'] = 2000
finding['properties']['repair_scope']['enum'] = ['SCENE_REPAIR']
finding['properties']['span_ids']['uniqueItems'] = True
SCHEMA = {'type':'object','additionalProperties':False,
    'required':['findings','advisory_notes','unresolved_material_issues','summary'],
    'properties':{'findings':{'type':'array','maxItems':16,'items':finding},
        'advisory_notes':{'type':'array','maxItems':16,'items':{'type':'string','maxLength':1000}},
        'unresolved_material_issues':{'type':'array','maxItems':16,'items':{'type':'string','maxLength':1000}},
        'summary':{'type':'string','maxLength':1000}}}


def adjudication_payload(data, contract, prior=None):
    # Parent context is already present at each exact source_pointer in approved_plan.
    requirements=[{k:v for k,v in r.items() if k!='parent_source_quote'} for r in contract['requirements']]
    output={**data,'source_requirements':requirements,'contract_sha256':contract['contract_sha256']}
    if prior is not None:
        if (prior['input']['full_story']!=data['full_story']
                or prior['input']['source_story_sha256']!=data['source_story_sha256']
                or prior['input']['audit_contract']!=contract
                or prior['input']['approved_plan']!=data['approved_plan']):
            raise RuntimeError('Candidate audit notes are not bound to current source')
        response=prior['response']
        output['candidate_evidence']=[{k:r[k] for k in ('requirement_id','span_ids','exact_text','reason')}
                                      for r in response['requirement_checks']]
        output['candidate_observations']=[{k:r[k] for k in ('family','span_ids','exact_text','reason')}
                                         for r in response['observations']]
    return output


def decision(response, segments):
    validate_schema(response,SCHEMA)
    text={r['span_id']:r.get('repaired_text',r.get('text')) for r in segments}
    if len(text)!=len(segments): raise RuntimeError('Duplicate source spans')
    for f in response['findings']:
        ids=f['span_ids'];quote=f['exact_text']
        if any(s not in text for s in ids) or len(set(ids))!=len(ids): raise RuntimeError('Unknown or duplicate repair span')
        if not quote or not any(quote in text[s] for s in ids): raise RuntimeError('Material evidence absent from repair scope')
        if not f['reason'].strip(): raise RuntimeError('Missing material causal reason')
    unresolved=response['unresolved_material_issues']
    return {'status':'UNRESOLVED' if unresolved else 'REPAIR' if response['findings'] else 'ACCEPT',
            'findings':[] if unresolved else response['findings'],
            'advisory_notes':response['advisory_notes'],'unresolved_material_issues':unresolved}
