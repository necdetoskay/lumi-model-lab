"""Bound semantic effect extraction; deterministic agreement with projected state.

No prose parsing heuristic or automatic state mutation. Extraction completeness
is a semantic judgment, not a deterministic proof that every effect was found.
"""
import json
from typing import Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel,ValidationFinding,canonical_sha256
from src.spineforge_production_source_ranges import RangeGuardV1
from src.spineforge_production_compact_ranges import range_table,resolve_range_guard,strict_range_schema
from src.spineforge_relay_v1_q6 import _expected_advance
from src.spineforge_state_fidelity import audit_state_fidelity

class ObservedEffectV1(StrictModel):
    field_id: str=Field(min_length=1)
    observed_value_json: str=Field(min_length=1)
    source_range_id: str=Field(min_length=1)

class EffectAuditV1(StrictModel):
    audit_id: str=Field(pattern=r'^[0-9a-f]{64}$')
    status: Literal['COMPLETE','INCOMPLETE']
    observed_effects: list[ObservedEffectV1]

class EffectGuardV1(RangeGuardV1):
    state_effect_audit: EffectAuditV1

def effect_context(state,contract):
    before=state.model_dump(mode='json');after=_expected_advance(state,contract).model_dump(mode='json')
    fields=[]
    def walk(a,b,path,present=True):
        if isinstance(a,dict) and isinstance(b,dict) and (a or b):
            for key in sorted(set(a)|set(b)):
                walk(a.get(key),b.get(key),path+'/'+key.replace('~','~0').replace('/','~1'),key in b)
        else:
            fields.append([f'F{len(fields):04}',path,b,present])
    for key in ['characters','objects','world']:walk(before[key],after[key],'/'+key)
    value=dict(schema='spineforge.state-effect-context.v1',state_sha256=canonical_sha256(state),contract_sha256=canonical_sha256(contract),field_columns=['id','pointer','projected_after','projected_present'],fields=fields)
    return {**value,'audit_id':canonical_sha256(value)}

def effect_schema(table,context):
    schema=EffectGuardV1.model_json_schema()
    def strict(node):
        if isinstance(node,dict):
            node.pop('default',None)
            if node.get('type')=='object':node['required']=list(node.get('properties',{}))
            for v in node.values():strict(v)
        elif isinstance(node,list):
            for v in node:strict(v)
    strict(schema)
    original=strict_range_schema(table)
    schema['$defs'].update(original['$defs'])
    schema['properties']['source_sha256']=original['properties']['source_sha256']
    schema['$defs']['EffectAuditV1']['properties']['audit_id']['enum']=[context['audit_id']]
    schema['$defs']['ObservedEffectV1']['properties']['field_id']['enum']=[r[0] for r in context['fields']]
    schema['$defs']['ObservedEffectV1']['properties']['source_range_id']={'$ref':'#/$defs/SourceRangeId'}
    return schema

def _json(value):
    def invalid(token):raise ValueError('Non-finite JSON value')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate effect value key')
            result[k]=v
        return result
    parsed=json.loads(value,parse_constant=invalid,object_pairs_hook=pairs)
    json.dumps(parsed,allow_nan=False)  # Also reject overflowing exponents.
    return parsed

def resolve_effect_guard(raw,prose,context):
    guard=EffectGuardV1.model_validate(raw)
    if guard.state_effect_audit.audit_id!=context['audit_id']:raise ValueError('Stale effect audit')
    base=guard.model_dump(mode='json');audit=base.pop('state_effect_audit')
    report=resolve_range_guard(base,prose)
    table=range_table(prose);choices={r[0]:r[1:] for r in table['ranges']};fields={r[0]:r for r in context['fields']}
    findings=[];seen=set();resolved=[];observations=[]
    projected={}
    for _,pointer,value,present in context['fields']:
        if not present:continue
        tokens=[s.replace('~1','/').replace('~0','~') for s in pointer[1:].split('/')]
        node=projected
        for token in tokens[:-1]:node=node.setdefault(token,{})
        node[tokens[-1]]=value
    if audit['status']!='COMPLETE':findings.append(ValidationFinding(code='STATE_EFFECT_SCAN_INCOMPLETE',family='contract',severity='BLOCKING',message='Semantic state-effect scan was not completed'))
    for effect in guard.state_effect_audit.observed_effects:
        if effect.field_id not in fields or effect.source_range_id not in choices:raise ValueError('Unknown effect field/source range')
        if effect.field_id in seen:raise ValueError('Duplicate terminal effect field')
        seen.add(effect.field_id)
        field=fields[effect.field_id];first,last=choices[effect.source_range_id]
        quote=prose[table['units'][first][0]:table['units'][last][1]]
        observed=_json(effect.observed_value_json)
        observations.append(dict(state_pointer=field[1],observed_value=observed,source_range_id=effect.source_range_id))
        resolved.append(dict(field_id=effect.field_id,path=field[1],observed=observed,projected_after=field[2],projected_present=field[3],exact_text=quote))
    fidelity=audit_state_fidelity(prose=prose,state=projected,review=dict(schema_name='spineforge.state-fidelity-review.v1',source_sha256=table['source_sha256'],state_sha256=canonical_sha256(projected),reviewer='Scene guard terminal-effect observations',observations=observations))
    mismatches={f['state_pointer'] for f in fidelity['findings']}
    for row in resolved:
        row['matches']=row['path'] not in mismatches
        if not row['matches']:
            expected=json.dumps(row['projected_after'],ensure_ascii=False) if row['projected_present'] else 'MISSING FIELD'
            findings.append(ValidationFinding(code='PROSE_STATE_EFFECT_MISMATCH',family='contract',severity='BLOCKING',message=f"{row['path']}: observed {json.dumps(row['observed'],ensure_ascii=False)} conflicts with projected scene exit {expected}; rewrite prose to the contract, do not invent state changes",evidence=[row['exact_text']]))
    return report,findings,dict(audit_id=context['audit_id'],status=audit['status'],effects=resolved,fidelity_audit=fidelity,semantic_extraction_not_completeness_proof=True)
