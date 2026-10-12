from types import SimpleNamespace

import pytest
from httpx import Request
from openai import APIConnectionError

from ncd_gemma.config import Settings
from ncd_gemma.llm import ProxyClient
from ncd_gemma.llm import ProxyError
from ncd_gemma.schemas import SEARCH_TOOL


@pytest.mark.parametrize("tool_list", [[], [SEARCH_TOOL]])
def test_empty_tools_omit_tool_choice_for_class_proxy(tmp_path, tool_list):
    captured = []
    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}', tool_calls=[]),
                                                       finish_reason='stop')], usage=None)
    client = ProxyClient.__new__(ProxyClient)
    client.settings = Settings(cache_dir=tmp_path)
    client.endpoint_identity = 'test-endpoint'
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    messages = [{"role": "user", "content": "test"}]
    client.complete(messages, tool_list, 'none', 10)
    assert ('tools' in captured[0]) == bool(tool_list)
    assert ('tool_choice' in captured[0]) == bool(tool_list)
    assert client.complete(messages, tool_list, 'none', 10)['cached']
    assert len(captured) == 1


def test_rate_limit_retry_is_bounded_and_counted(tmp_path, monkeypatch):
    waits, requests = [], []
    monkeypatch.setattr('ncd_gemma.llm.time.sleep', waits.append)
    class RateLimit(Exception):
        status_code = 429
        response = SimpleNamespace(headers={'retry-after':'16'})
    def create(**kwargs):
        requests.append(kwargs)
        if len(requests) == 1: raise RateLimit()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}',tool_calls=[]),finish_reason='stop')],usage=None)
    client = ProxyClient.__new__(ProxyClient)
    client.settings = Settings(cache_dir=tmp_path)
    client.endpoint_identity = 'test-endpoint'
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    result = client.complete([{'role':'user','content':'synthetic'}], [], 'none', 40)
    assert result['api_attempts'] == 2 and waits == [16.0]
    assert len(requests) == 2


def test_rate_limit_cannot_sleep_past_request_deadline(tmp_path, monkeypatch):
    waits = []
    monkeypatch.setattr('ncd_gemma.llm.time.sleep', waits.append)
    class RateLimit(Exception):
        status_code = 429
    def create(**kwargs): raise RateLimit()
    client = ProxyClient.__new__(ProxyClient)
    client.settings = Settings(cache_dir=tmp_path)
    client.endpoint_identity = 'test-endpoint'
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    with pytest.raises(ProxyError) as error:
        client.complete([{'role':'user','content':'synthetic'}], [], 'none', 10)
    assert error.value.attempts == 1 and not waits


def test_transient_proxy_connection_failure_retries_once(tmp_path, monkeypatch):
    waits, requests = [], []
    monkeypatch.setattr('ncd_gemma.llm.time.sleep', waits.append)
    def create(**kwargs):
        requests.append(kwargs)
        if len(requests) == 1:
            raise APIConnectionError(request=Request('POST', 'https://llm.nat-d.uk/v1/chat/completions'))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}',tool_calls=[]),
                                                       finish_reason='stop')], usage=None)
    client = ProxyClient.__new__(ProxyClient)
    client.settings = Settings(cache_dir=tmp_path)
    client.endpoint_identity = 'test-endpoint'
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    result = client.complete([{'role':'user','content':'synthetic'}], [], 'none', 15)
    assert result['api_attempts'] == 2 and waits == [2.0]
    assert len(requests) == 2
