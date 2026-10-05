"""Isolated, single-attempt Aion transport for the paired prompt experiment."""
import json
import requests
from src.generate import OPENROUTER_URL, OpenRouterCallError

MAX_TOKENS = 32768
MODEL = 'aion-labs/aion-3.5-mini'


def dispatch(api_key, payload):
    # Do not renormalize through the historical 7,000-token request class.
    if (payload.get('model') != MODEL or payload.get('max_tokens') != MAX_TOKENS
            or payload.get('reasoning') != {'effort': 'low', 'exclude': True}
            or payload.get('reasoning_effort') != 'low'
            or payload.get('stream') is not True
            or payload.get('stream_options') != {'include_usage': True}):
        raise RuntimeError('Frozen streaming Writer profile drift')
    body = {'id': None, 'model': MODEL, 'choices': [
        {'message': {'role': 'assistant', 'content': ''}, 'finish_reason': None}], 'usage': {}}
    parts = []
    response = None
    done = False
    try:
        response = requests.post(OPENROUTER_URL,
            headers={'Authorization': 'Bearer '+api_key, 'Content-Type': 'application/json',
                     'HTTP-Referer': 'https://github.com/necdetoskay/lumi-model-lab',
                     'X-Title': 'LUMI Model Lab'},
            json=payload, stream=True, timeout=(30, 240))
        response.raise_for_status()
        response.encoding = 'utf-8'
        for raw in response.iter_lines(decode_unicode=True):
            if isinstance(raw, bytes): raw = raw.decode('utf-8')
            if not raw or not raw.startswith('data:'): continue
            data = raw[5:].strip()
            if data == '[DONE]':
                done = True
                break
            chunk = json.loads(data)
            for key in ('id', 'model'):
                if chunk.get(key): body[key] = chunk[key]
            if isinstance(chunk.get('usage'), dict): body['usage'] = chunk['usage']
            if chunk.get('error'): raise RuntimeError('Provider streaming error')
            for choice in (chunk.get('choices') or [])[:1]:
                content = (choice.get('delta') or {}).get('content')
                if isinstance(content, str): parts.append(content)
                if choice.get('finish_reason') is not None:
                    body['choices'][0]['finish_reason'] = choice['finish_reason']
        body['choices'][0]['message']['content'] = ''.join(parts)
        if not done: raise RuntimeError('Provider stream ended without DONE')
        if not ''.join(parts).strip(): raise RuntimeError('Provider returned no visible story text')
        return ''.join(parts), body, payload
    except Exception as exc:
        body['choices'][0]['message']['content'] = ''.join(parts)
        # Store partial text, identifiers and reported usage even on failure.
        # Neither headers nor hidden reasoning are retained in evidence.
        raise OpenRouterCallError('Single-attempt Writer stream failed: '+type(exc).__name__,
            {'stage': 'stream', 'body': body}) from exc
    finally:
        if response is not None: response.close()
