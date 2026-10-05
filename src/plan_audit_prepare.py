"""Reproducible zero-cost preparation using the approved Lighthouse handoff."""
import json
from pathlib import Path
from src.lighthouse_experiment import approved_input
from src.plan_audit_contract import compile_contract, digest, validate_contract
from src.plan_audit_decision import audit_schema

OUTPUT = Path('evidence/plan-audit-contract-v1')


def prepare():
    # The existing builder checks approval scope and the original source hash.
    plan = approved_input()
    fingerprint = digest(plan)
    contract = compile_contract(plan, fingerprint)
    validate_contract(contract, plan, fingerprint)
    schema = audit_schema(contract)
    proof = {
        'status': 'OFFLINE_PREPARED_NOT_MODEL_QUALIFIED',
        'source_adapter': 'approved_editorial_plan_field_shape',
        'approved_plan_sha256': fingerprint,
        'original_source_sha256': plan['source_sha256'],
        'contract_sha256': contract['contract_sha256'],
        'requirement_count': len(contract['requirements']),
        'scene_count': len(plan['scenes']),
        'all_scene_actions_and_end_states_included': True,
        'source_projection': 'EXACT_ORIGINAL_LANGUAGE_NO_MODEL_NO_TRANSLATION',
        'api_calls': 0, 'new_cost_usd': 0,
        'existing_story_development_total_usd': 1.7585491,
        'production_write': False,
        'live_audit_runtime_changed': False,
        'prior_six_requirement_audit_is_not_proof_for_this_contract': True,
        'limits': ['Generic only within this editorial plan field shape.',
                   'Source sections are not automatically split into atomic semantic assertions.',
                   'Dynamic schema and source-language prompt have not been live model qualified.',
                   'A compiler hash is source binding, not an approval grant.'],
    }
    return contract, schema, proof


if __name__ == '__main__':
    contract, schema, proof = prepare()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, value in [('contract.json', contract), ('response-schema.json', schema),
                        ('preparation.json', proof)]:
        (OUTPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(proof, ensure_ascii=False))
