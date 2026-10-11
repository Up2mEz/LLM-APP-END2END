import pytest
from ncd_gemma.question_scope import broad_kidney_diet


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
