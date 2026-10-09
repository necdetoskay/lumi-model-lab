"""Lossless compact range table; frozen v1 evidence semantics remain unchanged."""
from src.spineforge_production_source_ranges import (
    range_table as original_table, resolve_range_guard as original_resolver,
    strict_range_schema as original_schema,
)

def range_table(prose):
    table=original_table(prose)
    return dict(schema='spineforge.source-ranges.v2',source_sha256=table['source_sha256'],
        offset_unit=table['offset_unit'],unit_columns=['start','end','text'],
        units=[[s['start'],s['end'],s['text']] for s in table['spans']],
        range_columns=table['range_columns'],ranges=table['ranges'])

def resolve_range_guard(raw,prose,table=None):
    if table is not None and table!=range_table(prose): raise ValueError('Compact source range table drift')
    return original_resolver(raw,prose)

def strict_range_schema(table):
    schema=original_schema(table)
    ids=[row[0] for row in table['ranges']]
    schema['$defs']['SourceRangeId']={'type':'string','enum':ids}
    for name in ('RangePredicateV1','RangeFindingV1'):
        schema['$defs'][name]['properties']['source_range_id']={'$ref':'#/$defs/SourceRangeId'}
    return schema
