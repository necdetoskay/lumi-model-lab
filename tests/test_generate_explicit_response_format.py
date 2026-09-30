from __future__ import annotations

import src.generate as gen


class FakeResponse:
    ok=True
    status_code=200
    headers={}

    def json(self):
        return {
            "choices":[{"message":{"content":"{\"ok\":true}"},"finish_reason":"stop"}],
            "usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2,"cost":0.0},
        }


def test_explicit_json_schema_survives_request_normalization(monkeypatch)->None:
    captured={}
    def fake_normalize(model,payload,*,request_class,structured_output):
        value=dict(payload)
        value["response_format"]={"type":"json_object"}
        value["provider"]={"allow_fallbacks":False}
        return value
    def fake_post(*args,**kwargs):
        captured["json"]=kwargs["json"]
        return FakeResponse()

    monkeypatch.setattr(gen,"normalize_openrouter_request",fake_normalize)
    monkeypatch.setattr(gen.requests,"post",fake_post)

    strict={
        "type":"json_schema",
        "json_schema":{
            "name":"test_contract",
            "strict":True,
            "schema":{
                "type":"object",
                "properties":{"ok":{"type":"boolean"}},
                "required":["ok"],
                "additionalProperties":False,
            },
        },
    }
    text,body,request=gen.call_openrouter(
        api_key="x",
        model="test/model",
        system_prompt="system",
        user_prompt="user",
        temperature=0,
        max_tokens=100,
        seed=None,
        request_class="test",
        structured_output=True,
        response_format=strict,
        require_parameters=True,
    )
    assert text=='{"ok":true}'
    assert request["response_format"]==strict
    assert captured["json"]["response_format"]==strict
    assert captured["json"]["provider"]=={
        "allow_fallbacks":False,
        "require_parameters":True,
    }
