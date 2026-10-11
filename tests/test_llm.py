from types import SimpleNamespace

import pytest

from ncd_gemma.config import Settings
from ncd_gemma.llm import ProxyClient
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
