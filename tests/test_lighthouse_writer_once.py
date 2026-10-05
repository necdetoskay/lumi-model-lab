import copy
import json

import pytest

from src.lighthouse_editorial_handoff import SOURCE, APPROVAL, build
from src.lighthouse_writer_once import (request_payload, scene_artifact,
    select_quality_scope, prepare, verify, execute_once, WRITER_INPUT)
from src.spineforge_v21_bounded_quality import build_scene_repair_handoff, apply_scene_rewrite
from src.spineforge_v21_constraints import digest_json
from src.generate import OpenRouterCallError


def input_plan():
    return build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))


def marked():
    return 'The Lighthouse Thief\n\n' + '\n\n'.join(
        f'[[SC{i:02}]]\nEkin spoke in scene {i}.\n\nDuru replied in scene {i}.'
        for i in range(1, 7))


def finding(span):
    return {'family': 'physical_feasibility', 'severity': 'serious',
            'repair_scope': 'SCENE_REPAIR', 'span_ids': [span],
            'exact_text': 'Ekin spoke.', 'reason': 'Synthetic fixture, not a real defect.'}


def test_request_keeps_proven_transport_without_old_story():
    request = request_payload(input_plan())
    assert request['model'] == 'aion-labs/aion-3.5-mini'
    assert request['max_tokens'] == 7000
    assert request['reasoning'] == {'effort': 'low', 'exclude': True}
    assert request['response_format'] == {'type': 'text'}
    assert 'seed' not in request
    assert all(word not in json.dumps(request) for word in ('Arda', 'Nisa', 'S159', 'route-line'))


def test_scene_map_covers_real_text_with_repeated_sentences_unicode():
    plan = input_plan()
    response = marked().replace('Duru replied in scene 2.', 'Duru said “Wait.” Ekin waited.')
    artifact = scene_artifact(response, plan)
    assert '[[' not in artifact['story']
    assert artifact['publication_ready'] is False
    for scene in artifact['scenes']:
        prose = artifact['story'][scene['char_start']:scene['char_end']]
        assert prose and 'Ekin' in prose
        spans = [r for r in artifact['story_segments'] if r['span_id'] in scene['span_ids']]
        assert all(artifact['story'][r['char_start']:r['char_end']] == r['repaired_text'] for r in spans)


@pytest.mark.parametrize('response', [
    marked().replace('[[SC04]]', '[[SC05]]'),
    marked().replace('[[SC03]]', ''),
    marked() + '\n[[SC01]]\nExtra.',
    marked().replace('Ekin spoke in scene 1.\n\nDuru replied in scene 1.', ''),
    marked().replace('[[SC01]]', '[[SC01]]\n[[BAD]]'),
    marked().replace('\n', '\r\n'),
])
def test_bad_scene_contract_stops(response):
    with pytest.raises(RuntimeError):
        scene_artifact(response, input_plan())


def test_real_scene_scope_preserves_entry_exit_and_outside_text():
    plan = input_plan()
    artifact = scene_artifact(marked(), plan)
    scene = artifact['scenes'][4]
    findings = [finding(scene['span_ids'][0])]
    constraints = select_quality_scope(artifact, findings, plan)
    handoff = build_scene_repair_handoff(
        source_story_artifact_id=artifact['artifact_sha256'], source_story_sha256=artifact['story_sha256'],
        source_story=artifact['story'], story_segments=artifact['story_segments'], findings=findings,
        approved_spine_hash=artifact['approved_spine_hash'],
        canon_invariants=[plan['preserved_outcomes']], approved_constraints=constraints)
    assert handoff['scene_cluster']['span_ids'] == scene['span_ids']
    assert handoff['approved_constraints']['constraints'][1]['role'] == 'exit_dependency'
    rewrite = apply_scene_rewrite(source_story=artifact['story'], story_segments=artifact['story_segments'],
                                 cluster=handoff['scene_cluster'], replacement_scene='Ekin lifted the hatchling. Duru helped.')
    start, end = scene['char_start'], scene['char_end']
    assert rewrite['repaired_story'] == artifact['story'][:start] + 'Ekin lifted the hatchling. Duru helped.' + artifact['story'][end:]


def test_multiscene_or_stale_artifact_cannot_route_to_repair():
    plan = input_plan()
    artifact = scene_artifact(marked(), plan)
    with pytest.raises(RuntimeError):
        select_quality_scope(artifact, [finding(artifact['scenes'][0]['span_ids'][0]),
                                      finding(artifact['scenes'][4]['span_ids'][0])], plan)
    with pytest.raises(RuntimeError):
        select_quality_scope(artifact, [finding('S999')], plan)
    artifact['story'] += 'changed'
    with pytest.raises(RuntimeError):
        select_quality_scope(artifact, [], plan)


def grant(report):
    return {'paid_execution_authorized': True, 'scope': 'LIGHTHOUSE_WRITER_ONLY_ONE_CALL',
            'preflight_sha256': report['artifact_sha256'], 'max_cost_usd': 0.03,
            'explicit_user_message': 'FAKE TEST AUTHORIZATION, NO LIVE API'}


def fake_transport(**kwargs):
    return marked(), {'choices': [{'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 200, 'total_tokens': 300, 'cost': 0.001}}, request_payload(input_plan())


def test_plan_approval_cannot_dispatch_paid_writer(tmp_path):
    calls = []
    with pytest.raises(RuntimeError, match='authorization'):
        execute_once(api_key='test', run_id='unauthorized', authorization=json.loads(APPROVAL.read_text()),
                     output_root=tmp_path, call_fn=lambda **kw: calls.append(kw))
    assert calls == []


def test_one_shot_persists_story_and_consumes_claim(tmp_path):
    report = verify()
    evidence = execute_once(api_key='test', run_id='ok', authorization=grant(report),
                            output_root=tmp_path, call_fn=fake_transport)
    assert evidence['status'] == 'WRITER_GENERATED_NOT_QUALITY_ACCEPTED'
    assert evidence['usage']['cost_usd'] == 0.001
    assert (tmp_path / 'ok/writer-story-artifact.json').is_file()
    with pytest.raises(FileExistsError):
        execute_once(api_key='test', run_id='retry', authorization=grant(report),
                     output_root=tmp_path, call_fn=fake_transport)


@pytest.mark.parametrize('kind', ['truncated', 'missing_cost', 'invalid_scene', 'over_budget'])
def test_failed_response_retained_without_retry(tmp_path, kind):
    observed = []
    def transport(**kwargs):
        observed.append(kwargs)
        text, body, request = fake_transport(**kwargs)
        if kind == 'truncated': body['choices'][0]['finish_reason'] = 'length'
        if kind == 'missing_cost': del body['usage']['cost']
        if kind == 'invalid_scene': text = text.replace('[[SC04]]', '')
        if kind == 'over_budget': body['usage']['cost'] = 0.031
        return text, body, request
    evidence = execute_once(api_key='test', run_id=kind, authorization=grant(verify()),
                            output_root=tmp_path, call_fn=transport)
    assert len(observed) == 1
    assert evidence['status'] == 'STOPPED_NO_RETRY'
    assert evidence['raw_response'] and evidence['provider_response']
    assert not (tmp_path / kind / 'writer-story.txt').exists()


def test_preflight_hash_and_saved_input_are_bound():
    report = verify()
    assert report['paid_execution_authorized'] is False
    assert report['planned_uncached_cost_usd'] < report['proposed_writer_budget_usd']
    assert report['writer_input_sha256'] == digest_json(json.loads(WRITER_INPUT.read_text()))


def test_provider_failure_retains_reported_cost_without_retry(tmp_path):
    calls = []
    def transport(**kw):
        calls.append(kw)
        raise OpenRouterCallError('No content', {'stage': 'provider_response',
            'body': {'choices': [], 'usage': {'prompt_tokens': 100, 'completion_tokens': 200,
                                            'total_tokens': 300, 'cost': 0.001}}})
    evidence = execute_once(api_key='test', run_id='fail', authorization=grant(verify()),
                            output_root=tmp_path, call_fn=transport)
    assert len(calls) == 1 and evidence['status'] == 'STOPPED_NO_RETRY'
    assert evidence['usage']['cost_usd'] == 0.001


def test_real_one_shot_transport_emits_frozen_request(monkeypatch):
    from src.spineforge_v19_transport import _request_once
    observed = []
    class Response:
        ok = True
        def json(self):
            return {'choices': [{'finish_reason': 'stop', 'message': {'content': marked()}}]}
    def post(*args, **kwargs):
        observed.append(kwargs['json'])
        return Response()
    monkeypatch.setattr('src.spineforge_v19_transport.requests.post', post)
    request = request_payload(input_plan())
    text, _, actual = _request_once(api_key='fake', model=request['model'],
        system_prompt=request['messages'][0]['content'], user_prompt=request['messages'][1]['content'],
        temperature=0.76, max_tokens=7000, seed=None, request_class='spineforge_v20_story_writer',
        response_format={'type': 'text'}, require_parameters=False)
    assert len(observed) == 1 and actual == request and text == marked()
