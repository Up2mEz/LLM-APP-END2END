"""Small, source-independent intent checks and evidence-bound field hints."""
import re


def greeting_reply(question: str) -> str | None:
    """A standalone greeting is outside document QA; mixed questions still search."""
    simple = re.sub(r'[\s!?.。！？,，]+', '', question).casefold()
    if simple in {'hello', 'hi', 'hey', 'สวัสดี', 'สวัสดีครับ', 'สวัสดีค่ะ', 'หวัดดี'}:
        return 'สวัสดีค่ะ ฉันช่วยค้นคำตอบจากเอกสารแนวทาง NCD ภาษาไทย ลองถามเรื่องเบาหวาน ความดัน หรือโรคไตได้เลย'
    return None


def label_field_hints(question: str, evidence: list[dict]) -> list[dict]:
    """Name a label field only when its exact heading and topic occur in evidence.

    This does not choose a medical target or infer a nutrition value. It helps
    the model distinguish a field name from advice to read a label.
    """
    if 'ฉลาก' not in question or not any(t in question for t in ('ข้อมูลอะไร', 'ดูอะไร', 'มองหาอะไร', 'ตรวจอะไร')):
        return []
    found = []
    for source in evidence:
        lines = source['text'].splitlines()
        if not any('ฉลาก' in line for line in lines):
            continue
        for line in lines:
            for match in re.finditer(r'ปริมาณ\s*([ก-๙A-Za-z]+)', line):
                topic = match.group(1)
                if len(topic) < 3 or topic not in question:
                    continue
                item = {'source_id': source['source_id'], 'field': match.group(0)}
                if item not in found:
                    found.append(item)
    return found[:3]


def broad_kidney_diet(question):
    if not re.search(r'โรคไต|ไตเสื่อม|ไตเรื้อรัง', question):
        return False
    if re.search(r'ระยะ\s*[1-5๑-๕]|ฟอกไต|ล้างไต|ผลเลือด|โพแทสเซียม|ฟอสฟอรัส|eGFR|DASH|โซเดียม|โปรตีน|แป้ง', question, re.I):
        return False
    return bool(re.search(r'(?:ควร|ต้อง|ห้าม|งด|เลี่ยง).{0,12}(?:กิน|อาหาร)|(?:กิน|อาหาร).{0,8}(?:อะไร|ไร|แบบไหน)', question))


KIDNEY_SCOPE_REMINDER = """คำถามนี้เป็นคำถามอาหารโรคไตแบบกว้างและยังไม่มีข้อมูลระยะโรค
ตอบเฉพาะคำแนะนำทั่วไปเรื่องลดเค็มจาก evidence ที่ให้ เช่นอาหารดองเค็มหรืออาหารแปรรูปที่เอกสารระบุ ใช้ 1 citation ที่ตรงที่สุด
ไม่ต้องไล่รายการอาหารที่มีโพแทสเซียม ฟอสฟอรัส โปรตีน นม ผัก หรือผลไม้ที่ควรงด และห้ามกำหนดปริมาณสำหรับคนนี้
ปิดท้ายโดยบอกว่ายังไม่ทราบระยะโรค ผลเลือด และการฟอกไต จึงยังระบุอาหารที่ต้องงดเฉพาะตัวไม่ได้ แล้วถามระยะโรค/การฟอกไต
การชี้แจงข้อมูลที่ยังไม่ทราบและถามรายละเอียดไม่ใช่การอ้างข้อเท็จจริงจากเอกสาร จึงไม่ต้องมี citation เพิ่ม
ใช้ JSON status answered พร้อม answer 2–3 ประโยคและ citations แบบ source_id/start_line/end_line เท่านั้น"""
