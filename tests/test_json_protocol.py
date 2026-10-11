import json

import pytest

from ncd_gemma.json_protocol import load_json


def test_duplicate_property_quote_repair_preserves_answer_and_numbers():
    malformed = '{"answer":"ข้อความ 83.7 [S1]","citations":[{"source_id":"S1","start_line":4,""end_line":8}]}'
    result = load_json(malformed)
    assert result['answer'] == 'ข้อความ 83.7 [S1]'
    assert result['citations'][0] == {'source_id':'S1','start_line':4,'end_line':8}


def test_valid_string_content_that_looks_like_syntax_is_never_changed():
    source = {'answer': 'Literal ,""end_line":8 stays as text', 'value': 17}
    assert load_json(json.dumps(source)) == source


@pytest.mark.parametrize('text', ['{"answer":"unfinished', '{"value":NaNx}', '{value:9}', '{"value":5', 'run_shell()'])
def test_other_malformed_content_is_not_guessed(text):
    with pytest.raises(ValueError):
        load_json(text)


def test_repair_does_not_relax_schema_or_convert_types():
    assert load_json('{"x":1,""end_line":"8"}')['end_line'] == '8'
