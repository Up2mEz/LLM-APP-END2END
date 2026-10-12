from types import SimpleNamespace

from ncd_gemma.scope_guard import scope_mismatch


def check(question, answer, evidence):
    citations = [SimpleNamespace(source_id=f'S{i}') for i in range(1, len(evidence)+1)]
    sources = {f'S{i}': {'text': text} for i, text in enumerate(evidence, 1)}
    return scope_mismatch(question, answer, citations, sources)


def test_missed_dose_must_name_the_same_drug():
    question = 'ถ้าลืมกิน ezetimibe หนึ่งวันควรเพิ่มยาเป็นสองเท่าหรือไม่'
    generic = 'ถ้าลืมยาเม็ดลดน้ำตาล ไม่ควรกินเพิ่มในวันถัดไป'
    assert check(question, 'ไม่ควรกินสองเม็ด [S1]', [generic])
    assert check(question, 'ไม่ควรกินสองเม็ด [S1]', ['คำแนะนำกรณีลืมกิน ezetimibe: ไม่ควรกินสองเม็ด']) is None


def test_population_specific_bmi_rejects_nearby_general_table():
    question = 'ผู้ป่วยไตเนโฟรติกจัด BMI ช่วงใดว่าน้ำหนักเกิน'
    assert check(question, '23.0-24.9 [S1]', ['สำหรับประชากรเอเชีย BMI 23.0-24.9 เป็นน้ำหนักเกิน'])
    assert check(question, '25-29.9 [S1]', ['ภาคผนวกโรคไตเนโฟรติก: Overweight BMI 25-29.9']) is None


def test_comorbid_diet_needs_both_disease_scopes_in_evidence_pack():
    question = 'เด็กที่เป็นเบาหวานและมีโรคไตร่วมควรกินของว่างได้พลังงานเท่าไร'
    generic = 'เด็กอายุ 6-8 ปี พลังงานจากอาหารว่างไม่ควรเกิน 140 กิโลแคลอรี'
    assert check(question, '140 กิโลแคลอรี [S1]', [generic])
    both = ['แนวทางเบาหวานกับโรคไตในเด็ก: ของว่าง 140 กิโลแคลอรี']
    assert check(question, '140 กิโลแคลอรี [S1]', both) is None
