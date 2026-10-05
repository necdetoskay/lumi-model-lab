import json
from pathlib import Path
import pytest
from src.story_delivery import normalize_marked_story
from src.lighthouse_experiment import approved_input
from src.lighthouse_writer_once import scene_artifact

IDS=['SC01','SC02']
STORY='A title\n\n[[SC01]]\nSalt — wind.\n\n[[SC02]]\nThe final image.'


def test_native_utf8_is_not_guessed_or_reencoded():
    story,proof=normalize_marked_story(STORY,IDS)
    assert story==STORY and proof['identical_copy_count']==1


@pytest.mark.parametrize('separator',['\n\n',''])
def test_only_exact_whole_story_replay_is_collapsed(separator):
    story,proof=normalize_marked_story(separator.join([STORY]*3),IDS)
    assert story==STORY and proof['identical_copy_count']==3
    assert len(set(proof['copy_sha256']))==1 and not proof['semantic_rewrite']


@pytest.mark.parametrize('text',[STORY+STORY.replace('final image','different ending'),
    STORY+'\n[[SC01]]\nPartial retry.',STORY.replace('[[SC02]]','[[SC03]]'),
    STORY.replace('[[SC01]]','[[SC02]]'),STORY+'\n[[EXTRA]]\nNew scene.'])
def test_different_or_partial_drafts_and_unknown_scenes_are_rejected(text):
    with pytest.raises(RuntimeError):normalize_marked_story(text,IDS)


def test_historical_encoding_correction_requires_explicit_provenance():
    broken=STORY.encode('utf8').decode('latin1')
    assert normalize_marked_story(broken,IDS)[0]==broken
    assert normalize_marked_story(broken,IDS,encoding_provenance='latin1_decoded_utf8_sse')[0]==STORY
    with pytest.raises(RuntimeError):normalize_marked_story(STORY,IDS,encoding_provenance='latin1_decoded_utf8_sse')


@pytest.mark.parametrize('variant,expected_count', [('current_baseline',1),('five_category_appendix',3)])
def test_real_saved_deliveries_match_previous_reading_hash_without_edit(variant,expected_count):
    root=Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005')
    raw=next(r['response']['story'] for r in json.loads((root/'calls.json').read_text())
             if r['stage']=='WRITER' and r['variant']==variant)
    plan=approved_input();story,proof=normalize_marked_story(raw,[s['scene_id'] for s in plan['scenes']],
        encoding_provenance='latin1_decoded_utf8_sse')
    artifact=scene_artifact(story,plan)
    expected=json.loads((root/(variant+'-derived-artifact.json')).read_text())
    assert artifact['story_sha256']==expected['story_sha256']
    assert proof['identical_copy_count']==expected_count
