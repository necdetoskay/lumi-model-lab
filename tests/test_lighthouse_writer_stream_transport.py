import json
import pytest
from src.generate import OpenRouterCallError
from src.lighthouse_writer_prompt_trial import requests
from src.lighthouse_experiment import approved_input
from src.lighthouse_writer_stream_transport import dispatch


class Response:
    def __init__(self, lines): self.lines = lines; self.closed = False
    def raise_for_status(self): pass
    def iter_lines(self, **kwargs): yield from self.lines
    def close(self): self.closed = True


def stream(content='Story', finish='stop', done=True):
    chunks = [{'id':'synthetic', 'choices':[{'delta':{'content':content}}]},
              {'choices':[{'delta':{}, 'finish_reason':finish}],
               'usage':{'prompt_tokens':10,'completion_tokens':30,'total_tokens':40,'cost':.0001}}]
    return ['data: '+json.dumps(c) for c in chunks]+(['data: [DONE]'] if done else [])


def test_exact_streaming_request_no_historical_cap_clamp(monkeypatch):
    request = requests(approved_input())[0][1]; seen = []; response = Response(stream())
    def post(url, **kwargs): seen.append(kwargs); return response
    monkeypatch.setattr('src.lighthouse_writer_stream_transport.requests.post',post)
    text,body,actual = dispatch('synthetic-test-key', request)
    assert text == 'Story' and actual == request and body['usage']['cost'] == .0001
    assert seen[0]['json']['max_tokens'] == 16384 and seen[0]['stream'] is True
    assert len(seen) == 1 and response.closed


@pytest.mark.parametrize('content,finish,done', [('', 'length', True), ('Partial', 'stop', False)])
def test_failed_stream_keeps_bill_and_partial_text_without_retry(monkeypatch,content,finish,done):
    response=Response(stream(content,finish,done)); seen=[]
    def post(*args, **kwargs): seen.append(1); return response
    monkeypatch.setattr('src.lighthouse_writer_stream_transport.requests.post',post)
    with pytest.raises(OpenRouterCallError) as error:
        dispatch('synthetic-test-key',requests(approved_input())[0][1])
    body=error.value.trace['body']
    assert body['usage']['cost']==.0001 and body['choices'][0]['message']['content']==content
    assert len(seen)==1 and response.closed and 'synthetic-test-key' not in str(error.value.trace)


def test_profile_drift_blocks_network(monkeypatch):
    monkeypatch.setattr('src.lighthouse_writer_stream_transport.requests.post',lambda *a,**k:pytest.fail('Network'))
    request=requests(approved_input())[0][1]; request['max_tokens']=7000
    with pytest.raises(RuntimeError): dispatch('test',request)
