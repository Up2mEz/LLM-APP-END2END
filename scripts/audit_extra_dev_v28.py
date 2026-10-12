"""Record manual semantic review of the exposed extra-dev-v28 regression.

Verdicts were checked against the current answer and citation text. The v26
audit supplies notes for unchanged correct cases; overrides document every
changed verdict. This script does not alter gold, source, or serving logic.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/extra_dev_v26_semantic_audit.json"
RUN = ROOT / "private/runs/extra-dev-v28/answers.jsonl"
PLAN = ROOT / "reports/extra_dev_v28_plan.json"

OVERRIDES = {
    "q033": ("correct", "เลือกหลักสูตรระดับกลางปี 2568 ได้ระยะเวลารวม 5 ชั่วโมง ไม่สลับกับระดับกลาง II ปี 2566"),
    "q127": ("correct", "ตอบร้อยละ 95 จากข้อความ T2D ใน source ที่อ้าง; claim ที่คัดไม่ตรงถูกตัดออกก่อนตรวจ"),
    "q058": ("correct", "lexical admission ดึงข้อความที่ระบุให้แยกเก็บน้ำหนักและส่วนสูง"),
    "q016": ("correct", "ตอบเด็กและวัยทำงานตรง citation; legacy line citation ถูกซ่อมจากข้อความที่ตรง source เพียงตำแหน่งเดียว"),
    "q063": ("correct", "ตอบไม่ควรใช้ ACEIs ร่วม ARBs พร้อมระดับ III และหลักฐาน B จากตาราง"),
    "q040": ("correct", "อ่านแถว HTML ปี 2567 ที่มีผู้ร่วม 468 คนและ remission 98 คน"),
    "q006": ("false_abstention", "การค้นรอบสองมีตาราง secondary MCD แถว Infection Virus, parasites ใน S11/S12 แต่ Gemma ยังเลือกงดตอบ"),
    "q007": ("correct", "เลือกช่วง Overweight 25-29.9 จากตาราง nephrotic แทนเกณฑ์ BMI เอเชียทั่วไป; คำตอบยังสั้นและไม่ระบุหน่วย"),
    "q123": ("correct_abstention", "ไม่ถ่ายคำแนะนำการลืมยาเบาหวานไปใช้กับ ezetimibe; หยุดเมื่อ citation ไม่มียานี้"),
    "q124": ("correct_abstention", "ไม่ใช้พลังงานของว่างเด็กทั่วไปกับโจทย์เด็กที่มีเบาหวานร่วมโรคไตโดยไม่มีหลักฐานตรง"),
    "q107": ("false_abstention", "S1 มี SLED สำหรับความดันต่ำและ S2 มี conventional intermittent สำหรับไหลเวียนคงที่ แต่โมเดลตอบเพียงด้านเดียวซ้ำจน completeness gate ปฏิเสธ"),
    "q110": ("false_abstention", "S1/S2 มีข้าวขาว 1 ทัพพีต่อ 1 คาร์บ และ S3 มีโคล่า 1 กระป๋อง 1.7 คาร์บ แต่ prune invalid claims เหลือ 1 จาก 5 claims แล้ว reviewer เลือก claim ID ไม่ตรง"),
}


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    raw = RUN.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    previous = {d["qid"]: d for d in base["details"]}
    current = {r["qid"]: r for r in rows}
    if len(rows) != len(current) or list(current) != plan["qids"] or set(previous) != set(current):
        raise ValueError("Audit must match both complete locked runs")
    details = []
    for qid in plan["qids"]:
        row = current[qid]
        verdict, note = OVERRIDES.get(qid, (previous[qid]["verdict"], previous[qid]["note"]))
        status = row["prediction"]["status"]
        if (verdict in {"correct", "wrong", "partial", "answered_unanswerable"}) != (status == "answered"):
            raise ValueError(f"Verdict/status mismatch: {qid}")
        details.append({"qid": qid, "type": row["type"], "answerable": row["answerable"],
                        "status": status, "verdict": verdict, "note": note,
                        "cited_documents": sorted({c["document_id"] for c in row["prediction"]["citations"]})})
    counts = Counter(d["verdict"] for d in details)
    strict = {"correct", "correct_abstention"}
    improved = [d["qid"] for d in details if d["verdict"] in strict and previous[d["qid"]]["verdict"] not in strict]
    regressed = [d["qid"] for d in details if d["verdict"] not in strict and previous[d["qid"]]["verdict"] in strict]
    report = {"plan_id": plan["id"], "comparison": base["plan_id"],
              "raw_answers_sha256": hashlib.sha256(raw).hexdigest(), "n": len(details),
              "verdict_counts": dict(counts), "strict_correct": counts["correct"] + counts["correct_abstention"],
              "strict_correct_rate": round((counts["correct"] + counts["correct_abstention"]) / len(details), 4),
              "strict_improved_qids": improved, "strict_regressed_qids": regressed,
              "strict_net_gain": len(improved) - len(regressed),
              "review_basis": "Coding-agent semantic review of all 30 answers against unchanged gold and cited source; same exposed dev split, not blinded clinical review",
              "details": details}
    (ROOT / "reports/extra_dev_v28_semantic_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n", "verdict_counts", "strict_correct", "strict_net_gain")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
