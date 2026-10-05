"""Offline editorial handoff; deliberately has no provider or paid entry point."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'docs/experiments/lighthouse-context-and-spine-draft.md'
PROMPT = 'prompts/lighthouse_editorial_writer_v1.md'
OUT = 'evidence/lighthouse-editorial-preparation'


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def build(source: str, prompt: str, approved_source_sha256: str) -> dict:
    if sha(source) != approved_source_sha256:
        raise ValueError('Approved editorial source changed')
    body = source.split('## Okur ve hikâye vaadi\n', 1)[1].split(
        '## İlk konu önerisinden netleştirilen fark', 1)[0]
    scenes = re.findall(r'^### (SC\d{2}) — ([^\n]+)\n(.*?)(?=^### |^## |\Z)',
                        body, flags=re.M | re.S)
    if [s[0] for s in scenes] != [f'SC{i:02}' for i in range(1, 7)]:
        raise ValueError('Expected the six approved scenes in order')
    approval = {
        'schema': 'editorial-plan-human-approval.v1',
        'verdict': 'APPROVE',
        'user_statement': 'Evet onaylıyorum',
        'evidence': 'User reply to detailed plan approval question; external conversation msg_idx 57',
        'source_commit': '546b88821ea961153840a09312e5e8d68a52ef01',
        'source_path': SOURCE,
        'source_sha256': approved_source_sha256,
        'scope': 'editorial context and plot only',
        'paid_execution_authorized': False,
    }
    request = {
        'model': 'aion-labs/aion-3.5-mini',
        'temperature': 0.76,
        'max_tokens': 7000,
        'reasoning': {'effort': 'low'},
        'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': 'APPROVED EDITORIAL PLAN\n\n## Okur ve hikâye vaadi\n' + body},
        ],
    }
    return {
        'schema': 'lighthouse-editorial-preparation.v1',
        'status': 'OFFLINE_INPUT_PREPARED_NOT_RUNTIME_QUALIFIED',
        'experiment_type': 'HUMAN_EDITORIAL_PLAN_TO_WRITER_AND_QUALITY',
        'automatic_spine_generation_measured': False,
        'approval': approval,
        'prompt_sha256': sha(prompt),
        'writer_request': request,
        'writer_request_sha256': sha(json.dumps(request, ensure_ascii=False, sort_keys=True)),
        'scenes': [{'scene_id': sid, 'title': title, 'approved_text': text.strip()}
                   for sid, title, text in scenes],
        'paid_execution_authorized': False,
        'provider_calls': 0,
        'production_state_commit_authorized': False,
        'limits': {'writer_calls': 1, 'quality_calls': 3, 'scene_repairs': 1, 'automatic_retries': 0},
        'translation_in_scope': False,
    }


def bind_scenes(raw: str) -> dict:
    markers = list(re.finditer(r'^\[\[(SC\d+)\]\][ \t]*\r?$', raw, flags=re.M))
    if [m[1] for m in markers] != [f'SC{i:02}' for i in range(1, 7)]:
        raise ValueError('Missing, duplicate, unknown or reordered scene markers')
    if not raw[:markers[0].start()].strip():
        raise ValueError('Missing story title')
    rows = []
    for i, marker in enumerate(markers):
        start = marker.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(raw)
        text = raw[start:end]
        if not text.strip():
            raise ValueError('Empty scene')
        rows.append({'scene_id': marker[1], 'start_char': start, 'end_char': end,
                     'text_sha256': sha(text), 'text': text})
    return {'raw_story_sha256': sha(raw), 'offset_unit': 'unicode_code_points', 'scenes': rows}


def main() -> None:
    folder = ROOT / OUT
    approval = json.loads((folder / 'approval.json').read_text())
    package = build((ROOT / SOURCE).read_text(), (ROOT / PROMPT).read_text(), approval['source_sha256'])
    if package['approval'] != approval:
        raise ValueError('Approval record differs from declared source and scope')
    (folder / 'writer-input.json').write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': package['status'], 'scenes': len(package['scenes']),
                      'request_characters': len(json.dumps(package['writer_request'], ensure_ascii=False)),
                      'paid_execution_authorized': False, 'provider_calls': 0}))


if __name__ == '__main__':
    main()
