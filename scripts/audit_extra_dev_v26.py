"""Record the human semantic review of the locked extra-dev-v26 run.

The judgments below are review notes, not a model-generated metric and not
training labels for the serving path. This script never writes gold or source.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "private/runs/extra-dev-v26/answers.jsonl"
PLAN = ROOT / "reports/extra_dev_v26_plan.json"

# Verdicts: correct, partial, wrong, false_abstention, correct_abstention,
# answered_unanswerable. "Correct" means the requested core fact is supported;
# presentation flaws are called out separately in notes.
JUDGMENTS = {
    "q044": ("correct", "ตอบอย่างน้อยปีละครั้งตรงหลักฐาน; ไม่กล่าวถึงการติดตามถี่ขึ้นเมื่อผิดปกติ แต่คำถามถามขั้นต่ำ"),
    "q065": ("correct", "ตรวจความดันทุกปีตั้งแต่อายุ 30 ปีตรงเอกสาร"),
    "q033": ("wrong", "ตอบ 4.5 ชั่วโมงจากหลักสูตรระดับกลาง II ปี 2566 แทนระดับกลางปี 2568 ที่ gold อ้าง 5 ชั่วโมง; สลับ edition"),
    "q104": ("correct", "ปัสสาวะกลางคืนตั้งแต่ 2 ครั้งตรงหลักฐาน"),
    "q039": ("correct", "คาร์บ 1 ส่วนประมาณ 15-18 กรัมตรงหลักฐาน"),
    "q054": ("correct", "ตัวอย่างอาหาร 121 ตัวอย่างตรงหลักฐาน; ไม่สับสนกับคน 124 คน"),
    "q127": ("false_abstention", "หลักฐาน S1/S2 ระบุร้อยละ 95 ชัด แต่ claim exact-copy ถูกปฏิเสธ 3 รอบ"),
    "q049": ("correct", "ตอบความเสี่ยงถูกตัดเท้าหรือขาตรงคำถามและหลักฐาน"),
    "q064": ("correct", "เริ่มยาลดความดัน 2 ชนิดเมื่อ >=150/90 ตรงเงื่อนไข; คำถามถามจำนวนยา"),
    "q137": ("correct", "การผ่าตัดวุ้นตาเมื่อเลือดไม่หายหรือจอตาถูกพังผืดดึงรั้งตรงหลักฐาน"),
    "q024": ("correct", "เกลือและน้ำคั่งทำให้คุมความดันยากและหัวใจทำงานหนัก; เนื้อหาซ้ำ citation 2 ครั้ง"),
    "q084": ("correct", "นมไขมันต่ำสำหรับผู้สูงอายุที่ดื่มนมแล้วไม่ท้องเสียตรงหลักฐาน"),
    "q018": ("correct", "ACEi หรือ ARB เป็นตัวเลือกแรกเมื่อมี albuminuria; ตอบซ้ำหลาย citation โดยไม่จำเป็น"),
    "q053": ("correct", "น้ำเปล่าหรือน้ำสมุนไพรไม่หวานตรงหลักฐาน; มีขึ้นบรรทัดกลางประโยคจาก OCR"),
    "q100": ("correct", "ระบุโรงพยาบาลเขาสุกิมตรงหลักฐาน"),
    "q058": ("false_abstention", "ผลค้น 10 แหล่งไม่ดึงหน้าที่ระบุให้แยกน้ำหนักและส่วนสูง; retrieval miss"),
    "q016": ("false_abstention", "S1 มีเด็กและวัยทำงานตรง gold แต่ citation line range นอก passage 3 รอบ"),
    "q091": ("correct", "เนื้อวัวและเนื้อควายตรงหลักฐาน"),
    "q132": ("correct", "ภาชนะทนการแทงทะลุและการกัดกร่อนตรงหลักฐาน; มีรายละเอียดฝากับฉลากเกินที่ถาม"),
    "q063": ("false_abstention", "review ยืนยัน III B แล้ว แต่ quantity guard มอง Roman III กับ B ว่าไม่มีปริมาณ"),
    "q040": ("false_abstention", "ผลค้นได้หัวตารางกงหราแต่ไม่ดึงแถวปี 2567 ที่มี 468 และ 98; ตาราง HTML ถูกแยกข้าม chunk"),
    "q022": ("correct", "BUN >100 หรือมีแนวโน้มถึง 100 มก./ดล.ตรงหลักฐาน; ข้อความซ้ำ"),
    "q006": ("false_abstention", "S1 มี Infection Virus, parasites แต่ quantity guard อ่าน กี่ ใน เกี่ยวข้อง เป็นคำถามตัวเลข"),
    "q007": ("wrong", "ใช้ BMI ประชากรเอเชียทั่วไป 23-24.9 แทนตารางโรคไตเนโฟรติก S1 ที่ระบุ 25-29.9"),
    "q123": ("answered_unanswerable", "นำคำแนะนำกรณีลืมยาเบาหวานไปใช้กับ ezetimibe ทั้งที่ citation ไม่กล่าวถึงยานี้"),
    "q121": ("correct_abstention", "เอกสารให้ปริมาณโซเดียมของน้ำปลา แต่ไม่ระบุยี่ห้อ"),
    "q122": ("correct_abstention", "เอกสารชุดนี้ไม่ให้ AQI cutoff เฉพาะผู้มีความดันสูง"),
    "q124": ("answered_unanswerable", "นำพลังงานอาหารว่างเด็กทั่วไป 140 kcal ไปใช้กับเด็กที่มีเบาหวานและ CKD โดยไม่มีหลักฐานตรงโรคร่วม"),
    "q107": ("partial", "ตอบ SLED สำหรับความดันต่ำถูก แต่ไม่ตอบ intermittent มาตรฐานสำหรับผู้ไหลเวียนคงที่"),
    "q110": ("correct", "ข้าวขาว 1 ทัพพี = 1 คาร์บ และโคล่า 1 กระป๋อง = 1.7 คาร์บครบ"),
}


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    raw = RUN.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    by_qid = {row["qid"]: row for row in rows}
    if len(rows) != len(by_qid) or list(by_qid) != plan["qids"] or set(JUDGMENTS) != set(by_qid):
        raise ValueError("Review does not match the locked 30-question run")
    details = []
    for qid in plan["qids"]:
        row = by_qid[qid]
        verdict, note = JUDGMENTS[qid]
        details.append({
            "qid": qid,
            "type": row["type"],
            "answerable": row["answerable"],
            "status": row["prediction"]["status"],
            "verdict": verdict,
            "note": note,
            "cited_documents": sorted({c["document_id"] for c in row["prediction"]["citations"]}),
        })
    counts = Counter(item["verdict"] for item in details)
    report = {
        "plan_id": plan["id"],
        "raw_answers_sha256": hashlib.sha256(raw).hexdigest(),
        "n": len(details),
        "verdict_counts": dict(counts),
        "strict_correct": counts["correct"] + counts["correct_abstention"],
        "strict_correct_rate": round((counts["correct"] + counts["correct_abstention"]) / len(details), 4),
        "partial": counts["partial"],
        "review_basis": "Manual comparison of each answer with gold and retrieved citation text; core factual correctness, not prose quality or clinical validation",
        "details": details,
    }
    target = ROOT / "reports/extra_dev_v26_semantic_audit.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("n", "verdict_counts", "strict_correct", "strict_correct_rate")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
