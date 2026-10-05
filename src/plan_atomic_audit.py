"""Deterministic sentence/clause projection, retaining source offsets and context."""
import re
from src.plan_audit_contract import compile_contract, digest
from src.plan_audit_decision import decision as route


def compile_atomic_contract(plan, approved_plan_sha256):
    parent = compile_contract(plan, approved_plan_sha256)
    requirements = []
    for row in parent['requirements']:
        if not row['id'].startswith('SCENE_'):
            requirements.append(row)
            continue
        source = row['source_quote']
        cursor = 0
        boundaries = [m.end() for m in re.finditer(r'(?<=[.;?!])\s+', source)] + [len(source)]
        for index, end in enumerate(boundaries, 1):
            # Keep original punctuation, line breaks, and delimiter whitespace.
            quote = source[cursor:end]
            requirements.append({**row, 'id': row['id'] + f'_C{index:02}',
                'source_quote': quote, 'parent_requirement_id': row['id'],
                'source_quote_start': cursor, 'source_quote_end': end,
                'parent_source_quote': source})
            cursor = end
    contract = {**parent, 'schema': 'approved-plan-atomic-audit-contract.v1',
                'parent_contract_sha256': parent['contract_sha256'],
                'derivation': 'DETERMINISTIC_LOSSLESS_PUNCTUATION_SPLIT',
                'requirements': requirements}
    contract.pop('contract_sha256')
    return {**contract, 'contract_sha256': digest(contract)}


def validate_atomic_contract(contract, plan, approved_plan_sha256):
    expected = compile_atomic_contract(plan, approved_plan_sha256)
    if contract != expected:
        raise ValueError('Atomic audit contract or source binding drift')
    return expected


def decision(response, segments, contract, plan, approved_plan_sha256):
    return route(response, segments, contract, plan, approved_plan_sha256,
                 contract_validator=validate_atomic_contract)
