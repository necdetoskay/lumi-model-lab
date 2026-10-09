"""Code-owned contiguous evidence choices; historical span-list protocol is frozen."""
from typing import Literal
from pydantic import Field, create_model
from src.spineforge_relay_v1_contracts import StrictModel
from src.spineforge_relay_v1_events import PredicateEvidenceV1
from src.spineforge_relay_v1_guard import SemanticGuardFindingV1
from src.spineforge_relay_v1_q5t import StructuredGuardV1
from src.spineforge_source_spans import source_table

def referenced(name,model):
    fields={k:(v.annotation,v) for k,v in model.model_fields.items() if k!='exact_text'}
    fields['source_range_id']=(str,Field(min_length=1))
    return create_model(name,__base__=StrictModel,**fields)

RangePredicateV1=referenced('RangePredicateV1',PredicateEvidenceV1)
RangeFindingV1=referenced('RangeFindingV1',SemanticGuardFindingV1)

class RangeResidualV1(StrictModel):
    schema_name: Literal['spineforge-relay.semantic-guard.v1']
    decision: Literal['PASS','REWRITE']
    findings: list[RangeFindingV1]
    summary: str=Field(min_length=1)

class RangeGuardV1(StrictModel):
    source_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    event_evidence: list[RangePredicateV1]
    residual: RangeResidualV1

def range_table(prose):
    table=source_table(prose)
    choices=[]
    for first in range(len(table['spans'])):
        for last in range(first,min(first+8,len(table['spans']))):
            choices.append([f'R{len(choices):04}',first,last])
    return {**table,'schema':'spineforge.source-ranges.v1',
            'range_columns':['id','first_unit_index','last_unit_index_inclusive'],'ranges':choices}

def resolve_range_guard(raw,prose,table=None):
    expected=range_table(prose)
    if table is not None and table!=expected: raise ValueError('Source range table drift')
    guard=RangeGuardV1.model_validate(raw)
    if guard.source_sha256!=expected['source_sha256']: raise ValueError('Stale source range binding')
    choices={row[0]:row[1:] for row in expected['ranges']}
    def resolve(row):
        data=row.model_dump(mode='json');choice=choices.get(data.pop('source_range_id'))
        if choice is None: raise ValueError('Unknown source range')
        first,last=choice;units=expected['spans']
        data['exact_text']=prose[units[first]['start']:units[last]['end']]
        return data
    residual=guard.residual.model_dump(mode='json')
    residual['findings']=[resolve(row) for row in guard.residual.findings]
    return StructuredGuardV1.model_validate(dict(event_evidence=[resolve(row) for row in guard.event_evidence],residual=residual))

def strict_range_schema(table):
    schema=RangeGuardV1.model_json_schema()
    def strict(node):
        if isinstance(node,dict):
            node.pop('default',None)
            if node.get('type')=='object':node['required']=list(node.get('properties',{}))
            for value in node.values():strict(value)
        elif isinstance(node,list):
            for value in node:strict(value)
    strict(schema)
    schema['properties']['source_sha256']['enum']=[table['source_sha256']]
    ids=[row[0] for row in table['ranges']]
    for name in ('RangePredicateV1','RangeFindingV1'):
        schema['$defs'][name]['properties']['source_range_id']={'type':'string','enum':ids}
    return schema
