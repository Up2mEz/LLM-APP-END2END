import json

import pytest

from ncd_gemma.agent import parse_answer
from ncd_gemma.evidence import TableContext, numbered_text, line_quote, table_like
from ncd_gemma.verification import parse_review


def chunk(cid, page, text, edition="v1"):
    return {"chunk_id": cid, "document_id": "synthetic", "edition_id": edition,
            "pdf_page_start": page, "pdf_page_end": page, "char_start": 0, "text": text}


def test_split_table_keeps_header_and_units_without_crossing_edition():
    header = chunk("header", 1, "อายุ | รวม | จากนม | จากอาหาร\nหน่วย: กรัมต่อวัน")
    data = chunk("rows", 2, "1 80 30 50\n2 90 40 50")
    unrelated = chunk("other-edition", 2, "DO NOT INCLUDE", "v2")
    original = json.loads(json.dumps(data))
    result = TableContext([header, data, unrelated]).enrich(data)
    assert header["text"] in result["text"] and data["text"] in result["text"]
    assert "DO NOT INCLUDE" not in result["text"]
    assert result["pdf_page_start"] == 1 and result["pdf_page_end"] == 2
    assert data == original  # Frozen input is not mutated.


def test_distant_page_is_not_injected_into_a_table():
    old = chunk("old", 1, "OLD HEADER")
    data = chunk("rows", 30, "1 80 30 50\n2 90 40 50")
    assert "OLD HEADER" not in TableContext([old, data]).enrich(data)["text"]


def test_html_header_hit_includes_neighboring_data_row():
    header = chunk('header', 17, 'ผลลัพธ์ปี 2567 <table><tr><th>ปี</th><th>เข้าร่วม</th><th>Remission</th></tr>')
    row = chunk('row', 18, '<tr><td>2567</td><td>468 คน</td><td>98 คน</td></tr></table>')
    other = chunk('other', 18, '<tr><td>WRONG</td></tr>', 'older')
    assert table_like(header['text'])
    result = TableContext([header, row, other]).enrich(header)
    assert '468 คน' in result['text'] and '98 คน' in result['text']
    assert 'WRONG' not in result['text']


def test_citation_lines_are_copied_from_source_not_generated_by_the_model():
    sources = {"S1": {"text": "หัวเรื่องเอกสาร\nข้อความหลักฐานสำหรับทดสอบ\nอีกย่อหน้าหนึ่ง"}}
    candidate = {"status": "answered", "answer": "คำตอบ [S1]", "citations": [
        {"source_id": "S1", "start_line": 2, "end_line": 2}]}
    result = parse_answer(json.dumps(candidate), sources, True)
    assert result.citations[0].quote == "ข้อความหลักฐานสำหรับทดสอบ"
    assert numbered_text(sources["S1"]["text"]).startswith("1: หัวเรื่อง")


@pytest.mark.parametrize("start,end", [(0,1), (1,99), (2,1), (True,1), ("1",1)])
def test_unknown_or_invalid_line_ranges_fail_closed(start,end):
    with pytest.raises(ValueError):
        line_quote({"text": "ข้อความหลักฐานสำหรับทดสอบ"}, start, end)


def test_review_selects_real_evidence_lines_without_retyping_a_quote():
    sources = {"S1": {"text": "ข้อความหลักฐานสำหรับทดสอบ"}}
    review = {"checks": [{"requirement":"ประเด็นที่ถาม", "covered":True,
                         "source_id":"S1", "start_line":1, "end_line":1}],
              "supported":True, "reason":"ตรงกับบรรทัดที่เลือก"}
    assert parse_review({"content": json.dumps(review)}, "คำตอบ", sources).supported
    review["checks"][0]["end_line"] = 2
    with pytest.raises(ValueError):
        parse_review({"content": json.dumps(review)}, "คำตอบ", sources)
