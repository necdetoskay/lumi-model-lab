from copy import deepcopy
import json
from pathlib import Path
import pytest
from src.lighthouse_experiment import approved_input
from src.plan_audit_contract import compile_contract, digest, validate_contract
from src.plan_audit_decision import audit_schema, decision


def fixture(count=3):
    return {'reader_age': 18, 'output_language': 'en',
            'target_words': {'min': 1400},
            'length_policy': 'MINIMUM_ONLY_NO_UPPER_WORD_LIMIT',
            'reader_promise': 'Adventure and exploration.',
            'mock_context': 'Nara has no magic. Her brother is alive.',
            'setting_and_hazards': 'The ship has one exit into the orchard.',
            'preserved_outcomes': 'The map is lost permanently.',
            'approved_clarifications': 'No substitute reward.',
            'scenes': [{'scene_id': f'BEAT{i}',
                        'approved_action': f'Nara performs action {i}.',
                        'required_end_state': f'Outcome {i}.'} for i in range(count)]}


def resolve(plan, pointer):
    value = plan
    for part in pointer.lstrip('/').split('/'):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


@pytest.mark.parametrize('count', [1, 3, 10])
def test_arbitrary_scene_count_ids_age_and_lossless_source_coverage(count):
    plan = fixture(count)
    contract = compile_contract(plan, digest(plan))
    assert len(contract['requirements']) == 4 + count * 2
    assert all(row['source_quote'] == resolve(plan, row['source_pointer'])
               for row in contract['requirements'])
    assert contract['reader_age'] == 18 and contract['length_policy']['max_words'] is None
    assert contract['requirements'][-1]['obligation'] == 'ACTUAL_STORY_END'
    assert contract == compile_contract(deepcopy(plan), digest(plan))


def test_real_approved_plan_projects_all_scene_actions_and_states_without_translation():
    plan = approved_input()
    contract = compile_contract(plan, digest(plan))
    assert len(contract['requirements']) == 16
    assert contract['requirements'][-1]['source_quote'] == plan['scenes'][-1]['required_end_state']
    assert 'Ekin' in contract['requirements'][-1]['source_quote']
    assert contract['paid_execution_authorized'] is False


@pytest.mark.parametrize('field', ['mock_context', 'setting_and_hazards', 'preserved_outcomes',
                                 'approved_clarifications', 'reader_promise'])
def test_missing_source_cannot_silently_reduce_audit_coverage(field):
    plan = fixture(); del plan[field]
    with pytest.raises(ValueError): compile_contract(plan, digest(plan))


@pytest.mark.parametrize('change', ['fact', 'action', 'end', 'age', 'order'])
def test_approved_fingerprint_invalidated_by_semantic_or_order_change(change):
    plan = fixture(); original = digest(plan)
    if change == 'fact': plan['mock_context'] += ' She can fly.'
    if change == 'action': plan['scenes'][0]['approved_action'] += ' New rescue.'
    if change == 'end': plan['scenes'][-1]['required_end_state'] += ' Reward.'
    if change == 'age': plan['reader_age'] = 4
    if change == 'order': plan['scenes'].reverse()
    with pytest.raises(ValueError, match='fingerprint'): compile_contract(plan, original)


@pytest.mark.parametrize('change', ['quote', 'remove', 'obligation', 'hash', 'id'])
def test_tampered_contract_rejected_even_if_hash_is_recomputed(change):
    plan = fixture(); contract = compile_contract(plan, digest(plan))
    if change == 'quote': contract['requirements'][0]['source_quote'] = 'Invented canon'
    if change == 'remove': contract['requirements'].pop()
    if change == 'obligation': contract['requirements'][-1]['obligation'] = 'PRESERVE_FACTS'
    if change == 'id': contract['requirements'][0]['id'] = 'OTHER'
    if change == 'hash': contract['approved_plan_sha256'] = '0' * 64
    contract['contract_sha256'] = digest({k:v for k,v in contract.items() if k != 'contract_sha256'})
    with pytest.raises(ValueError): validate_contract(contract, plan, digest(plan))


def response_fixture():
    plan = fixture(1); contract = compile_contract(plan, digest(plan))
    segments = [{'span_id': 'S001', 'text': 'Synthetic grounded evidence.'}]
    response = {'requirement_checks': [
        {'requirement_id': row['id'], 'span_ids': ['S001'],
         'exact_text': 'Synthetic grounded evidence.', 'reason': 'Synthetic test decision',
         'repair_span_ids': [], 'assessment': 'SATISFIED'} for row in contract['requirements']],
        'observations': [], 'summary': 'Synthetic routing fixture, not a model qualification.'}
    return plan, contract, segments, response


def test_dynamic_schema_does_not_mutate_qualified_lighthouse_schema():
    from src.lighthouse_audit_decision import IDS, SCHEMA
    plan, contract, _, _ = response_fixture()
    schema = audit_schema(contract)
    assert schema['properties']['requirement_checks']['items']['properties']['requirement_id']['enum'] != IDS
    assert SCHEMA['properties']['requirement_checks']['items']['properties']['requirement_id']['enum'] == IDS


def test_advice_cannot_dispatch_patch_but_material_violation_can():
    plan, contract, segments, response = response_fixture()
    response['observations'] = [{'family': 'closure_integrity', 'span_ids': [], 'exact_text': '',
        'reason': 'Optional polish', 'material_impact': '', 'classification': 'ADVISORY'}]
    result = decision(response, segments, contract, plan, digest(plan))
    assert result['status'] == 'ACCEPT' and not result['findings']
    response['requirement_checks'][-1].update(assessment='MATERIAL_VIOLATION', repair_span_ids=['S001'])
    result = decision(response, segments, contract, plan, digest(plan))
    assert result['status'] == 'REPAIR' and result['findings'][0]['family'] == 'closure_integrity'


def test_uncertainty_does_not_accept_or_dispatch_known_findings():
    plan, contract, segments, response = response_fixture()
    response['requirement_checks'][0].update(assessment='MATERIAL_VIOLATION', repair_span_ids=['S001'])
    response['requirement_checks'][1].update(assessment='UNCERTAIN', span_ids=[], exact_text='')
    result = decision(response, segments, contract, plan, digest(plan))
    assert result['status'] == 'UNRESOLVED' and result['findings'] == []


@pytest.mark.parametrize('change', ['quote', 'span', 'repair_span', 'duplicate', 'missing', 'nondefect_repair'])
def test_invalid_audit_cannot_accept_or_patch(change):
    plan, contract, segments, response = response_fixture(); row = response['requirement_checks'][0]
    if change == 'quote': row['exact_text'] = 'Invented quotation'
    if change == 'span': row['span_ids'] = ['S999']
    if change == 'repair_span': row.update(assessment='MATERIAL_VIOLATION', repair_span_ids=['S999'])
    if change == 'duplicate': response['requirement_checks'][1]['requirement_id'] = row['requirement_id']
    if change == 'missing': response['requirement_checks'].pop()
    if change == 'nondefect_repair': row['repair_span_ids'] = ['S001']
    with pytest.raises(RuntimeError): decision(response, segments, contract, plan, digest(plan))


def test_recorded_six_check_live_audit_cannot_be_reused_as_sixteen_check_proof():
    plan = approved_input(); contract = compile_contract(plan, digest(plan))
    calls = json.loads(Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-06-20261005/calls.json').read_text())
    old = calls[-1]['response']
    with pytest.raises(RuntimeError):
        decision({k:old[k] for k in ('requirement_checks', 'observations', 'summary')},
                 [], contract, plan, digest(plan))
