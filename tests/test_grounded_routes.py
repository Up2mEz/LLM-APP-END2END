"""Synthetic relations: varied values must be read from evidence, never a qid."""
from ncd_gemma.grounded_routes import grounded_answer
from ncd_gemma.agent import Agent
from ncd_gemma.config import Settings
from test_agent import FakeLLM, FakeRetriever, call


def source(sid, text, document_id='synthetic-2569'):
    return {'source_id': sid, 'chunk_id': sid, 'document_id': document_id,
            'edition_id': '2569', 'pdf_page_start': 3, 'pdf_page_end': 3,
            'score': 0.8, 'text': text}


def test_label_field_is_read_from_column_heading_and_question_topic():
    s = source('S1', 'อ่านฉลากโภชนาการก่อนเลือกซื้อ\nสินค้า ปริมาณน้ำตาล (กรัม)\nขนม ก 8')
    result = grounded_answer('ควรมองหาข้อมูลอะไรบนฉลากเพื่อลดน้ำตาล', {'S1': s})
    assert result['route'] == 'explicit_label_field'
    assert 'ปริมาณน้ำตาล' in result['answer']
    assert 'ปริมาณน้ำตาล' in result['citations'][0]['quote']
    assert grounded_answer('ควรมองหาข้อมูลอะไรบนฉลากเพื่อลดโซเดียม', {'S1': s}) is None


def test_round_and_cycle_require_same_source_and_matching_year():
    s = source('S1', 'การคิดคะแนน ส่วนที่ 3 CQI\nคิดคะแนนเฉพาะการประเมินรอบที่ 3\n'
                        'CQI พัฒนาต่อยอดตามรูปแบบ PDCA')
    result = grounded_answer('งาน CQI ปี 2569 คิดคะแนนรอบใดและใช้วงจรอะไร', {'S1': s})
    assert 'รอบที่ 3' in result['answer'] and 'PDCA' in result['answer']
    assert grounded_answer('งาน CQI ปี 2568 คิดคะแนนรอบใดและใช้วงจรอะไร', {'S1': s}) is None
    old_edition = source('S1', s['text'] + '\nรายงานเปรียบเทียบกับปี 2568')
    assert grounded_answer('งาน CQI ปี 2568 คิดคะแนนรอบใดและใช้วงจรอะไร', {'S1': old_edition}) is None
    separate = {'S1': source('S1', 'CQI คิดคะแนนเฉพาะการประเมินรอบที่ 3'),
                'S2': source('S2', 'CQI พัฒนาต่อยอดตามรูปแบบ PDCA')}
    assert grounded_answer('งาน CQI ปี 2569 คิดคะแนนรอบใดและใช้วงจรอะไร', separate) is None


def test_course_duration_does_not_mix_level_ii_with_plain_level():
    older = source('S1', '6. ระยะเวลาการอบรม\nระยะเวลา รวม 4.5 ชั่วโมง\n'
                   'หลักสูตรดูแลโรคเบาหวานและความดันโลหิตสูง (ระดับกลาง II)',
                   document_id='course-intermediate-ii-2566')
    current = source('S2', '6. ระยะเวลาการอบรม\nระยะเวลา รวม 6 ชั่วโมง\n'
                     'หลักสูตรดูแลโรคเบาหวานและความดันโลหิตสูง (ระดับกลาง)',
                     document_id='course-intermediate-2569')
    question = 'การอบรมออนไลน์ระดับกลางเรื่องดูแลเบาหวานกับความดันใช้เวลาเรียนรวมเท่าไร'
    result = grounded_answer(question, {'S1': older, 'S2': current})
    assert result['route'] == 'course_level_duration'
    assert '6 ชั่วโมง [S2]' in result['answer']
    assert grounded_answer(question.replace('ระดับกลาง', 'ระดับกลาง II'),
                           {'S1': older, 'S2': current})['answer'].endswith('4.5 ชั่วโมง [S1]')
    assert grounded_answer(question.replace('ระดับกลาง', 'ระดับกลางปี 2568'),
                           {'S1': older, 'S2': current}) is None


def test_separate_measurement_fields_are_copied_from_the_database_list():
    q = 'ฐานข้อมูลควรแยกเก็บน้ำหนักกับส่วนสูงหรือรวมเป็นค่าเดียว'
    s = source('S1', 'จัดเก็บข้อมูลผู้ป่วย\nแยกน้ำหนักและส่วนสูง รอบเอว รอบสะโพก')
    assert grounded_answer(q, {'S1':s})['answer'] == 'เอกสารระบุให้แยกเก็บน้ำหนักและส่วนสูง [S1]'
    assert grounded_answer(q, {'S1':source('S1','บันทึกค่า BMI ค่าเดียว')}) is None


def test_split_html_table_reads_requested_year_and_labelled_column_only():
    table = ('โรงพยาบาลกงหรา\n<table><tr><th>ปี</th><th>เข้าร่วม</th><th>จำนวน</th></tr>\n'
             '<tr><td>ลดการใช้ยา</td><td>หยุดยา</td><td>Remission</td></tr>'
             '<tr><td>2567</td><td>310 คน</td><td>20 คน</td><td>11 คน</td><td>91 คน (29.35)</td></tr>'
             '<tr><td>2568</td><td>125 คน</td><td>9 คน</td><td>6 คน</td><td>34 คน (27.2)</td></tr></table>')
    s = source('S1', table)
    q = 'โครงการกงหราปี 2567 มีคนร่วมและเข้าสู่ remission กี่คน'
    result = grounded_answer(q, {'S1': s})
    assert '310 คน' in result['answer'] and '91 คน' in result['answer']
    assert '125 คน' not in result['answer'] and '125 คน' not in result['citations'][0]['quote']
    assert grounded_answer(q.replace('2567','2569'), {'S1': s}) is None
    assert grounded_answer(q, {'S1':source('S1',table.replace('Remission','Other'))}) is None


def test_two_sodium_mechanisms_require_both_facts_in_one_passage():
    q = 'อาหารกระป๋องและผงชูรสทำให้คนไตเสื่อมได้รับโซเดียมเพิ่มขึ้นได้จากอะไร'
    text = ('อาหารกระป๋องทุกชนิด ซึ่งอาหารเหล่านี้มีการเติมเกลือหรือสารกันบูด ซึ่งมีเกลือ (โซเดียม) มาก\n'
            'ผงชูรส แม้เป็นสารปรุงรสที่ไม่มีรสเค็ม แต่ก็มีเกลือ (โซเดียม) เป็นส่วนประกอบอยู่ประมาณร้อยละ 22')
    result = grounded_answer(q, {'S1': source('S1', text)})
    assert result['route'] == 'two_food_sodium_mechanisms'
    assert 'ร้อยละ 22' in result['answer'] and 'เติมเกลือหรือสารกันบูด' in result['answer']
    assert grounded_answer(q, {'S1': source('S1', text.replace('เติมเกลือหรือสารกันบูด','พบโซเดียม'))}) is None
    assert grounded_answer(q, {'S1': source('S1', text.splitlines()[0]),
                               'S2': source('S2', text.splitlines()[1])}) is None


def test_secondary_mcd_infection_row_requires_heading_and_secondary_branch():
    q = 'โรคไตชนิด MCD ที่เกิดตามหลังการติดเชื้อเกี่ยวข้องกับเชื้อกลุ่มใดบ้าง'
    text = ('ตารางที่ 9 สาเหตุของโรค Minimal change disease\nชนิด MCD สาเหตุ\n'
            'Primary Idiopathic\nSecondary\nDrugs Other\nInfection Bacteria, protozoa\n')
    result = grounded_answer(q, {'S1': source('S1', text)})
    assert result['route'] == 'secondary_mcd_infection_row'
    assert 'Bacteria และ protozoa' in result['answer']
    assert 'Infection Bacteria, protozoa' in result['citations'][0]['quote']
    assert grounded_answer(q, {'S1': source('S1', text.replace('Secondary', 'Primary'))}) is None
    assert grounded_answer(q, {'S1': source('S1', text.replace('Minimal change disease', 'Other disease'))}) is None
    assert grounded_answer(q.replace('ชนิด MCD', 'ชนิด primary MCD'), {'S1': source('S1', text)}) is None


def test_dialysis_comparison_requires_both_branches_in_same_edition():
    q = 'ผู้ป่วยไตวายที่ระบบไหลเวียนคงที่กับคนที่ความดันค่อนข้างต่ำเหมาะกับการฟอกเลือดแบบเป็นช่วงต่างกันอย่างไร'
    stable = source('S1', 'Conventional intermittent hemodialysis ใช้เป็นวิธีการมาตรฐานในผู้ป่วยไตวาย '
                          'ที่มีความเสถียรของระบบไหลเวียนโลหิต')
    low = source('S2', 'การฟอกเลือดแบบยืดเวลา (SLED) ใช้ในผู้ป่วยที่มีความดันโลหิตค่อนข้างต่ำ')
    result = grounded_answer(q, {'S1': stable, 'S2': low})
    assert result['route'] == 'dialysis_circulation_branches'
    assert 'conventional intermittent hemodialysis' in result['answer'] and 'SLED' in result['answer']
    assert len(result['citations']) == 2
    assert grounded_answer(q, {'S1': stable}) is None
    other = source('S2', low['text'], document_id='different-guideline')
    assert grounded_answer(q, {'S1': stable, 'S2': other}) is None
    assert grounded_answer(q.replace('ไหลเวียนคงที่', 'ไหลเวียนไม่คงที่'), {'S1': stable, 'S2': low}) is None


def test_paired_carb_examples_read_both_servings_without_mixing_editions():
    q = 'เมื่อนับคาร์บ ข้าวขาวหนึ่งคาร์บตักกี่ทัพพีและโคล่าหนึ่งกระป๋องนับได้กี่คาร์บ'
    rice = source('S1', 'ตัวอย่างอาหารปริมาณ 1 คาร์บ เช่น ข้าวขาว\n2 ทัพพี ข้าวเหนียว 1 ทัพพี')
    cola = source('S2', 'เครื่องดื่มเติมน้ำตาล เช่น น้ำอัดลม (โคล่า)\n1 กระป๋อง เท่ากับ 2.3 คาร์บ')
    result = grounded_answer(q, {'S1': rice, 'S2': cola})
    assert result['route'] == 'paired_carb_examples'
    assert 'ข้าวขาว 2 ทัพพีเท่ากับ 1 คาร์บ' in result['answer']
    assert 'โคล่า 1 กระป๋องเท่ากับ 2.3 คาร์บ' in result['answer']
    assert len(result['citations']) == 2
    assert grounded_answer(q, {'S1': rice}) is None
    assert grounded_answer(q.replace('หนึ่งกระป๋อง', 'สองกระป๋อง'), {'S1': rice, 'S2': cola}) is None
    assert grounded_answer(q.replace('ข้าวขาวหนึ่งคาร์บ', 'ข้าวขาวไม่ใช่หนึ่งคาร์บ'),
                           {'S1': rice, 'S2': cola}) is None
    assert grounded_answer(q, {'S1': rice, 'S2': source('S2', cola['text'], document_id='other')}) is None


def test_conditioned_target_selects_specific_value_without_general_value():
    s = source('S1', 'หากบวม จำกัดโซเดียมไม่เกิน 3 กรัม/วัน\nความดันไม่เกิน 135/85 มม.ปรอท '
                        'หรือน้อยกว่า 110/70 มม.ปรอทในรายที่โปรตีนในปัสสาวะมากกว่า 2 กรัม/วัน')
    q = 'เมื่อมีโซเดียมที่ต้องจำกัดและโปรตีนรั่วเกินวันละ 2 กรัม ควรตั้งเป้าความดันเท่าไร'
    result = grounded_answer(q, {'S1': s})
    assert '3 กรัม/วัน' in result['answer'] and '110/70' in result['answer']
    assert '135/85' not in result['answer']
    assert grounded_answer(q.replace('2 กรัม', '4 กรัม'), {'S1': s}) is None
    assert grounded_answer(q.replace('โปรตีนรั่ว', 'โปรตีนจากอาหาร'), {'S1': s}) is None


def test_conditioned_target_preserves_comparison_operators():
    s = source('S1', 'จำกัดโซเดียมน้อยกว่า 3 กรัม/วัน\n'
                        'ความดันไม่เกิน 110/70 มม.ปรอทในรายที่โปรตีนในปัสสาวะมากกว่า 2 กรัม/วัน')
    q = 'โปรตีนรั่วเกิน 2 กรัม ต้องจำกัดโซเดียมและตั้งเป้าความดันเท่าไร'
    result = grounded_answer(q, {'S1': s})
    assert 'โซเดียมน้อยกว่า 3' in result['answer']
    assert 'ความดันไม่เกิน 110/70' in result['answer']


def test_cross_source_diet_relation_requires_both_contexts():
    plate = source('S1', 'รูปแบบ DASH แบ่งจานเป็น 4 ส่วน อีก 1 ส่วน เป็นข้าวหรืออาหารที่มาจากแป้ง')
    kidney = source('S2', 'ผู้ที่เป็นโรคไตเรื้อรังก่อนล้างไตต้องระวังโปรตีนในข้าวแป้ง '
                          'ถ้าไม่อิ่มให้กินกลุ่มข้าวแป้งที่ปลอดโปรตีนเพิ่ม ได้แก่ วุ้นเส้น')
    q = 'จาน DASH ให้ข้าวแป้งเท่าไร และเมื่อมีไตเรื้อรังร่วมด้วยควรเปลี่ยนแป้งอย่างไร'
    result = grounded_answer(q, {'S1': plate, 'S2': kidney})
    assert result['route'] == 'cross_source_diet_relation'
    assert len(result['citations']) == 2 and 'ก่อนล้างไต' in result['answer']
    assert grounded_answer(q, {'S1': plate}) is None
    dialysis = q.replace('เมื่อมีไตเรื้อรังร่วมด้วย', 'เมื่อมีไตเรื้อรังและล้างไตแล้ว')
    assert grounded_answer(dialysis, {'S1': plate, 'S2': kidney}) is None
    assert grounded_answer(q, {'S1': source('S1', 'รูปแบบ DASH อีก 1 ส่วน เป็นข้าวหรืออาหารที่มาจากแป้ง'),
                               'S2': kidney}) is None


def test_agent_can_release_exact_label_relation_after_one_search():
    question = 'ควรมองหาข้อมูลอะไรบนฉลากเพื่อลดน้ำตาล'
    hit = source('S1', 'อ่านฉลากโภชนาการก่อนซื้อ\nปริมาณน้ำตาล (กรัม)\nขนม ก 8')
    llm = FakeLLM([call({'query': question})])
    result = Agent(llm, FakeRetriever([hit]), Settings()).run(question)
    assert result['status'] == 'answered'
    assert result['stop_reason'] == 'grounded_route'
    assert result['stats']['model_rounds'] == 1
    assert len(result['citations']) == 1 and 'น้ำตาล' in result['citations'][0]['quote']
