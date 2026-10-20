"""Render the v31 comparison note from the recorded audits and metrics."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "reports/evaluations/v31"


def read(name):
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


def main():
    comparison = read("comparison.json")
    dev, extra = read("dev_semantic_audit.json"), read("extra_semantic_audit.json")
    dm, em = read("dev_metrics.json"), read("extra_metrics.json")
    notes = [
        "# ผล evaluation v31 เทียบ v30",
        "",
        "ตรวจวันที่ 20 ตุลาคม 2569",
        "",
        "เอกสารนี้เก็บเหตุการณ์รอบ v31 ขณะบริการขัดข้อง ผลหลังบริการกลับมาอยู่ใน [การประเมิน v32](EVALUATION_V32_TH.md)",
        "",
        "## ข้อสรุป",
        "",
        f"Hash guard ใช้งานกับโค้ดล่าสุดได้แล้วโดยสร้างแผน v31 แยกจาก v30 ชุด dev เดิมได้สาระครบ {len(dev['core_matches'])}/25 ข้อและงดตอบถูก 5/5 ข้อ เทียบ v30 ที่ได้ 25/25 และ 5/5 จึงตอบถูกเพิ่ม 0 ข้อและถอยลง 1 ข้อคือ q082",
        "",
        f"Extra-dev ยืนยันคำตอบถูกได้ {extra['strict_correct']}/30 ข้อ อีก {len(extra['service_unavailable_qids'])} ข้อได้รับผลกระทบจาก class proxy ขัดข้อง จึงยังวัดคุณภาพคำตอบทั้งชุดเทียบ v30 ไม่ได้ ไม่ตีความ 19 ข้อนี้ว่าโมเดลตอบผิด",
        "",
        "Repository และเอกสารมีผลปัจจุบันพร้อมอธิบาย แต่ยังไม่พร้อมส่งเป็นเดโมที่มั่นใจว่าทำงานครบเส้นทาง ต้องรอ class proxy กลับมา ทดสอบใหม่ และจัดการ q082 รวมทั้งตรวจ public demo URL ในเวลาที่จะส่ง",
        "",
        "## วิธีทดลองและความเปลี่ยนแปลง",
        "",
        "ใช้ 30 qids เดิมและ extra-dev อีก 30 qids เดิม ลำดับเหมือน v30 ทุกข้อ Gold, corpus, table context และ repo ต้นทางไม่ได้ถูกแก้ แผนตรวจ release data ทั้ง 34 ไฟล์เทียบ SHA-256 เดิมก่อนประเมิน",
        "",
        f"Gold SHA-256: `{comparison['gold_sha256']}`",
        "",
        "v31 เป็น evaluation version ส่วน prompt ยังใช้ ncd-gemma-v30 เพราะไม่ได้แก้ prompt หรือวิธีตอบในรอบนี้ ความต่างของ runtime จาก lock v30 คือ llm.py ที่มี connection retry และ config.py สำหรับ deployment ซึ่งแก้ไว้ก่อนหน้า งานรอบนี้เพิ่ม versioned evaluation harness และ CLI",
        "",
        "แผนใหม่ล็อกโค้ด runtime และ harness, โค้ด retrieval ที่นำมาใช้, config, schemas, ข้อมูล, prompt และค่ารัน ทุกครั้งจะตรวจแผนก่อนเริ่มและหลังจบ ส่วน resume ตรวจ fingerprint ของแผน qid คำถาม reference answer และ prompt version ถ้าไม่ตรงจะหยุด ไม่เขียนทับแผนเดิม",
        "",
        "ใช้ gemma-4-E4B-it, temperature 0 และไม่เกิน 6 model rounds ตาม budget ที่ v30 บันทึกไว้ ส่วน v31 ล็อกเพิ่มว่าใช้ 3 searches, request timeout 45 วินาที และเวลารวม 150 วินาทีต่อคำถาม แผน v30 ไม่ได้บันทึก settings ทุก field v31 เริ่ม cache แยกว่างต่อชุด ขณะที่ v30 replay จาก cached responses เดิม การทดลองนี้จึงตรวจการทำงานปัจจุบันได้ แต่แยกผลการแก้โค้ดจากความแปรผันของบริการไม่ได้",
        "",
        f"บันทึก API attempts ใหม่ {comparison['new_api_calls_recorded']} ครั้ง แบ่งเป็น dev {dm['new_api_calls_recorded']} และ extra-dev {em['new_api_calls_recorded']} ครั้ง รวมคำขอที่ล้มเหลวด้วย ไม่ใช่จำนวนคำตอบสำเร็จหรือจำนวนครั้งที่ยืนยันว่าถูกคิดเงิน ไม่มีการส่ง gold หรือ reference answers ให้โมเดล",
        "",
        "## ผลที่วัดได้",
        "",
        "| รายการ | v30 | v31 |",
        "|---|---:|---:|",
        f"| Dev ตอบได้สาระครบ | 25/25 | {len(dev['core_matches'])}/25 |",
        "| Dev งดตอบตรง label | 5/5 | 5/5 |",
        f"| Dev decision accuracy | 1.0000 | {dm['decision_accuracy']:.4f} |",
        f"| Dev citation primary evidence hit | 0.7200 | {dm['citation_primary_evidence_hit_rate_answerable']:.4f} |",
        f"| Dev character F1 | 0.4453 | {dm['mean_character_f1_answerable']:.4f} |",
        f"| Extra-dev ยืนยันผลสำเร็จในรอบรัน | 30/30 | {extra['strict_correct']}/30 |",
        f"| Extra-dev บริการขัดข้องจนวัดสาระไม่ได้ | 0 | {len(extra['service_unavailable_qids'])} |",
        f"| API attempts ใหม่ทั้งสองชุด | 0 | {comparison['new_api_calls_recorded']} |",
        "",
        "Dev มีคำตอบหรือหลักฐานเปลี่ยน 4 ข้อคือ q079, q068, q082 และ q098 ตรวจใหม่กับ gold และข้อความอ้างอิงแล้ว สามข้อยังได้สาระครบ ส่วน q082 งดตอบเกินจำเป็น Extra-dev มี q024 เปลี่ยนถ้อยคำแต่ยังครบ ส่วนคำตอบที่เหมือน v30 จะสืบทอด verdict ได้ต่อเมื่อ fingerprint ของ answer, status, citations และ cited sources ตรงกัน",
        "",
        "## ข้อที่ยังมีปัญหา",
        "",
        "q082 ถามโปรตีนสำหรับเด็กหญิงอายุ 13 ถึง 15 ปีในเกณฑ์ปี 2546 ซึ่ง gold ระบุ 55 กรัมต่อวัน Trace แสดงว่าค้นพบตารางแล้ว แต่คำตอบขาด citations จากนั้นใช้ line แทน quote และครั้งถัดไปไม่ส่ง table_cells ตาม schema จึงจบด้วย answer_validation_failed ภายใน 4 model rounds หลังปฏิเสธรูปแบบสามครั้ง ปัญหานี้เป็น structured output และ repair ไม่ใช่กรณีไม่มีเอกสาร",
        "",
        "q084 สร้าง candidate แล้วแต่การเรียก reviewer ได้ HTTP 502 จึงจบด้วย verification_unavailable และ status insufficient_evidence Automatic metrics นับเป็น false abstention ตาม status แต่ audit แยกเป็น service_unavailable เพราะ trace ชี้ว่าบริการตรวจคำตอบล้มเหลว",
        "",
        "อีก 18 ข้อจบด้วย proxy_http_502: " + ", ".join(em["error_qids"]) + " ไม่มีคำตอบสมบูรณ์ให้ตรวจ semantic correctness",
        "",
        "การตรวจ /v1/models หลังรันพบ HTTP 530 พร้อมหน้า Cloudflare Tunnel error ที่ llm.nat-d.uk เป็นหลักฐานว่าปลายทางให้บริการไม่สำเร็จ ณ เวลาตรวจ ไม่ใช่ข้อพิสูจน์ว่า API key ผิดหรือ hash guard มีปัญหา",
        "",
        "ควรปรับการซ่อม JSON ให้ตรงชนิด structured output และเพิ่มการตรวจรูปแบบก่อนส่งซ่อม โดยคงการตรวจแถวและคอลัมน์ตาราง ส่วน outage ควรแยกสถานะ verification unavailable ออกจากหลักฐานไม่พอ และพิจารณา bounded backoff กับ circuit breaker สำหรับ 5xx โดยไม่วนเรียกไม่จำกัด ทั้งหมดนี้เป็นงานถัดไป ยังไม่ได้เปลี่ยน runtime ใน v31",
        "",
        "## ผลรายข้อ",
        "",
    ]
    labels = {"correct": "ตอบได้สาระครบ", "correct_abstention": "งดตอบถูก",
              "false_abstention": "งดเกินจำเป็น", "service_unavailable": "บริการขัดข้อง",
              "partial": "ไม่ครบ", "wrong": "ผิด", "error": "ระบบผิดพลาด"}
    for title, audit in (("Dev เดิม", dev), ("Extra-dev", extra)):
        notes += [f"### {title}", "", "| QID | ประเภท | ผล v31 | วิธีตรวจ |",
                  "|---|---|---|---|"]
        for row in audit["details"]:
            method = "Fingerprint ตรง v30" if row["inherited_identical_v30"] else "ตรวจคำตอบและ trace ใหม่"
            notes.append(f"| {row['qid']} | {row['type']} | {labels[row['verdict']]} | {method} |")
        notes.append("")
    notes += [
        "## การทำซ้ำและข้อจำกัด",
        "",
        "รัน `python -B -m ncd_gemma.cli evaluate plan --version v31 --suite both` เพื่อตรวจแผน และใช้ `evaluate agent` ด้วย arguments เดียวกันเพื่อรันใน clean clone ที่มีข้อมูล โมเดลและ key ตาม README ในเครื่องที่มีผลแล้วคำสั่งจะ resume โดยไม่ลบผลผิดพลาด หากต้องเริ่มรอบใหม่ให้เลือกเลขรุ่นใหม่ เช่น v32",
        "",
        "ผล unit/API tests ผ่าน 176 ข้อ มี deprecation warning หนึ่งรายการ Frozen retrieval คำนวณใหม่จาก saved hits ตรงเดิมครบ 6 runs ผลเหล่านี้ไม่ยืนยันว่า class proxy พร้อมให้บริการ",
        "",
        "ทั้งสองชุดเปิดผลและใช้ปรับระบบมาก่อน การตรวจสาระเป็น coding-agent audit ไม่ใช่ blind review โดยแพทย์ ไม่ใช่ held-out accuracy และไม่ควรอ้างว่าระบบพร้อมใช้ตัดสินใจทางคลินิก",
        "",
        "หลักฐาน: [แผนและผล v31](../reports/evaluations/v31), [บันทึก tests](../reports/evaluation_tests_2026-10-20.json), [แผนและผล v30 เดิม](../reports/history), [สถานะ proxy](../reports/evaluations/v31/proxy_availability.json)",
    ]
    path = ROOT / "docs/EVALUATION_V31_TH.md"
    path.write_text("\n".join(notes).rstrip() + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
