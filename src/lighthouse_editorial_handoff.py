"""Offline projection of the human-approved plan; this module cannot call models."""
import hashlib
import json
import re
from pathlib import Path

SOURCE = Path('docs/experiments/lighthouse-context-and-spine-draft.md')
APPROVAL = Path('evidence/lighthouse-editorial/plan-approval.json')
OUTPUT = Path('evidence/lighthouse-editorial/writer-input.json')


def build(source: bytes, approval: dict) -> dict:
    digest = hashlib.sha256(source).hexdigest()
    if (approval.get('source_sha256') != digest
            or approval.get('verdict') != 'APPROVE'
            or approval.get('scope') != 'EDITORIAL_PLAN_ONLY'
            or approval.get('paid_execution_authorized') is not False):
        raise ValueError('Plan approval or source binding invalid')
    text = source.decode('utf-8')
    def section(title):
        return text.split('## ' + title + '\n', 1)[1].split('\n## ', 1)[0].strip()
    scenes = []
    for scene_id, title, body in re.findall(
            r'### (SC\d{2}) — ([^\n]+)\n(.*?)(?=\n### |\Z)',
            section('Olay zinciri'), re.S):
        if 'Son durum:' in body:
            narrative, end_state = body.rsplit('Son durum:', 1)
        elif scene_id == 'SC06':
            narrative, end_state = body.strip().rsplit('\n\n', 1)
        else:
            raise ValueError('Scene end state missing')
        scenes.append(dict(scene_id=scene_id, title=title,
                           approved_action=narrative.strip(),
                           required_end_state=end_state.strip()))
    if [s['scene_id'] for s in scenes] != [f'SC{i:02}' for i in range(1, 7)]:
        raise ValueError('Missing or reordered approved scene')
    return {
        'schema': 'lighthouse-editorial-writer-input.v1',
        'status': 'PREPARED_NOT_RUNTIME_QUALIFIED',
        'experiment_kind': 'HUMAN_EDITORIAL_PLAN_WRITER_QUALITY',
        'source_sha256': digest,
        'plan_approval_sha256': hashlib.sha256(json.dumps(approval, ensure_ascii=False,
            sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'paid_execution_authorized': False,
        'production_canon_write_authorized': False,
        'spine_architect_evaluated': False,
        'reader_age': 12,
        'output_language': 'en',
        'target_words': {'min': 1400, 'max': 1800},
        'reader_promise': section('Okur ve hikâye vaadi'),
        'mock_context': section('Mock bağlam'),
        'setting_and_hazards': section('Mekân ve tehlike'),
        'scenes': scenes,
        'preserved_outcomes': section('Yazımda korunacak sonuçlar'),
        'approved_clarifications': section('İlk konu önerisinden netleştirilen fark'),
        'runtime_blockers': [
            'Bind this editorial input to the existing Writer adapter without bridge data',
            'Bind generated scene spans to actual output before quality handoff',
            'Verify exact model IDs, live prices, input/output caps and total budget',
            'Obtain separate paid authorization for this experiment',
        ],
    }


if __name__ == '__main__':
    result = build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'scene_count': len(result['scenes']),
                      'paid_execution_authorized': False}))
