import pytest
from ncd_gemma.question_scope import broad_kidney_diet, greeting_reply, label_field_hints


@pytest.mark.parametrize('question,expected',[
    ('เป็นโรคไต ควรงดกินไร',True),
    ('แม่มีโรคไต อาหารแบบไหนควรงด',True),
    ('เป็นโรคไตระยะ 4 ควรกินอาหารอย่างไร',False),
    ('ฟอกไตอยู่ควรงดกินอะไร',False),
    ('โรคไตควรจำกัดโซเดียมวันละกี่กรัม',False),
    ('โรคไตหมายความว่าอย่างไร',False),
    ('อาหารสำหรับคนเป็นเบาหวานควรกินแบบไหน',False),
])
def test_broad_question_is_distinct_from_specific_guideline_facts(question,expected):
    assert broad_kidney_diet(question) is expected


def test_standalone_greetings_do_not_capture_real_questions():
    assert greeting_reply('hello!')
    assert greeting_reply('สวัสดีค่ะ')
    assert greeting_reply('hello เป็นโรคไตควรลดอะไร') is None
    assert greeting_reply('สวัสดี โรคไตคืออะไร') is None


def test_label_hint_requires_question_topic_and_actual_field_in_evidence():
    evidence = [{'source_id': 'S1', 'text': 'อ่านฉลากโภชนาการก่อนซื้อ\nอาหาร ปริมาณน้ำตาล (กรัม)\nชนิด A 5'}]
    assert label_field_hints('ควรมองหาข้อมูลอะไรบนฉลากเพื่อลดน้ำตาล', evidence) == [
        {'source_id': 'S1', 'field': 'ปริมาณน้ำตาล'}]
    assert label_field_hints('ควรมองหาข้อมูลอะไรบนฉลากเพื่อลดโซเดียม', evidence) == []
    assert label_field_hints('น้ำตาลควรจำกัดกี่กรัม', evidence) == []
