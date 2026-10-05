import json
from pathlib import Path
import pytest
import src.lighthouse_delivery_replay as runtime


def test_recorded_pipeline_continues_automatically_without_accepting_story(tmp_path):
    result=runtime.replay(tmp_path/'replay')
    assert result['status']=='SAVED_DELIVERY_REPLAY_PASS' and result['new_api_calls']==0
    assert [c['decision']['status'] for c in result['cases']]==['REPAIR','REPAIR']
    assert [len(c['citation_corrections']) for c in result['cases']]==[0,1]
    assert not result['stories_publication_ready'] and not result['live_transport_qualified']
    with pytest.raises(FileExistsError):runtime.replay(tmp_path/'replay')


@pytest.mark.parametrize('change',['plan','provider_body','finish_reason','dispatched_request'])
def test_stale_or_inconsistent_saved_source_cannot_be_replayed(tmp_path,monkeypatch,change):
    ledger=json.loads((runtime.WRITER_SOURCE/'calls.json').read_text());row=ledger[0]
    if change=='plan':
        row['input']['messages'][1]['content']='{}'
        row['response']['actual_request']['messages'][1]['content']='{}'
    if change=='provider_body':row['response']['provider_response']['choices'][0]['message']['content']='changed'
    if change=='finish_reason':row['response']['provider_response']['choices'][0]['finish_reason']='length'
    if change=='dispatched_request':row['response']['actual_request']['max_tokens']=1
    source=tmp_path/'source';source.mkdir();(source/'calls.json').write_text(json.dumps(ledger))
    monkeypatch.setattr(runtime,'WRITER_SOURCE',source)
    with pytest.raises(RuntimeError):runtime.replay(tmp_path/'result')
