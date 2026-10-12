import pytest
from ncd_gemma.copy_alignment import anchor_copy, align_claim_copies, missing_requested_dimension

TEXT='ข้อมูลโครงการสังเคราะห์สำหรับกลุ่มผู้เข้าร่วมกิจกรรมที่ได้ลงทะเบียนไว้ล่วงหน้า จำนวน 18 คน โดยจะนำมาคิดคะแนนเฉพาะการประเมินรอบที่ 4'

def test_near_copy_outputs_real_source_instead_of_accepting_paraphrase():
    candidate=TEXT.replace('ได้ลงทะเบียน','ลงทะเบียน')
    assert anchor_copy(candidate,TEXT)==TEXT

@pytest.mark.parametrize('candidate', [TEXT.replace('18','19'),TEXT.replace('รอบที่ 4','รอบที่ 5'),TEXT.replace('จะนำมา','จะไม่นำมา'),TEXT+' (invented English)'])
def test_alignment_cannot_repair_changed_facts_into_valid_quotes(candidate):
    assert anchor_copy(candidate,TEXT)==candidate

def test_source_choice_and_original_candidate_are_preserved():
    raw={'status':'answered','claims':[{'text':TEXT.replace('ได้ลงทะเบียน','ลงทะเบียน'),'source_id':'S2','span_ids':['P1']}]}
    result=align_claim_copies(raw,{'S2':{'text':TEXT}})
    assert result['claims'][0]['text']==TEXT and result['claims'][0]['source_id']=='S2'
    assert raw['claims'][0]['text']!=TEXT

def test_dimension_gate_distinguishes_section_from_round_and_bare_proportion():
    assert missing_requested_dimension('โครงการคิดคะแนนรอบใด','ส่วนที่ 3 มีคะแนน 20')
    assert not missing_requested_dimension('โครงการคิดคะแนนรอบใด','รอบที่ 4')
    assert missing_requested_dimension('กลุ่ม B มีจำนวนและสัดส่วนเท่าไร','กลุ่ม B 18 60')
    assert not missing_requested_dimension('กลุ่ม B มีจำนวนและสัดส่วนเท่าไร','กลุ่ม B 18 คน ร้อยละ 60')

def test_frequency_requires_schedule_not_only_daily_amount():
    assert missing_requested_dimension('สารทดลอง A มีปริมาณและความถี่เท่าไร','สารทดลอง A 6 กรัมต่อวัน')
    assert not missing_requested_dimension('สารทดลอง A มีปริมาณและความถี่เท่าไร','สารทดลอง A 6 กรัมต่อวัน แบ่ง 3 ครั้ง')

def test_label_field_and_unasked_prescribing_are_distinguished():
    assert missing_requested_dimension('ควรมองหาข้อมูลอะไรบนฉลาก','อ่านฉลากก่อนซื้อทุกครั้ง')
    assert not missing_requested_dimension('ควรมองหาข้อมูลอะไรบนฉลาก','ปริมาณน้ำตาลต่อหนึ่งหน่วยบริโภค')
    assert missing_requested_dimension('เป้าค่าที่วัดคือเท่าไร','ให้เริ่มด้วยยาชนิด A ก่อน')
    assert not missing_requested_dimension('ควรใช้ยาอย่างไร','ให้เริ่มด้วยยาชนิด A ก่อน')


def test_one_conditioned_target_rejects_extra_general_target():
    question = 'ถ้าผู้ป่วยมีค่าโปรตีนเกินเกณฑ์ ควรตั้งเป้าความดันเท่าไร'
    assert missing_requested_dimension(question, 'ทั่วไป 130/80 หรือกรณีนี้ 125/75 มม.ปรอท')
    assert not missing_requested_dimension(question, 'กรณีนี้ต่ำกว่า 125/75 มม.ปรอท')
    assert not missing_requested_dimension('เปรียบเทียบความดันของสองกลุ่มว่าเท่าไร', '130/80 และ 125/75 มม.ปรอท')


def test_other_condition_cannot_replace_requested_disease_context():
    question = 'เมื่อมีไตเรื้อรังร่วมด้วยควรเปลี่ยนแป้งอย่างไร'
    assert missing_requested_dimension(question, 'ถ้าไม่อิ่ม ให้กินวุ้นเส้นเพิ่ม')
    assert not missing_requested_dimension(question, 'ผู้มีไตเรื้อรังอาจเลือกแป้งโปรตีนต่ำ เช่น วุ้นเส้น')


def test_two_situation_comparison_requires_both_halves():
    question = 'ระบบไหลเวียนคงที่กับความดันค่อนข้างต่ำเหมาะกับการฟอกเลือดต่างกันอย่างไร'
    assert missing_requested_dimension(question, 'SLED ใช้ในรายความดันต่ำ')
    assert not missing_requested_dimension(question, 'รายไหลเวียนคงที่ใช้ intermittent และรายความดันต่ำใช้ SLED')
