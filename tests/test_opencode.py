import pytest

from toolforge_pilot import opencode
from toolforge_pilot.preflight import suggest


ROWS = [
    {'id': 'deepseek-v4.1-flash-free', 'name': 'DeepSeek', 'family': 'deepseek', 'context': 200000, 'output': 32000, 'released': 10, 'variants': []},
    {'id': 'glm-5.3-flash-free', 'name': 'GLM', 'family': 'glm', 'context': 128000, 'output': 16000, 'released': 9, 'variants': []},
    {'id': 'minimax-m3.1-flash-free', 'name': 'MiniMax', 'family': 'minimax', 'context': 64000, 'output': 8000, 'released': 8, 'variants': []},
]


def make_client(rows=None):
    client = opencode.Client('http://127.0.0.1:1234', 'test')
    client.models = lambda refresh=False: list(rows or ROWS)
    return client


def test_chain_uses_order_as_allow_list_and_keeps_primary():
    client = make_client()
    assert client.chain('deepseek-v4.1-flash-free', order=['minimax-m3.1-flash-free']) == [
        'deepseek-v4.1-flash-free', 'minimax-m3.1-flash-free']
    assert client.chain('deepseek-v4.1-flash-free', order=[]) == [
        'deepseek-v4.1-flash-free', 'glm-5.3-flash-free', 'minimax-m3.1-flash-free']


def test_chain_skips_exhausted_models_until_reset():
    client = make_client()
    chain = client.chain('deepseek-v4.1-flash-free', fallback=True,
                         skip={'deepseek-v4.1-flash-free', 'glm-5.3-flash-free'})
    assert chain == ['minimax-m3.1-flash-free']
    with pytest.raises(opencode.OpenCodeError, match='erschöpft'):
        client.chain('deepseek-v4.1-flash-free', skip={row['id'] for row in ROWS})


def test_generate_switches_after_rate_limit_and_reports_tried():
    client = make_client()
    calls = []
    switched = []

    def generate_one(prompt, model, timeout=None):
        calls.append(model)
        if model == 'deepseek-v4.1-flash-free':
            raise opencode.OpenCodeError('limit', status=429, reason='rate_limit', retry_after_ms=45000)
        return {'text': 'ok', 'model': model}

    client.generate_one = generate_one
    result = client.generate('Auftrag', model='deepseek-v4.1-flash-free',
                             order=['glm-5.3-flash-free'],
                             on_switch=lambda old, new, exc: switched.append((old, new)))
    assert calls == ['deepseek-v4.1-flash-free', 'glm-5.3-flash-free']
    assert result['model'] == 'glm-5.3-flash-free'
    assert result['tried'] == ['deepseek-v4.1-flash-free']
    assert switched[0][1] == 'glm-5.3-flash-free'


def test_generate_does_not_hide_non_retryable_errors():
    client = make_client()

    def generate_one(prompt, model, timeout=None):
        raise opencode.OpenCodeError('auth', status=401, reason='unauthorized')

    client.generate_one = generate_one
    with pytest.raises(opencode.OpenCodeError, match='auth'):
        client.generate('Auftrag', model='deepseek-v4.1-flash-free',
                        order=['glm-5.3-flash-free'])


def test_generate_reports_shared_quota_with_retry_after():
    client = make_client()

    def generate_one(prompt, model, timeout=None):
        raise opencode.OpenCodeError('limit', status=429, reason='rate_limit', retry_after_ms=45000)

    client.generate_one = generate_one
    with pytest.raises(opencode.OpenCodeError) as exc:
        client.generate('Auftrag')
    assert exc.value.status == 429
    assert exc.value.reason == 'rate_limit'
    assert exc.value.retry_after_ms == 45000
    assert len(exc.value.tried) == len(ROWS)


def test_studio_switch_checks_context_and_preflight_chat_never_falls_back():
    client = make_client()
    studio = opencode.OpenCodeStudio(client, fallback=False)
    with pytest.raises(ValueError, match='Modelllimit'):
        studio.switch('glm-5.3-flash-free', 999999)
    assert studio.switch('glm-5.3-flash-free', 32000) == 'glm-5.3-flash-free'
    captured = {}

    def generate(prompt, **kwargs):
        captured.update(kwargs)
        return {'text': 'Antwort', 'model': kwargs.get('model')}

    client.generate = generate
    assert studio.chat('glm-5.3-flash-free', 'Probe', .2)['response'] == 'Antwort'
    assert captured['fallback'] is False
    assert captured['model'] == 'glm-5.3-flash-free'


def test_flatten_messages_keeps_roles_and_text_parts():
    prompt = opencode.flatten_messages([
        {'role': 'system', 'content': 'Regel'},
        {'role': 'user', 'content': [{'type': 'text', 'text': 'Auftrag'}]},
        {'role': 'assistant', 'content': ''},
    ])
    assert '### SYSTEM\nRegel' in prompt
    assert '### USER\nAuftrag' in prompt
    assert '### ASSISTANT' not in prompt


def test_openai_completion_shape_and_model_prefix():
    client = make_client()
    captured = {}

    def generate(prompt, **kwargs):
        captured.update(kwargs)
        return {'text': 'Fertige Antwort', 'model': 'glm-5.3-flash-free', 'tried': ['deepseek-v4.1-flash-free']}

    client.generate = generate
    result = opencode.completion(client, {
        'model': 'openai/glm-5.3-flash-free',
        'messages': [{'role': 'user', 'content': 'Schreibe Code'}],
    }, order=['glm-5.3-flash-free'])
    assert captured['model'] == 'glm-5.3-flash-free'
    assert captured['order'] == ['glm-5.3-flash-free']
    assert result['choices'][0]['message']['content'] == 'Fertige Antwort'
    assert result['model'] == 'glm-5.3-flash-free'
    assert result['x_toolforge']['fallbacks'] == ['deepseek-v4.1-flash-free']


def test_suggest_uses_an_independent_judge_for_free_models():
    rows = [{'key': row['id'], 'type': 'llm', 'max_context_length': row['context']} for row in ROWS]
    result = suggest(rows, 'coding')
    assert result['candidates'][0] == 'deepseek-v4.1-flash-free'
    assert result['judge'] != result['candidates'][0]


def test_service_info_rejects_non_local_urls(monkeypatch, tmp_path):
    import json
    monkeypatch.setenv('TOOLFORGE_OPENCODE_URL', 'https://example.com')
    monkeypatch.setenv('TOOLFORGE_OPENCODE_PASSWORD', 'x')
    with pytest.raises(opencode.OpenCodeUnavailable, match='lokal'):
        opencode.service_info()
    monkeypatch.delenv('TOOLFORGE_OPENCODE_URL')
    monkeypatch.delenv('TOOLFORGE_OPENCODE_PASSWORD')
    state = tmp_path / 'service.json'
    state.write_text(json.dumps({'url': 'http://127.0.0.1:9999', 'password': 'pw'}), encoding='utf-8')
    monkeypatch.setenv('TOOLFORGE_OPENCODE_SERVICE_FILE', str(state))
    assert opencode.service_info() == {'url': 'http://127.0.0.1:9999', 'password': 'pw'}


def test_session_bridge_uses_project_id_and_openai_shape(tmp_path):
    from backend.pilot_service import Session
    session = Session(tmp_path, 'project-123')
    session.settings['provider'] = 'opencode'
    client = make_client()

    def generate(prompt, **kwargs):
        return {'text': 'Brückenantwort', 'model': 'glm-5.3-flash-free', 'tried': []}

    client.generate = generate
    session.opencode_client = lambda: client
    assert session.bridge_base().endswith('/api/projects/project-123/opencode/v1')
    listed = session.bridge_models()
    assert [row['id'] for row in listed['data']] == [row['id'] for row in ROWS]
    response = session.bridge_chat({'model': 'deepseek-v4.1-flash-free',
                                    'messages': [{'role': 'user', 'content': 'Hallo'}]})
    assert response['object'] == 'chat.completion'
    assert response['choices'][0]['message']['content'] == 'Brückenantwort'
    assert session.opencode_last_model == 'glm-5.3-flash-free'
    session.close()
