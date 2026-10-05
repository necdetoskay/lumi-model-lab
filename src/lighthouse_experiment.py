"""One editorial-plan experiment. Preparation is offline; paid dispatch is gated."""
from copy import deepcopy
import hashlib
import json
import re
import ast
from pathlib import Path
from time import perf_counter

from src.lighthouse_editorial_handoff import SOURCE, APPROVAL, build
from src.lighthouse_writer_once import request_payload, dependency_paths as writer_dependency_paths
from src.spineforge_v20_story_audit_artifact import _segment_story
from src.spineforge_v21_constraints import digest_json
from src.spineforge_v21_quality_runtime import (
    _usage, build_initial_audit_payload, build_targeted_final_audit_payload,
)
from src.spineforge_v21_bounded_quality import (
    split_findings, build_scene_repair_handoff, apply_scene_rewrite,
)
from src.spineforge_v21_model_adapter import (
    provider_usage, validate_schema, AUDIT_RESPONSE_SCHEMA, REPAIR_RESPONSE_SCHEMA,
)

EXPERIMENT_ID = 'LIGHTHOUSE-EDITORIAL-01'
WRITER_MODEL = 'aion-labs/aion-3.5-mini'
PROMPT = Path('prompts/lighthouse_editorial_writer.md')
LIMITS = {'WRITER': .03, 'INITIAL_AUDIT': .08, 'SCENE_REPAIR': .07, 'FINAL_AUDIT': .05}
TOTAL_BUDGET = .23
RATES = {'WRITER': (.70, 1.40), 'INITIAL_AUDIT': (2., 10.),
         'SCENE_REPAIR': (2., 10.), 'FINAL_AUDIT': (2., 10.)}


def approved_input():
    return build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))


def dependency_manifest():
    paths = {Path(__file__).relative_to(Path.cwd()), Path('src/lighthouse_editorial_handoff.py'),
             SOURCE, APPROVAL, PROMPT, Path('configs/model_runtime_profiles.yaml'),
             Path('requirements.txt'), Path('tests/test_lighthouse_experiment.py')}
    paths.update(Path('prompts').glob('spineforge_v21_*.md'))
    paths.update(writer_dependency_paths())
    pending = list(paths)
    while pending:
        path = pending.pop()
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [n.name for n in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                if module and module.startswith('src.'):
                    dep = Path(module.replace('.', '/') + '.py')
                    if dep not in paths:
                        paths.add(dep)
                        pending.append(dep)
    return [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(paths)]


def writer_request(plan):
    # Reuse the qualified v20 request policy (low mandatory reasoning, no seed),
    # without claiming that the new editorial plan is a v20 NarrativeSpine.
    return request_payload(plan)


def bind_story(raw, plan):
    """Remove only machine markers; bind actual sentence IDs to actual scenes."""
    matches = list(re.finditer(r'^\[\[(SC\d{2})\]\][ \t]*$', raw, re.M))
    if [m[1] for m in matches] != [s['scene_id'] for s in plan['scenes']]:
        raise RuntimeError('Missing, duplicate or reordered scene markers')
    if raw.count('[[') != 6 or raw.count(']]') != 6:
        raise RuntimeError('Unexpected scene marker syntax')
    title = raw[:matches[0].start()].strip()
    if not title or '\n' in title:
        raise RuntimeError('Expected one title line before SC01')
    parts, bounds = [title], []
    for i, marker in enumerate(matches):
        end = matches[i + 1].start() if i < 5 else len(raw)
        prose = raw[marker.end():end].strip()
        if not prose:
            raise RuntimeError('Empty scene')
        start = len('\n\n'.join(parts)) + 2
        parts.append(prose)
        bounds.append({'scene_id': marker[1], 'char_start': start,
                       'char_end': start + len(prose)})
    story = '\n\n'.join(parts)
    segments = []
    for row in _segment_story(story):
        scene = next((b for b in bounds if b['char_start'] <= row['char_start']
                      and row['char_end'] <= b['char_end']), None)
        segments.append({'span_id': row['id'], 'paragraph_id': row['paragraph_id'],
                         'paragraph_index': row['paragraph_index'],
                         'repaired_text': row['text'],
                         'scene_id': scene['scene_id'] if scene else 'TITLE'})
    return {'story': story, 'story_sha256': hashlib.sha256(story.encode()).hexdigest(),
            'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'segments': segments, 'scene_bounds': bounds,
            'word_count': len(story.split()), 'plan_sha256': digest_json(plan)}


def constraints_for_findings(plan, artifact, findings):
    blocking, _ = split_findings(findings)
    by_id = {r['span_id']: r for r in artifact['segments']}
    ids = {sid for f in blocking for sid in f.span_ids}
    if not ids or any(sid not in by_id for sid in ids):
        raise RuntimeError('Unknown blocking span')
    scenes = {by_id[sid]['scene_id'] for sid in ids}
    if len(scenes) != 1 or 'TITLE' in scenes:
        raise RuntimeError('Blocking findings require more than one approved scene')
    scene_id = next(iter(scenes))
    rows = [r for r in artifact['segments'] if r['scene_id'] == scene_id]
    if len(rows) > 40:
        raise RuntimeError('Approved scene exceeds existing 40-span repair bound')
    index = next(i for i, s in enumerate(plan['scenes']) if s['scene_id'] == scene_id)
    scene = plan['scenes'][index]
    constraints = [{'source_pointer': '/setting_and_hazards', 'role': 'SETTING',
                    'text': plan['setting_and_hazards']},
                   {'source_pointer': '/preserved_outcomes', 'role': 'OUTCOMES',
                    'text': plan['preserved_outcomes']}]
    for key, role in [('approved_action', 'SCENE_ACTION'), ('required_end_state', 'EXIT_STATE')]:
        constraints.append({'source_pointer': f'/scenes/{index}/{key}', 'role': role,
                            'text': scene[key]})
    if index:
        constraints.append({'source_pointer': f'/scenes/{index-1}/required_end_state',
                            'role': 'ENTRY_STATE',
                            'text': plan['scenes'][index-1]['required_end_state']})
    result = {'schema': 'spineforge-v21-approved-constraints.v1',
              'approved_spine_hash': digest_json(plan),
              'derivation': 'EXACT_APPROVED_EDITORIAL_FIELD_PROJECTION',
              'scene_scope': {'start_span_id': rows[0]['span_id'],
                              'end_span_id': rows[-1]['span_id']},
              'constraints': constraints}
    result['artifact_sha256'] = digest_json(result)
    return result


def writer_call_once(api_key, request):
    """Use the existing one-shot prose transport; never its retrying wrapper."""
    from src.spineforge_v19_transport import _request_once
    from src.generate import OpenRouterCallError
    started = perf_counter()
    try:
        story, body, actual_request = _request_once(api_key=api_key, model=WRITER_MODEL,
            system_prompt=request['messages'][0]['content'],
            user_prompt=request['messages'][1]['content'], temperature=.76,
            max_tokens=7000, seed=None, request_class='spineforge_v20_story_writer',
            response_format={'type': 'text'}, require_parameters=False)
    except OpenRouterCallError as exc:
        from src.spineforge_v21_model_adapter import AdapterResponseError
        body = (exc.trace or {}).get('body') or {}
        try:
            usage = provider_usage(body, 'WRITER', round(perf_counter() - started, 3))
        except AdapterResponseError as usage_error:
            usage = usage_error.usage
        raise AdapterResponseError('Writer one-shot transport failure', usage,
                                   {'provider_response': body}) from exc
    usage = provider_usage(body, 'WRITER', round(perf_counter() - started, 3))
    choices = body.get('choices') or []
    if not choices or choices[0].get('finish_reason') != 'stop':
        from src.spineforge_v21_model_adapter import AdapterResponseError
        raise AdapterResponseError('Writer did not finish normally', usage,
                                   {'provider_response': body})
    if actual_request != request:
        from src.spineforge_v21_model_adapter import AdapterResponseError
        raise AdapterResponseError('Writer request drift', usage, {'provider_response': body})
    return {'story': story, 'usage': usage, 'provider_response': body}


def run_once(*, plan, authorization, output_dir, writer_fn, initial_fn, repair_fn, final_fn):
    """Callbacks dispatch once. Exclusive ledger directory consumes one authorization."""
    if plan != approved_input():
        raise RuntimeError('Approved editorial input drift')
    if (authorization.get('experiment_id') != EXPERIMENT_ID
            or authorization.get('plan_sha256') != digest_json(plan)
            or authorization.get('explicit_paid_authorization') is not True
            or authorization.get('budget_usd') != TOTAL_BUDGET
            or not authorization.get('authorization_id')):
        raise RuntimeError('Separate exact paid authorization required')
    request = writer_request(plan)
    if authorization.get('writer_request_sha256') != digest_json(request):
        raise RuntimeError('Writer prompt/request drift')
    if authorization.get('runtime_manifest_sha256') != digest_json(dependency_manifest()):
        raise RuntimeError('Runtime dependency drift')
    out = Path(output_dir) / authorization['authorization_id']
    # No existing directory may be resumed, including after a failed dispatch.
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', authorization['authorization_id']):
        raise RuntimeError('Invalid authorization id')
    out.mkdir(parents=True, exist_ok=False)
    def save(name, value):
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    save('authorization-consumed.json', authorization)
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
              'spine_architect_evaluated': False, 'translation_executed': False,
              'automatic_retry_executed': False, 'state_commit_executed': False}
    try:
        writer = invoke('WRITER', writer_fn, request)
        save('writer-raw.json', writer)
        artifact = bind_story(writer['story'], plan)
        save('writer-artifact.json', artifact)
        (out / 'original-story.txt').write_text(artifact['story'])
        if artifact['word_count'] < plan['target_words']['min']:
            raise RuntimeError('Writer length below approved minimum')
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
    plan = approved_input()
    request = writer_request(plan)
    if args.execute:
        if args.authorization is None:
            parser.error('--execute requires a separate explicit paid authorization file')
        api_key = os.environ.get('OPENROUTER_API_KEY', '')
        if not api_key:
            parser.error('OPENROUTER_API_KEY is required')
        from src.spineforge_v21_model_adapter import (
            execute_initial_audit_call, execute_scene_repair_call, execute_final_audit_call,
        )
        result = run_once(plan=plan, authorization=json.loads(args.authorization.read_text()),
            output_dir=Path('evidence/lighthouse-paid-experiment'),
            writer_fn=lambda p: writer_call_once(api_key, p),
            initial_fn=lambda p: execute_initial_audit_call(api_key=api_key, payload=p),
            repair_fn=lambda p: execute_scene_repair_call(api_key=api_key, payload=p),
            final_fn=lambda p: execute_final_audit_call(api_key=api_key, payload=p))
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(0 if result['status'] == 'ACCEPT' else 1)
    output = Path('evidence/lighthouse-editorial')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'writer-input.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    prepared = {'experiment_id': EXPERIMENT_ID, 'status': 'OFFLINE_PREPARED_UNPAID',
                'plan_sha256': digest_json(plan), 'writer_request_sha256': digest_json(request),
                'writer_request': request, 'stage_cost_limits_usd': LIMITS,
                'proposed_budget_usd': TOTAL_BUDGET,
                'writer_request_utf8_bytes': len(json.dumps(request, ensure_ascii=False).encode()),
                'max_calls': 4, 'max_repairs': 1, 'paid_execution_authorized': False}
    prepared['runtime_manifest'] = dependency_manifest()
    prepared['runtime_manifest_sha256'] = digest_json(prepared['runtime_manifest'])
    (output / 'prepared-experiment.json').write_text(json.dumps(prepared, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in prepared.items() if k != 'writer_request'}))
