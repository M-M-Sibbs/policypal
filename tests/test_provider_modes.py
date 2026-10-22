import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest
import requests

from app.generator import ChatGenerator, OpenAICompatibleClient, ProviderError
from .test_rag_components import HITS


def client():
    return OpenAICompatibleClient('groq', 'secret-test-value', 'model', '', 1, 0, 300, 42)


@pytest.mark.parametrize('status,category', [(401, 'authentication'), (403, 'authentication'),
    (429, 'rate_limit'), (400, 'model_rejection'), (404, 'model_rejection'), (503, 'upstream')])
def test_failures_keep_safe_categories(monkeypatch, status, category):
    monkeypatch.setattr('app.generator.requests.post', lambda *a, **k: SimpleNamespace(status_code=status))
    monkeypatch.setattr('app.generator.time.sleep', lambda _: None)
    with pytest.raises(ProviderError) as err:
        client().complete([])
    assert err.value.category == category
    assert 'secret-test-value' not in str(err.value)


def failing_client(monkeypatch):
    c = client()
    def fail(messages):
        raise ProviderError('sensitive upstream payload', category='authentication', status_code=401)
    monkeypatch.setattr(c, 'complete', fail)
    return c


def test_degraded_mode_is_visible_and_logs_are_safe(monkeypatch, make_client, caplog):
    generator = ChatGenerator([failing_client(monkeypatch)], 150)
    with caplog.at_level(logging.WARNING):
        body = make_client(generator).post('/chat', json={'question': 'How many PTO days can I carry over?'}).get_json()
    assert body['generation']['mode'] == 'degraded'
    assert body['generation']['failures'][0]['category'] == 'authentication'
    assert body['provider'] == 'extractive:offline'
    assert 'authentication' in caplog.text
    assert 'sensitive upstream payload' not in caplog.text


def test_strict_request_disallows_fallback(monkeypatch, make_client):
    generator = ChatGenerator([failing_client(monkeypatch)], 150)
    response = make_client(generator).post('/chat', json={'question': 'How many PTO days can I carry over?', 'require_llm': True})
    assert response.status_code == 502
    assert response.get_json()['generation']['mode'] == 'unavailable'


def test_unavailable_when_fallback_cannot_answer(monkeypatch):
    generator = ChatGenerator([failing_client(monkeypatch)], 150)
    with pytest.raises(ProviderError) as err:
        generator.generate('Unrelated astronomy?', HITS)
    assert err.value.generation['mode'] == 'unavailable'


def test_timeout_category_is_preserved(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout('secret-test-value')
    monkeypatch.setattr('app.generator.requests.post', timeout)
    with pytest.raises(ProviderError) as err:
        client().complete([])
    assert err.value.category == 'timeout'
    assert 'secret-test-value' not in str(err.value)


@pytest.mark.parametrize('content', [None, '', 42, {'text': 'not a completion'}])
def test_empty_or_malformed_completions_are_provider_failures(monkeypatch, content):
    monkeypatch.setattr('app.generator.requests.post', lambda *a, **k: SimpleNamespace(
        status_code=200, json=lambda: {'choices': [{'message': {'content': content}}]}))
    with pytest.raises(ProviderError) as err:
        client().complete([])
    assert err.value.category == 'malformed_response'


@pytest.mark.parametrize('content', ['', 'Partial policy answer [1].'])
def test_length_limited_completion_is_not_accepted(monkeypatch, content):
    monkeypatch.setattr('app.generator.requests.post', lambda *a, **k: SimpleNamespace(
        status_code=200, json=lambda: {'choices': [{'finish_reason': 'length', 'message': {'content': content}}]}))
    with pytest.raises(ProviderError) as err:
        client().complete([])
    assert err.value.category == 'token_limit'


def test_configured_reasoning_effort_is_sent(monkeypatch):
    payloads = []
    def post(*args, **kwargs):
        payloads.append(kwargs['json'])
        return SimpleNamespace(status_code=200, json=lambda: {'choices': [{'message': {'content': 'Five days [1].'}}]})
    monkeypatch.setattr('app.generator.requests.post', post)
    c = OpenAICompatibleClient('groq', 'secret', 'openai/gpt-oss-20b', '', 1, 0, 1200, 42, reasoning_effort='low')
    assert c.complete([]) == 'Five days [1].'
    assert payloads[0]['reasoning_effort'] == 'low' and payloads[0]['max_tokens'] == 1200


def test_citation_retry_supplies_previous_answer_for_correction(monkeypatch, make_client):
    c = client()
    sent = []
    def complete(messages):
        sent.append(messages)
        return 'Five days. Bonus [99].' if len(sent) == 1 else 'Five days carry over [1].'
    monkeypatch.setattr(c, 'complete', complete)
    body = make_client(ChatGenerator([c], 150)).post('/chat', json={'question': 'How many PTO days can I carry over?'}).get_json()
    assert body['status'] == 'answered'
    assert {'role': 'assistant', 'content': 'Five days. Bonus [99].'} in sent[1]
    assert sent[1][-1]['role'] == 'user'


def test_new_request_does_not_reuse_previous_requests_answer(monkeypatch):
    c = client()
    messages_seen = []
    def complete(messages):
        messages_seen.append(messages)
        if len(messages_seen) == 2:
            raise ProviderError('offline')
        return 'Previous request answer [1].'
    monkeypatch.setattr(c, 'complete', complete)
    generator = ChatGenerator([c], 150)
    generator.generate('old question', HITS)
    generator.generate('PTO carry over', HITS)
    generator.generate('PTO carry over', HITS, retry=True)
    assert not any(m['role'] == 'assistant' and m['content'] == 'Previous request answer [1].' for m in messages_seen[-1])


def test_health_observes_calls_without_calling_provider(monkeypatch, make_client):
    generator = ChatGenerator([failing_client(monkeypatch)], 150)
    api = make_client(generator, llm_provider='groq')
    assert api.get('/health').get_json()['provider_status']['availability'] == 'unknown'
    api.post('/chat', json={'question': 'How many PTO days can I carry over?'})
    observed = api.get('/health').get_json()['provider_status']
    assert observed['availability'] == 'unavailable' and observed['observed_at']
    assert observed['providers']['groq:model']['category'] == 'authentication'


def test_offline_demo_and_no_generation_are_distinct(client):
    body = client.post('/chat', json={'question': 'How many PTO days can I carry over?'}).get_json()
    assert body['generation']['mode'] == 'offline_demo'
    body = client.post('/chat', json={'question': 'What is the capital of France?'}).get_json()
    assert body['generation']['mode'] == 'not_attempted' and body['provider'] is None


def test_concurrent_generation_metadata_does_not_bleed(monkeypatch):
    c = client()
    barrier = Barrier(2)
    def complete(messages):
        barrier.wait(timeout=3)
        if 'fail' in messages[1]['content'].split('<question>')[1]:
            raise ProviderError('private', category='rate_limit')
        return 'Five days [1].'
    monkeypatch.setattr(c, 'complete', complete)
    generator = ChatGenerator([c], 150)
    def run(question):
        generator.generate(question, HITS)
        barrier.wait(timeout=3)
        return generator.generation_info['mode']
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, ['PTO carry over', 'fail PTO carry over'])) == ['llm', 'degraded']
