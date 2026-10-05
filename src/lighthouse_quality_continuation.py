"""Single paid quality continuation of a saved Writer artifact; no Writer transport."""
import json
import re
import hashlib
from copy import deepcopy
from pathlib import Path
from src.lighthouse_experiment import (
    approved_input, bind_story, dependency_manifest, digest_json, _usage,
    constraints_for_findings, split_findings, build_scene_repair_handoff,
    apply_scene_rewrite, build_initial_audit_payload, build_targeted_final_audit_payload,
    validate_schema, AUDIT_RESPONSE_SCHEMA, REPAIR_RESPONSE_SCHEMA,
)
EXPERIMENT_ID = 'LIGHTHOUSE-QUALITY-CONTINUATION-01'
SOURCE_DIR = Path('evidence/lighthouse-paid-experiment/LIGHTHOUSE-PAID-01-20261005')
PREPARED = Path('evidence/lighthouse-editorial/quality-continuation-prepared.json')
LIMITS = {'INITIAL_AUDIT': .08, 'SCENE_REPAIR': .07, 'FINAL_AUDIT': .05}

def prepare():
    plan = approved_input()
    artifact = bind_story(json.loads((SOURCE_DIR / 'writer-raw.json').read_text())['story'], plan)
    original = (SOURCE_DIR / 'original-story.txt').read_text()
    if artifact['story'] != original:
        raise RuntimeError('Saved Writer text drift')
    if artifact['story_sha256'] != json.loads((SOURCE_DIR / 'writer-artifact.json').read_text())['story_sha256']:
        raise RuntimeError('Original artifact hash drift')
    if artifact['word_count'] < plan['target_words']['min']:
        raise RuntimeError('Saved story below approved minimum')
    paths = {r['path'] for r in dependency_manifest()}
    paths.update(str(p) for p in SOURCE_DIR.glob('*'))
    paths.update(['src/lighthouse_quality_continuation.py',
                  'tests/test_lighthouse_quality_continuation.py',
                  '.github/workflows/lighthouse-quality-once.yml'])
    files = [{'path': p, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    return {'experiment_id': EXPERIMENT_ID, 'plan_sha256': digest_json(plan),
            'source_story_sha256': artifact['story_sha256'], 'word_count': artifact['word_count'],
            'runtime_manifest_sha256': digest_json(files), 'runtime_manifest': files,
            'stage_cost_limits_usd': LIMITS, 'budget_usd': .20,
            'max_calls': 3, 'max_repairs': 1, 'writer_calls': 0,
            'paid_execution_authorized': False}, plan, artifact

def run_once(*, authorization, output_dir, initial_fn, repair_fn, final_fn):
    prepared, plan, artifact = prepare()
    for key in ['experiment_id', 'plan_sha256', 'source_story_sha256', 'runtime_manifest_sha256', 'budget_usd']:
        if authorization.get(key) != prepared[key]:
            raise RuntimeError('Continuation authorization drift: ' + key)
    if authorization.get('explicit_paid_authorization') is not True:
        raise RuntimeError('Explicit continuation authorization required')
    aid = authorization.get('authorization_id', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', aid):
        raise RuntimeError('Invalid continuation authorization id')
    out = Path(output_dir) / aid
    out.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    save('authorization-consumed.json', authorization)
    save('source-artifact.json', artifact)
    (out / 'original-story.txt').write_text(artifact['story'])
    calls = []
    def invoke(stage, fn, payload):
        row = {'stage': stage, 'input': deepcopy(payload), 'input_sha256': digest_json(payload),
               'status': 'STARTED'}
        calls.append(row)
        save('calls.json', calls)  # Failure here stops BEFORE dispatch.
        try:
            response = fn(deepcopy(payload))
            row['response'] = response
            row['usage'] = _usage(response, stage)
            row['status'] = 'COMPLETED'
            save('calls.json', calls)
            if row['usage']['cost_usd'] > LIMITS[stage]:
                raise RuntimeError('Stage cost ceiling exceeded')
            if stage != 'WRITER':
                schema = REPAIR_RESPONSE_SCHEMA if stage == 'SCENE_REPAIR' else AUDIT_RESPONSE_SCHEMA
                validate_schema({k: response[k] for k in schema['properties'] if k in response}, schema)
            return response
        except Exception as exc:
            row['status'] = 'FAILED'
            row['failure_type'] = type(exc).__name__
            row['failure_message'] = getattr(exc, 'diagnostic_message', str(exc))
            row['provider_evidence'] = getattr(exc, 'provider_evidence', None)
            row['reported_usage'] = getattr(exc, 'usage', None)
            save('calls.json', calls)
            raise
    result = {'experiment_id': EXPERIMENT_ID, 'status': 'STARTED', 'repair_count': 0,
              'writer_call_count': 0, 'spine_architect_evaluated': False,
              'translation_executed': False, 'automatic_retry_executed': False,
              'state_commit_executed': False}
    try:
        invariant_texts = [plan['mock_context'], plan['setting_and_hazards'],
                           plan['preserved_outcomes']] + [s['approved_action'] + '\n' +
                           s['required_end_state'] for s in plan['scenes']]
        common = {'source_story_artifact_id': EXPERIMENT_ID + '-writer',
                  'source_story_sha256': artifact['story_sha256'], 'source_story': artifact['story'],
                  'story_segments': artifact['segments'], 'approved_spine_hash': digest_json(plan),
                  'canon_invariants': invariant_texts}
        payload = build_initial_audit_payload(**common)
        payload['reader_profile'] = {'age': 12, 'language': 'en'}
        audit = invoke('INITIAL_AUDIT', initial_fn, payload)
        known_ids = {r['span_id'] for r in artifact['segments']}
        if any(s not in known_ids for f in audit['findings'] for s in f['span_ids']):
            raise RuntimeError('Initial audit references unknown span')
        blocking, _ = split_findings(audit['findings'])
        if not blocking:
            result.update(status='ACCEPT', accepted_story_sha256=artifact['story_sha256'])
            (out / 'accepted-story.txt').write_text(artifact['story'])
        else:
            constraints = constraints_for_findings(plan, artifact, audit['findings'])
            handoff = build_scene_repair_handoff(**common, findings=audit['findings'],
                                                approved_constraints=constraints)
            handoff['reader_profile'] = payload['reader_profile']
            save('repair-handoff.json', handoff)
            result['repair_count'] = 1
            repair = invoke('SCENE_REPAIR', repair_fn, handoff)
            expected = {f.index for f in blocking}
            resolved = repair['resolved_blocking_finding_indexes']
            if (any(type(i) is not int for i in resolved) or len(resolved) != len(set(resolved))
                    or set(resolved) != expected):
                raise RuntimeError('Repair claim does not match blocking set')
            rewrite = apply_scene_rewrite(source_story=artifact['story'],
                story_segments=artifact['segments'], cluster=handoff['scene_cluster'],
                replacement_scene=repair['replacement_scene'])
            save('rewrite.json', rewrite)
            (out / 'candidate-story.txt').write_text(rewrite['repaired_story'])
            final_payload = build_targeted_final_audit_payload(
                repaired_story_sha256=rewrite['repaired_story_sha256'],
                replacement_scene=repair['replacement_scene'].strip(),
                scene_repair_handoff=handoff, approved_spine_hash=digest_json(plan),
                canon_invariants=invariant_texts)
            final_payload['reader_profile'] = payload['reader_profile']
            final = invoke('FINAL_AUDIT', final_fn, final_payload)
            final_ids = {r['span_id'] for r in final_payload['replacement_scene_segments']}
            if any(s not in final_ids for f in final['findings'] for s in f['span_ids']):
                raise RuntimeError('Final audit references unknown span')
            remaining, _ = split_findings(final['findings'])
            result['status'] = 'REJECT_NON_CONVERGENT' if remaining else 'ACCEPT'
            if not remaining:
                (out / 'accepted-story.txt').write_text(rewrite['repaired_story'])
                result['accepted_story_sha256'] = rewrite['repaired_story_sha256']
    except Exception as exc:
        result.update(status='REJECT_RUNTIME', failure_type=type(exc).__name__,
                      failure_message=str(exc))
    result['call_count'] = len(calls)
    for row in calls:
        if 'usage' not in row and row.get('reported_usage'):
            try:
                row['usage'] = _usage({'usage': row['reported_usage']}, row['stage'])
            except RuntimeError:
                pass
    result['confirmed_cost_usd'] = sum(c.get('usage', {}).get('cost_usd', 0) for c in calls)
    result['accounting_complete'] = all('usage' in c for c in calls)
    save('result.json', result)
    return result

if __name__ == '__main__':
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    if not args.execute:
        prepared, _, _ = prepare()
        PREPARED.write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({k:v for k,v in prepared.items() if k != 'runtime_manifest'}))
    else:
        if not args.authorization or not os.environ.get('OPENROUTER_API_KEY'):
            parser.error('Continuation requires exact authorization and API key')
        from src.spineforge_v21_model_adapter import (
            execute_initial_audit_call, execute_scene_repair_call, execute_final_audit_call,
        )
        key = os.environ['OPENROUTER_API_KEY']
        result = run_once(authorization=json.loads(args.authorization.read_text()),
            output_dir=Path('evidence/lighthouse-quality-continuation'),
            initial_fn=lambda p: execute_initial_audit_call(api_key=key, payload=p),
            repair_fn=lambda p: execute_scene_repair_call(api_key=key, payload=p),
            final_fn=lambda p: execute_final_audit_call(api_key=key, payload=p))
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'ACCEPT' else 1)
