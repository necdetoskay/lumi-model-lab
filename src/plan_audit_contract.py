"""Offline, lossless audit projection of an approved editorial plan.

This adapter supports the editorial plan field shape, not arbitrary Spine schemas.
It neither translates nor invents semantic assertions and cannot call an API.
"""
import hashlib
import json
import re

SCHEMA = 'approved-plan-audit-contract.v1'
GLOBAL_FIELDS = (
    ('mock_context', 'canon_integrity', 'PRESERVE_FACTS'),
    ('setting_and_hazards', 'spine_fidelity', 'PRESERVE_FACTS'),
    ('preserved_outcomes', 'spine_fidelity', 'PRESERVE_OUTCOMES'),
    ('approved_clarifications', 'spine_fidelity', 'PRESERVE_OUTCOMES'),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing nonempty source: ' + name)
    return value


def compile_contract(plan, approved_plan_sha256):
    """Caller supplies the immutable handoff hash AFTER upstream plan approval.

    A matching digest proves binding, not user approval. Upstream remains responsible
    for verifying approval against its original source; this compiler grants none.
    """
    if digest(plan) != approved_plan_sha256:
        raise ValueError('Approved plan fingerprint drift')
    age = plan.get('reader_age')
    if isinstance(age, bool) or not isinstance(age, int) or age < 1:
        raise ValueError('Invalid reader age')
    nonempty(plan.get('output_language'), 'output_language')
    minimum = plan.get('target_words', {}).get('min')
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError('Invalid minimum word count')
    if plan.get('length_policy') != 'MINIMUM_ONLY_NO_UPPER_WORD_LIMIT':
        raise ValueError('Unsupported length policy')
    scenes = plan.get('scenes')
    if not isinstance(scenes, list) or not scenes:
        raise ValueError('Missing approved scenes')
    rows = []

    def add(key, pointer, quote, family, obligation):
        rows.append({'id': key, 'source_pointer': pointer,
                     'source_quote': nonempty(quote, pointer),
                     'family': family, 'obligation': obligation})

    for field, family, obligation in GLOBAL_FIELDS:
        add('GLOBAL_' + field.upper(), '/' + field, plan.get(field), family, obligation)
    seen = set()
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise ValueError('Invalid scene object')
        scene_id = nonempty(scene.get('scene_id'), 'scene_id')
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}', scene_id) or scene_id in seen:
            raise ValueError('Invalid or duplicate scene ID')
        seen.add(scene_id)
        for field, suffix, obligation in (
                ('approved_action', 'ACTION', 'SHOW_APPROVED_ACTION'),
                ('required_end_state', 'END_STATE',
                 'ACTUAL_STORY_END' if index == len(scenes) - 1 else 'SCENE_END_STATE')):
            add('SCENE_' + scene_id + '_' + suffix, f'/scenes/{index}/{field}',
                scene.get(field), 'closure_integrity' if obligation == 'ACTUAL_STORY_END'
                else 'spine_fidelity', obligation)
    contract = {
        'schema': SCHEMA, 'approved_plan_sha256': approved_plan_sha256,
        'derivation': 'DETERMINISTIC_EXACT_SOURCE_PROJECTION',
        'reader_age': age, 'output_language': plan['output_language'],
        'length_policy': {'min_words': minimum, 'max_words': None},
        'requirements': rows,
        'reader_guidance': {'source_pointer': '/reader_promise',
                            'source_quote': nonempty(plan.get('reader_promise'), 'reader_promise')},
        'scene_order': [scene['scene_id'] for scene in scenes],
        'upstream_approval_required': True,
        'paid_execution_authorized': False,
        'production_write_authorized': False,
    }
    return {**contract, 'contract_sha256': digest(contract)}


def validate_contract(contract, plan, approved_plan_sha256):
    expected = compile_contract(plan, approved_plan_sha256)
    if contract != expected:
        raise ValueError('Audit contract content or source binding drift')
    return expected
