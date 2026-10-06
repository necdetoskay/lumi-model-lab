"""Source-grounded audit with explicit coverage and separate evidence/repair scope.

These checks establish provenance and coverage, not semantic truth. Model quality must
still pass independent clean and flawed controls before any patch is authorized.
"""
from copy import deepcopy
from src.source_adjudication import SCHEMA as BASE_SCHEMA, decision as route
from src.spineforge_v21_model_adapter import validate_schema

SCHEMA = deepcopy(BASE_SCHEMA)
SCHEMA['required'].append('reviewed_requirements')
SCHEMA['properties']['reviewed_requirements'] = {
    'type': 'array', 'minItems': 1, 'maxItems': 256, 'uniqueItems': True,
    'items': {'type': 'integer', 'minimum': 1, 'maximum': 256}}
finding = SCHEMA['properties']['findings']['items']
finding['required'] += ['source_requirements', 'evidence']
finding['properties']['source_requirements'] = {
    'type': 'array', 'maxItems': 32, 'uniqueItems': True,
    'items': {'type': 'integer', 'minimum': 1, 'maximum': 256}}
finding['properties']['evidence'] = {
    'type': 'array', 'minItems': 1, 'maxItems': 24,
    'items': {'type': 'object', 'additionalProperties': False,
              'required': ['span_id', 'quote'],
              'properties': {'span_id': {'type': 'string', 'maxLength': 16},
                             'quote': {'type': 'string', 'minLength': 1, 'maxLength': 3000}}}}


def decision(response, segments, contract):
    validate_schema(response, SCHEMA)
    expected = set(range(1, len(contract['requirements']) + 1))
    reviewed = response['reviewed_requirements']
    if len(set(reviewed)) != len(reviewed) or set(reviewed) != expected:
        raise RuntimeError('Incomplete or unknown source requirement coverage')
    text = {r['span_id']: r.get('repaired_text', r.get('text')) for r in segments}
    for finding in response['findings']:
        refs = finding['source_requirements']
        if not set(refs) <= expected or len(refs) != len(set(refs)):
            raise RuntimeError('Unknown or duplicate source requirement')
        if finding['family'] == 'spine_fidelity' and not refs:
            raise RuntimeError('Plan deviation lacks a source requirement')
        witnesses = finding['evidence']
        keys = [(w['span_id'], w['quote']) for w in witnesses]
        if len(set(keys)) != len(keys):
            raise RuntimeError('Duplicate evidence witness')
        for w in witnesses:
            if w['span_id'] not in text or not w['quote'].strip() or w['quote'] not in text[w['span_id']]:
                raise RuntimeError('Evidence quote not found in its exact source span')
        if not any(w['span_id'] in finding['span_ids'] and finding['exact_text'] in w['quote'] for w in witnesses):
            raise RuntimeError('Repair target lacks a quoted evidence witness')
        # Internal contradictions require two states. A plan contradiction can use
        # one story state plus its indexed authoritative source requirement.
        if not refs and len(set(w['span_id'] for w in witnesses)) < 2:
            raise RuntimeError('Internal contradiction lacks two distinct source states')
    compatible = {k: deepcopy(response[k]) for k in BASE_SCHEMA['properties']}
    for finding in compatible['findings']:
        finding.pop('source_requirements')
        finding.pop('evidence')
    return route(compatible, segments)
