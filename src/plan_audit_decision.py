"""Dynamic audit schema/routing prototype; no paid execution entry point."""
from copy import deepcopy
from src.lighthouse_audit_decision import CHECK, OBSERVATION
from src.plan_audit_contract import validate_contract
from src.spineforge_v21_model_adapter import validate_schema


def audit_schema(contract):
    ids = [row['id'] for row in contract['requirements']]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Invalid contract requirement IDs')
    check = deepcopy(CHECK)
    check['properties']['requirement_id']['enum'] = ids
    return {'type': 'object', 'additionalProperties': False,
            'required': ['requirement_checks', 'observations', 'summary'],
            'properties': {
                'requirement_checks': {'type': 'array', 'minItems': len(ids),
                                       'maxItems': len(ids), 'items': check},
                'observations': {'type': 'array', 'maxItems': 16,
                                 'items': deepcopy(OBSERVATION)},
                'summary': {'type': 'string', 'maxLength': 1500}}}


def decision(response, segments, contract, plan, approved_plan_sha256):
    validate_contract(contract, plan, approved_plan_sha256)
    validate_schema(response, audit_schema(contract))
    text = {}
    for segment in segments:
        key = segment['span_id']
        value = segment.get('repaired_text', segment.get('text'))
        if key in text or not isinstance(value, str):
            raise RuntimeError('Duplicate span or invalid source text')
        text[key] = value
    requirements = {row['id']: row for row in contract['requirements']}
    checks = response['requirement_checks']
    if sorted(row['requirement_id'] for row in checks) != sorted(requirements):
        raise RuntimeError('Missing or duplicate requirement check')

    def evidence(row, mandatory=False):
        ids, quote = row['span_ids'], row['exact_text']
        if len(set(ids)) != len(ids) or any(key not in text for key in ids):
            raise RuntimeError('Invalid evidence span IDs')
        if quote and not any(quote in text[key] for key in ids):
            raise RuntimeError('Quote absent from cited source spans')
        if mandatory and (not ids or not quote):
            raise RuntimeError('Missing exact source evidence')

    findings, advisory, verified, uncertain = [], [], [], []
    for row in checks:
        evidence(row, mandatory=row['assessment'] != 'UNCERTAIN')
        repair = row['repair_span_ids']
        if len(set(repair)) != len(repair) or any(key not in text for key in repair):
            raise RuntimeError('Invalid repair span IDs')
        if row['assessment'] != 'MATERIAL_VIOLATION' and repair:
            raise RuntimeError('Non-defect cannot authorize repair spans')
        note = {'requirement_id': row['requirement_id'],
                'span_ids': row['span_ids'], 'note': row['reason']}
        if row['assessment'] == 'UNCERTAIN':
            uncertain.append(row['requirement_id'])
        elif row['assessment'] == 'SATISFIED':
            verified.append(note)
        else:
            if not repair:
                raise RuntimeError('Violation without bounded repair scope')
            findings.append({'family': requirements[row['requirement_id']]['family'],
                             'severity': 'moderate', 'repair_scope': 'SCENE_REPAIR',
                             'span_ids': repair, 'exact_text': row['exact_text'],
                             'reason': row['reason']})
    for row in response['observations']:
        kind = row['classification']
        evidence(row, mandatory=kind.startswith('DEFECT_'))
        note = {'span_ids': row['span_ids'], 'note': row['reason']}
        if kind.startswith('DEFECT_'):
            if row['material_impact'].strip().lower() in {'', 'none', 'n/a'}:
                raise RuntimeError('Defect without material impact')
            findings.append({'family': row['family'], 'severity': 'moderate',
                             'repair_scope': {'DEFECT_SCENE': 'SCENE_REPAIR',
                                              'DEFECT_STRUCTURAL': 'STRUCTURAL_REPAIR',
                                              'DEFECT_REPLAN': 'REPLAN'}[kind],
                             'span_ids': row['span_ids'], 'exact_text': row['exact_text'],
                             'reason': row['reason']})
        elif kind == 'ADVISORY':
            advisory.append(note)
        else:
            verified.append(note)
    return {'status': 'UNRESOLVED' if uncertain else 'REPAIR' if findings else 'ACCEPT',
            'findings': [] if uncertain else findings, 'advisory_notes': advisory,
            'verified_requirements': verified, 'unresolved_requirements': uncertain,
            'contract_sha256': contract['contract_sha256']}
