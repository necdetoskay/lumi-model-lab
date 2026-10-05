"""One-shot editorial Writer. Plan approval never grants paid execution."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from pathlib import Path

from src.lighthouse_editorial_handoff import SOURCE, APPROVAL, build
from src.model_registry import normalize_openrouter_request
from src.generate import OpenRouterCallError
from src.spineforge_v19_transport import _request_once
from src.spineforge_v20_story_audit_artifact import _segment_story
from src.spineforge_v21_constraints import digest_json, sha_file
from src.spineforge_v21_model_adapter import provider_usage
from src.spineforge_v21_bounded_quality import split_findings

MODEL = 'aion-labs/aion-3.5-mini'
PROMPT = Path('prompts/lighthouse_editorial_writer.md')
PROFILE = Path('evidence/lighthouse-editorial/writer-preflight.json')
WRITER_INPUT = Path('evidence/lighthouse-editorial/writer-input.json')


def request_payload(writer_input):
    request = normalize_openrouter_request(MODEL, {
        'model': MODEL,
        'messages': [{'role': 'system', 'content': PROMPT.read_text()},
                     {'role': 'user', 'content': json.dumps(writer_input, ensure_ascii=False)}],
        'temperature': 0.76, 'max_tokens': 7000,
    }, request_class='spineforge_v20_story_writer', structured_output=False)
    request['response_format'] = {'type': 'text'}
    return request


def dependency_paths():
    paths = {Path(__file__).relative_to(Path.cwd()),
             Path('tests/test_lighthouse_editorial_handoff.py'),
             Path('tests/test_lighthouse_writer_once.py'),
             Path('.github/workflows/lighthouse-editorial-zero-cost.yml'),
             PROMPT, SOURCE, APPROVAL, WRITER_INPUT,
             Path('configs/model_runtime_profiles.yaml'), Path('requirements.txt')}
    pending = list(paths)
    while pending:
        path = pending.pop()
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) else
                       [r.name for r in node.names] if isinstance(node, ast.Import) else [])
            for module in modules:
                if module and module.startswith('src.'):
                    dep = Path(module.replace('.', '/') + '.py')
                    if dep not in paths:
                        paths.add(dep)
                        pending.append(dep)
    return sorted(paths)


def prepare():
    writer_input = build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))
    WRITER_INPUT.write_text(json.dumps(writer_input, ensure_ascii=False, indent=2) + '\n')
    request = request_payload(writer_input)
    # UTF-8 byte count is a conservative planning allowance, not an exact token count.
    input_bytes = len(json.dumps(request, ensure_ascii=False).encode())
    report = {
        'schema': 'lighthouse-writer-preflight.v1',
        'status': 'OFFLINE_PREPARED_PAID_NOT_AUTHORIZED',
        'experiment_kind': 'HUMAN_EDITORIAL_PLAN_WRITER_QUALITY',
        'spine_architect_evaluated': False,
        'source_commit': '546b88821ea961153840a09312e5e8d68a52ef01',
        'writer_input_sha256': digest_json(writer_input),
        'request': request, 'request_sha256': digest_json(request),
        'input_utf8_bytes': input_bytes,
        'planning_method': 'UTF8_BYTES_AS_CONSERVATIVE_INPUT_TOKEN_ALLOWANCE_NOT_EXACT_TOKENIZATION',
        'pricing_checked_date': '2026-10-05',
        'pricing_usd_per_million': {'input': 0.70, 'output': 1.40},
        'pricing_source': 'https://openrouter.ai/aion-labs/aion-3.5-mini/',
        'planned_uncached_cost_usd': round(input_bytes * 0.70 / 1e6 + 7000 * 1.40 / 1e6, 6),
        'proposed_writer_budget_usd': 0.03,
        'cost_ceiling_semantics': 'STOP_AFTER_ACTUAL_COST_REPORTED_NO_NEXT_CALL',
        'provider_spend_cap_guaranteed': False,
        'paid_execution_authorized': False,
        'max_writer_calls': 1, 'automatic_retry': False,
        'quality_execution_authorized': False,
        'translation_execution_authorized': False,
        'production_canon_write_authorized': False,
        'files': [{'path': str(p), 'sha256': sha_file(p)} for p in dependency_paths()],
    }
    report['artifact_sha256'] = digest_json(report)
    PROFILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def verify():
    report = json.loads(PROFILE.read_text())
    if digest_json({k: v for k, v in report.items() if k != 'artifact_sha256'}) != report['artifact_sha256']:
        raise RuntimeError('Writer preflight integrity drift')
    if {r['path'] for r in report['files']} != {str(p) for p in dependency_paths()}:
        raise RuntimeError('Writer dependency closure drift')
    for row in report['files']:
        if sha_file(Path(row['path'])) != row['sha256']:
            raise RuntimeError('Writer frozen file drift: ' + row['path'])
    value = build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))
    if (json.loads(WRITER_INPUT.read_text()) != value
            or digest_json(value) != report['writer_input_sha256']
            or request_payload(value) != report['request']):
        raise RuntimeError('Writer approved input/request drift')
    return report


def scene_artifact(marked_story, writer_input):
    if '\r' in marked_story:
        raise RuntimeError('Writer scene contract requires LF line endings')
    marks = list(re.finditer(r'^\[\[(SC\d{2})\]\]\s*$', marked_story, re.M))
    if [m[1] for m in marks] != [s['scene_id'] for s in writer_input['scenes']]:
        raise RuntimeError('Writer scenes missing, duplicated or reordered')
    title = marked_story[:marks[0].start()].strip()
    if not title or '\n' in title or '[[' in title:
        raise RuntimeError('Writer title contract invalid')
    story, scenes = title, []
    for i, mark in enumerate(marks):
        prose = marked_story[mark.end():marks[i+1].start() if i+1 < len(marks) else len(marked_story)].strip()
        if not prose or '[[' in prose or ']]' in prose:
            raise RuntimeError('Writer scene prose empty or contains stray marker')
        start = len(story) + 2
        story += '\n\n' + prose
        scenes.append({'scene_id': mark[1], 'char_start': start,
                       'char_end': len(story), 'text_sha256': hashlib.sha256(prose.encode()).hexdigest()})
    segments = [{'span_id': r['id'], 'repaired_text': r['text'], **r}
                for r in _segment_story(story)]
    for scene in scenes:
        ids = [r['span_id'] for r in segments
               if scene['char_start'] <= r['char_start'] and r['char_end'] <= scene['char_end']]
        if not ids:
            raise RuntimeError('Writer scene has no mapped spans')
        scene['span_ids'] = ids
    words = len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", story))
    out = {'schema': 'lighthouse-writer-story-artifact.v1', 'immutable': True,
           'status': 'WRITER_GENERATED_NOT_QUALITY_ACCEPTED', 'story': story,
           'story_sha256': hashlib.sha256(story.encode()).hexdigest(),
           'marked_response_sha256': hashlib.sha256(marked_story.encode()).hexdigest(),
           'writer_input_sha256': digest_json(writer_input),
           'approved_spine_hash': digest_json(writer_input),
           'story_segments': segments, 'scenes': scenes, 'word_count': words,
           'target_length_hit': 1400 <= words <= 1800, 'publication_ready': False}
    out['artifact_sha256'] = digest_json(out)
    return out


def select_quality_scope(artifact, findings, writer_input):
    if (digest_json({k: v for k, v in artifact.items() if k != 'artifact_sha256'}) != artifact['artifact_sha256']
            or artifact['writer_input_sha256'] != digest_json(writer_input)):
        raise RuntimeError('Writer artifact/input integrity drift')
    blocking, _ = split_findings(findings)
    if not blocking:
        return None
    referenced = {span for row in blocking for span in row.span_ids}
    candidates = [s for s in artifact['scenes'] if referenced <= set(s['span_ids'])]
    if len(candidates) != 1 or len(candidates[0]['span_ids']) > 40:
        raise RuntimeError('Blocking findings require more than one bounded scene')
    scene = candidates[0]
    approved = next(s for s in writer_input['scenes'] if s['scene_id'] == scene['scene_id'])
    constraints = {'approved_spine_hash': digest_json(writer_input),
        'scene_scope': {'start_span_id': scene['span_ids'][0], 'end_span_id': scene['span_ids'][-1]},
        'constraints': [{'role': 'scene_action', 'text': approved['approved_action']},
                        {'role': 'exit_dependency', 'text': approved['required_end_state']},
                        {'role': 'canon_invariant', 'text': writer_input['preserved_outcomes']},
                        {'role': 'canon_invariant', 'text': writer_input['mock_context']},
                        {'role': 'canon_invariant', 'text': writer_input['setting_and_hazards']}],
        'source_story_sha256': artifact['story_sha256']}
    constraints['artifact_sha256'] = digest_json(constraints)
    return constraints


def execute_once(*, api_key, run_id, authorization, output_root=Path('evidence/lighthouse-writer'),
                 call_fn=None):
    report = verify()
    if (authorization.get('paid_execution_authorized') is not True
            or authorization.get('scope') != 'LIGHTHOUSE_WRITER_ONLY_ONE_CALL'
            or authorization.get('preflight_sha256') != report['artifact_sha256']
            or authorization.get('max_cost_usd') != 0.03
            or not authorization.get('explicit_user_message')):
        raise RuntimeError('Separate explicit Writer paid authorization required')
    if not api_key or not run_id or Path(run_id).name != run_id or run_id in {'.', '..'}:
        raise RuntimeError('Writer key/run id missing or invalid')
    output_root.mkdir(parents=True, exist_ok=True)
    # Exclusive persistent claim, scoped to this authorization; no in-process retries.
    claim = output_root / ('authorization-' + digest_json(authorization) + '.claimed')
    claim.open('x').close()
    out = output_root / run_id
    out.mkdir(exist_ok=False)
    request = report['request']
    evidence = {'schema': 'lighthouse-writer-call.v1', 'status': 'STARTED',
                'request': request, 'preflight_sha256': report['artifact_sha256'],
                'authorization': authorization, 'automatic_retry_executed': False,
                'usage': None, 'quality_execution_authorized': False}
    path = out / 'writer-call.json'
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    started = time.perf_counter()
    try:
        text, body, actual_request = (call_fn or _request_once)(
            api_key=api_key, model=MODEL, system_prompt=request['messages'][0]['content'],
            user_prompt=request['messages'][1]['content'], temperature=0.76,
            max_tokens=7000, seed=None, request_class='spineforge_v20_story_writer',
            response_format={'type': 'text'}, require_parameters=False)
        evidence.update(raw_response=text, provider_response={k: body[k] for k in ('id','model','choices','usage') if k in body},
                        actual_request=actual_request)
        # Retain exact response before parsing or usage validation can fail.
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
        evidence['usage'] = provider_usage(body, 'LIGHTHOUSE_WRITER', time.perf_counter() - started)
        if actual_request != request:
            raise RuntimeError('Writer dispatched request differs from frozen preflight')
        finish = (body.get('choices') or [{}])[0].get('finish_reason')
        if finish != 'stop':
            raise RuntimeError('Writer incomplete response: ' + str(finish))
        if evidence['usage']['cost_usd'] > 0.03:
            raise RuntimeError('Writer reported cost exceeds authorized ceiling')
        artifact = scene_artifact(text, json.loads(WRITER_INPUT.read_text()))
        (out / 'writer-story-artifact.json').write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + '\n')
        (out / 'writer-story.txt').write_text(artifact['story'])
        evidence['status'] = 'WRITER_GENERATED_NOT_QUALITY_ACCEPTED'
    except Exception as exc:
        if isinstance(exc, OpenRouterCallError):
            trace = getattr(exc, 'trace', None) or {}
            body = trace.get('body') or {}
            evidence['provider_response'] = {k: body[k] for k in ('id', 'model', 'choices', 'usage') if k in body}
            evidence['provider_failure_stage'] = trace.get('stage')
            if body:
                try:
                    evidence['usage'] = provider_usage(body, 'LIGHTHOUSE_WRITER', time.perf_counter() - started)
                except RuntimeError:
                    pass
        evidence.update(status='STOPPED_NO_RETRY', failure_type=type(exc).__name__,
                        failure_message=exc.args[0] if isinstance(exc, RuntimeError) else type(exc).__name__)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    return evidence


if __name__ == '__main__':
    import sys
    report = prepare() if '--prepare' in sys.argv else verify()
    print(json.dumps({k: report[k] for k in ('status', 'input_utf8_bytes', 'planned_uncached_cost_usd',
                                            'proposed_writer_budget_usd', 'paid_execution_authorized')}, indent=2))
