import pytest
from ncd_gemma.tool_protocol import decode_arguments


def native(body, name="search_docs"):
    return f"<|tool_call>call:{name}{body}<tool_call|>"


def test_native_nested_arguments_preserve_thai_punctuation():
    raw = native('{query:<|"|>ไต, HbA1c {ข้อ 1}: "ไทย"<|"|>,top_k:3,filters:{population:<|"|>general<|"|>}}')
    assert decode_arguments(raw, "search_docs") == {"query": 'ไต, HbA1c {ข้อ 1}: "ไทย"', "top_k": 3, "filters": {"population": "general"}}


def test_json_still_supported():
    assert decode_arguments('{"query":"ไทย","top_k":2}', "search_docs")["top_k"] == 2


@pytest.mark.parametrize("raw", [native('{query:<|"|>x<|"|>}', "shell"),
    native('{query:<|"|>x<|"|>,query:<|"|>y<|"|>}'),
    '{"query":"x","query":"y"}', native('{query:__import__("os")}'),
    native('{query:<|"|>unfinished}'), native('{query:<|"|>x<|"|>}') + "extra", "[]"])
def test_rejects_malformed_duplicate_or_executable_arguments(raw):
    with pytest.raises(ValueError):
        decode_arguments(raw, "search_docs")
