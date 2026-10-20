"""Publish the completed v32 comparison while preserving the v31 outage record."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "reports/evaluations/v32"


def read(name):
    return json.loads((FOLDER / name).read_text(encoding="utf-8"))


def main():
    report = read("comparison.json")
    dev, extra = read("dev_semantic_audit.json"), read("extra_semantic_audit.json")
    dm, em = read("dev_metrics.json"), read("extra_metrics.json")
    success = dev["strict_correct"] + extra["strict_correct"]
    lines = [
        "# ผล evaluation v32 เทียบ v30",
        "",
        "ตรวจวันที่ 20 ตุลาคม 2569",
        "",
        "## ข้อสรุป",
        "",
        f"แก้ hash guard ด้วยแผน evaluation ใหม่ที่ตรงกับโค้ดแล้ว การทดสอบ v32 ครบ 60 ข้อมีผลสำเร็จตามการตรวจสาระ {success}/60 ข้อ เทียบ v30 ที่เคยได้ 60/60 จาก cache จึงไม่มีข้อที่ตอบถูกเพิ่ม และมี regression 3 ข้อคือ q082, q007 และ q063",
        "",
        "โค้ด รายงานและเส้นทางเดโมมีให้ตรวจแล้ว แต่ยังไม่แนะนำให้ถือว่าพร้อมส่งแบบปิดงานแก้ไขครบ ควรแก้สามข้อนี้และทดสอบซ้ำใน evaluation version ถัดไปก่อน โดยยังคง gold และผลที่ล้มเหลวไว้",
        "",
        "## สิ่งที่แก้ในรอบนี้",
        "",
        "เพิ่ม versioned_evaluation.py และ CLI ที่รับ --version กับ --suite แผนจะล็อกโค้ด runtime และ evaluation harness, โค้ด retrieval ที่นำมาใช้, release data 34 ไฟล์, configs, schemas, prompt, settings และ cache policy ตรวจทั้งก่อนเริ่มและหลังจบ หากมีสิ่งใดเปลี่ยนต้องใช้เลขรุ่นใหม่",
        "",
        "Resume ต้องมี run identity ที่ตรงกับ hash ของแผน ตรวจ qid ซ้ำ คำถาม reference answer และ prompt version ก่อนนำผลเก่ามาใช้ แยก cache ต่อ plan โดยเริ่มว่างในครั้งแรก ผล v30 เก็บใน history และ raw run เดิมอยู่ครบ ไม่มีการลบข้อผิดพลาดแล้วรันแทนในชื่อเดิม",
        "",
        "ความต่างจาก runtime ที่ล็อกไว้ใน v30 มี llm.py และ config.py ซึ่งแก้ไว้ก่อนงานนี้ ส่วนรอบนี้ไม่ได้แก้ prompt, retrieval หรือ source bound readers Prompt version จึงยังเป็น ncd-gemma-v30 แม้ evaluation version เป็น v32",
        "",
        f"Gold SHA-256 ยังคงเป็น `{report['gold_sha256']}` โค้ด ข้อมูล config และค่ารันของ v32 ตรงกับ v31: {str(report['same_code_and_settings_as_v31']).lower()} คำถามและลำดับทั้งสองชุดตรง v30 ทุกข้อ ไม่ได้ส่ง gold ให้โมเดล และไม่แก้ repo ต้นทาง",
        "",
        "## เหตุใดจึงมีทั้ง v31 และ v32",
        "",
        "v31 เป็นรอบแรกด้วยโค้ดปัจจุบันและ cache ใหม่ Dev เสร็จครบ แต่ extra-dev มี 19 ข้อได้รับผลกระทบจาก class proxy: 18 ข้อได้ HTTP 502 และ q084 ล้มเหลวขณะเรียก reviewer ต่อมาตรวจ endpoint พบ HTTP 530 และหน้า Cloudflare Tunnel error เก็บผลและ API attempts 144 ครั้งไว้ครบ",
        "",
        "เมื่อ endpoint กลับมาตอบ HTTP 200 จึงสร้าง v32 ด้วยโค้ดเดียวกัน เริ่ม cache ใหม่ และรันทั้งสองชุดอีกครั้ง ไม่มีการใช้คำตอบจาก v31 เติมใน v32 การเรียกใหม่ยังมี cache ภายในรอบสำหรับ payload ซ้ำได้ จึงอ่าน API attempts และ model rounds แยกกัน",
        "",
        f"v32 บันทึก API attempts ใหม่ {report['new_api_calls_recorded']} ครั้ง แบ่ง dev {dm['new_api_calls_recorded']} และ extra-dev {em['new_api_calls_recorded']} ครั้ง ไม่พบสถานะ error จาก proxy ในรอบนี้ ตัวเลขรวมคำขอที่ retry ไม่ใช่การยืนยันจำนวนครั้งที่ถูกคิดเงิน",
        "",
        "## ผลเปรียบเทียบ",
        "",
        "| รายการ | v30 | v31 | v32 |",
        "|---|---:|---:|---:|",
        f"| Dev ได้สาระครบ | 25/25 | 24/25 | {len(dev['core_matches'])}/25 |",
        f"| Dev งดตอบตรง label | 5/5 | 5/5 | {len(dev['label_correct_abstentions'])}/5 |",
        f"| Extra-dev ได้สาระครบ | 26/26 | 11 ข้อ ก่อนบริการขัดข้อง | {len(extra['core_matches'])}/26 |",
        f"| Extra-dev งดตอบตรง label | 4/4 | วัดไม่ได้ | {len(extra['label_correct_abstentions'])}/4 |",
        f"| ผลสำเร็จรวมการงดตอบที่ถูกต้อง | 60/60 | 40/60 และบริการขัดข้อง 19 ข้อ | {success}/60 |",
        f"| API attempts ใหม่ | 0 | 144 | {report['new_api_calls_recorded']} |",
        "",
        "| Automatic metric | Dev v30 | Dev v32 | Extra-dev v32 |",
        "|---|---:|---:|---:|",
        f"| Abstention decision accuracy | 1.0000 | {dm['decision_accuracy']:.4f} | {em['decision_accuracy']:.4f} |",
        f"| Citation primary evidence hit | 0.7200 | {dm['citation_primary_evidence_hit_rate_answerable']:.4f} | {em['citation_primary_evidence_hit_rate_answerable']:.4f} |",
        f"| Mean character F1 | 0.4453 | {dm['mean_character_f1_answerable']:.4f} | {em['mean_character_f1_answerable']:.4f} |",
        "",
        "Decision accuracy ไม่ตรวจว่าตอบสาระครบหรือไม่ เช่น q063 เลือกตอบถูกประเภทแต่ขาดประเด็นที่ถาม Citation hit ตรวจ primary evidence ของ gold ส่วน Character F1 เป็น text overlap ผล extra-dev v30 เดิมไม่ได้บันทึก citation hit และ character F1 ใน schema เดียวกัน จึงไม่ใส่ค่าประมาณแทน",
        "",
        "## ข้อที่ยังผิดและสาเหตุ",
        "",
        "| QID | สิ่งที่เกิดขึ้น | สิ่งที่ควรแก้ต่อ |",
        "|---|---|---|",
        "| q082 | พบตารางที่ตอบได้ 55 กรัมต่อวัน แต่โมเดลส่ง citations ไม่ครบ ต่อมาใช้ line แทน quote และไม่ส่ง table_cells จน answer_validation_failed พบซ้ำทั้ง v31 และ v32 | ทำ structured output และ repair ให้แยกรูปแบบตารางกับ claim ชัดเจน โดยไม่ผ่อนการตรวจคอลัมน์ |",
        "| q007 | ค้นพบภาคผนวก nephrotic syndrome ซึ่งมี Overweight 25 ถึง 29.9 แล้ว แต่ quote ที่เลือกไม่ครอบคลุมประชากร จึงถูก scope guard ปฏิเสธซ้ำ และมี payload ซ้ำที่ใช้ cache ในรอบ repair | ผูกแถวตารางกับหัวข้อประชากรจาก source จริงและปรับ feedback ให้ซ่อมบริบท ไม่ตอบซ้ำเดิม ห้ามยืมเกณฑ์ BMI ของประชากรทั่วไป |",
        "| q063 | ตอบว่าไม่ควรใช้ ACEIs ร่วมกับ ARBs แต่ไม่บอกคำแนะนำ III และหลักฐาน B ซึ่งอยู่ใน quote Reviewer กลับตัดสินว่าครบ | แยก requested fields และตรวจความครบของระดับคำแนะนำกับหลักฐานโดยตรง ลดการพึ่ง reviewer โมเดลเดียว |",
        "",
        "q075, q061, q006, q107 และ q110 ที่เคยแก้มาก่อนยังได้สาระครบใน v32 ส่วน q124 งดตอบตรง gold แต่หยุดด้วย answer_validation_failed จึงไม่ควรอ้างว่าค้นครบทุกเอกสาร",
        "",
        "## ผลรายข้อ",
        "",
    ]
    labels = {"correct":"ตอบได้สาระครบ", "correct_abstention":"งดตอบถูก", "false_abstention":"งดเกินจำเป็น",
              "partial":"คำตอบไม่ครบ", "wrong":"ตอบผิด", "service_unavailable":"บริการขัดข้อง"}
    for title, audit in (("Dev เดิม", dev), ("Extra-dev", extra)):
        lines += [f"### {title}", "", "| QID | ประเภท | ผล v32 | วิธีตรวจ |", "|---|---|---|---|"]
        for d in audit["details"]:
            method = "Fingerprint ตรง v30" if d["inherited_identical_v30"] else "ตรวจคำตอบกับ gold และ source ใหม่"
            lines.append(f"| {d['qid']} | {d['type']} | {labels[d['verdict']]} | {method} |")
        lines.append("")
    lines += [
        "## การทดสอบและการทำซ้ำ",
        "",
        "Tests ผ่าน 176 ข้อ ไม่มี failure, error หรือ skipped มี Starlette deprecation warning หนึ่งรายการ Frozen retrieval replay ตรงเดิมครบ 6 runs การตรวจไฟล์ที่ใช้จากต้นทาง 48 ไฟล์และ PDF 33 ไฟล์ยังได้ hash เดิม",
        "",
        "Clean clone จาก GitHub เมื่อ 20 ตุลาคม 2026 ดาวน์โหลด release ตรวจ hashes ของข้อมูล 34 ไฟล์ replay retrieval 6 runs และตรวจแผน v32 ทั้งสองชุดผ่าน หลังแก้ LF/CRLF ใน Git ของไฟล์ที่นำมาใช้สามไฟล์ให้ตรงกับ raw bytes ที่ประเมิน เนื้อหาและแผนไม่เปลี่ยน การตรวจใช้ Python environment เดิม ไม่มี LLM calls และยังไม่ใช่การทดสอบติดตั้ง dependencies ใหม่ ดู [หลักฐาน](../reports/remote_release_validation_2026-10-20.json)",
        "",
        "หลังติดตั้งข้อมูลและโมเดลตาม README ใช้ `python -B -m ncd_gemma.cli evaluate plan --version v32 --suite both` เพื่อตรวจ hash guard และใช้ `evaluate agent` พร้อม arguments เดียวกันเพื่อรัน การเริ่มใน clean clone ใช้ class proxy จริง ส่วนเครื่องที่มีผลแล้วจะ resume หากต้องการรอบใหม่ให้เลือกเวอร์ชันใหม่ เช่น v33 ไม่ลบผลหรือแผนเดิม",
        "",
        "Raw responses และ cache อยู่ใน ignored folders คำสั่ง `python -B scripts/audit_evaluation.py --version v32` ตรวจเทียบ raw runs ในเครื่องนี้กับ verdict ที่ระบุไว้ ผู้ที่มีเพียง public repo สามารถรันคำตอบและ automatic metrics ใหม่ได้ แต่การตัดสิน semantic correctness ต้องอ่านคำตอบของรอบตนเอง ไม่คัดลอก verdict เดิม",
        "",
        "ทั้ง 60 ข้อเป็น exposed development regression และ verdict เป็น coding-agent audit ไม่ใช่ held-out test หรือการรับรองจากผู้เชี่ยวชาญ ความต่างระหว่าง cache เก่ากับ fresh requests ยังมีความแปรผันของบริการร่วมด้วย จึงไม่อ้างว่าการเปลี่ยน evaluation harness ทำให้โมเดลเก่งขึ้นหรือแย่ลงโดยตรง",
        "",
        "หลักฐาน: [ผลและแผน v32](../reports/evaluations/v32), [บันทึก outage v31](EVALUATION_V31_TH.md), [ผล tests](../reports/evaluation_tests_2026-10-20.json), [ผลตรวจเดโมล่าสุด](../reports/readiness_2026-10-20.json)",
    ]
    path = ROOT / "docs/EVALUATION_V32_TH.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
