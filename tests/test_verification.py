import json

import pytest

from ncd_gemma.verification import parse_review, misses_explicit_quantity

ANSWER = "เด็กวัยเรียนควรนอน 9 ถึง 12 ชั่วโมง [S1]"
SOURCES = {"S1": {"text": "เอกสารตัวอย่าง: เด็กวัยเรียนควรนอน 9 ถึง 12 ชั่วโมงต่อคืน"}}


def review(**changes):
    check = {"requirement": "ระยะเวลานอนของเด็กวัยเรียน", "covered": True,
             "answer_quote": "9 ถึง 12 ชั่วโมง", "source_id": "S1",
             "evidence_quote": "เด็กวัยเรียนควรนอน 9 ถึง 12 ชั่วโมงต่อคืน"}
    check.update(changes)
    return {"checks": [check], "supported": True, "reason": "ครบตามข้อความตัวอย่าง"}


def test_review_accepts_grounded_excerpts_and_json_fence():
    message = {"content": "```json\n" + json.dumps(review()) + "\n```"}
    assert parse_review(message, ANSWER, SOURCES).supported


@pytest.mark.parametrize("changes", [
    {"answer_quote": "8 ชั่วโมง"},
    {"answer_quote": " "},
    {"source_id": "S9"},
    {"evidence_quote": "ข้อเท็จจริงที่ผู้ตรวจแต่งเพิ่มขึ้นมา"},
    {"evidence_quote": "9"},
    {"covered": False},
])
def test_review_cannot_approve_invented_support_or_missing_requirement(changes):
    with pytest.raises(ValueError):
        parse_review({"content": json.dumps(review(**changes))}, ANSWER, SOURCES)


def test_partial_answer_is_rejected_without_demanding_nonexistent_quotes():
    verdict = review()
    verdict["checks"].append({"requirement": "สิ่งที่ถามเพิ่มเติม", "covered": False,
                              "answer_quote": "", "source_id": "", "evidence_quote": ""})
    verdict["supported"] = False
    assert not parse_review({"content": json.dumps(verdict)}, ANSWER, SOURCES).supported


def test_unexpected_tool_call_cannot_pass_review():
    with pytest.raises(ValueError):
        parse_review({"content": json.dumps(review()), "tool_calls": [{"id": "bad"}]}, ANSWER, SOURCES)


def test_numeric_table_row_without_labels_cannot_be_used_as_verification():
    source = {"S1": {"text": "ตารางตัวอย่าง\n10 20 30 40 50"}}
    verdict = review(evidence_quote="10 20 30 40 50")
    with pytest.raises(ValueError, match="only numbers"):
        parse_review({"content": json.dumps(verdict)}, ANSWER, source)


def test_missing_answer_quote_may_be_null_only_when_not_covered():
    verdict = review(covered=False, answer_quote=None, source_id="", evidence_quote="")
    verdict["supported"] = False
    assert not parse_review({"content": json.dumps(verdict)}, ANSWER, SOURCES).supported
    with pytest.raises(ValueError):
        parse_review({"content": json.dumps(review(answer_quote=None))}, ANSWER, SOURCES)


@pytest.mark.parametrize("answer,missing", [
    ("ได้รับประกาศนียบัตร [S1]", True),
    ("ได้รับประกาศนียบัตร [S1, S2]", True),
    ("ได้รับ 12 คะแนน [S1]", False),
    ("ได้รับสิบสองคะแนน [S1]", False),
])
def test_source_markers_do_not_satisfy_an_explicit_quantity_question(answer, missing):
    assert misses_explicit_quantity("จบกิจกรรมได้กี่คะแนน", answer) is missing
    assert not misses_explicit_quantity("จบกิจกรรมได้รับอะไร", answer)
