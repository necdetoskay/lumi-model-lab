import json
import pytest
from src.lighthouse_editorial_preparation import ROOT, SOURCE, PROMPT, OUT, build, bind_scenes, sha


def test_exact_approved_source_and_disabled_payment():
    approval = json.loads((ROOT / OUT / 'approval.json').read_text())
    p = build((ROOT / SOURCE).read_text(), (ROOT / PROMPT).read_text(), approval['source_sha256'])
    assert p['approval'] == approval
    assert p['paid_execution_authorized'] is False
    assert p['provider_calls'] == 0
    assert p['automatic_spine_generation_measured'] is False
    assert len(p['scenes']) == 6
    assert p == json.loads((ROOT / OUT / 'writer-input.json').read_text())


def test_approval_does_not_survive_source_change():
    source = (ROOT / SOURCE).read_text()
    with pytest.raises(ValueError, match='source changed'):
        build(source + ' Changed ending.', (ROOT / PROMPT).read_text(), sha(source))


def sample():
    return 'The Lighthouse Thief\n' + ''.join(f'[[SC{i:02}]]\nEkin waited. Duru listened.\n\n' for i in range(1, 7))


def test_scene_offsets_preserve_original_text():
    raw = sample()
    bound = bind_scenes(raw)
    assert bound['raw_story_sha256'] == sha(raw)
    for row in bound['scenes']:
        assert raw[row['start_char']:row['end_char']] == row['text']


@pytest.mark.parametrize('bad', [sample().replace('[[SC03]]', '[[SC02]]'),
                                    sample().replace('[[SC06]]', '[[SC07]]'),
                                    sample().replace('[[SC04]]', ''),
                                    sample().replace('[[SC02]]\nEkin waited. Duru listened.', '[[SC02]]'),
                                    sample().replace('The Lighthouse Thief\n', '')])
def test_bad_scene_boundaries_stop(bad):
    with pytest.raises(ValueError):
        bind_scenes(bad)
