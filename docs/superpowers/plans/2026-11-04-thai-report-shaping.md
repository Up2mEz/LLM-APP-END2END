# Thai Report Mark Positioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แก้ตำแหน่งสระบนและวรรณยุกต์ที่ทับกันใน PDF โดยรักษาเนื้อหาและรายงาน 4–8 หน้า

**Architecture:** พิสูจน์ปัญหาด้วย specimen ของ font/shaper ก่อนเลือกแก้ renderer ห้ามใช้การเพิ่ม line spacing แทนการจัดตำแหน่ง glyph ภายในคำ ตรวจทั้ง body/bold/header/table แล้วจึงสร้างรายงานใหม่จาก source เดิม

**Tech Stack:** Python 3.12, ReportLab/Thai font, PDF renderer ที่มีอยู่; ทดสอบ HarfBuzz availability ก่อนเลือกวิธีแก้ ไม่ติดตั้งหรือเปลี่ยนเครื่องมือในช่วงวางแผน

**Spec:** ผู้ใช้ส่งภาพคำ “นี้” ที่วรรณยุกต์ซ้อนสระ; ข้อกำหนดรายงานใน `2026-11-04-capstone-evaluation-spec.md` และรูปเล่มตัวหนังสือดำ ฟอนต์มาตรฐานไทย ไม่มีวันที่ปรับปรุง

## Global Constraints

- PLAN ONLY รอผู้ใช้บอกให้ทำ ห้ามแก้ report builder/PDF ตอนนี้
- ไม่แตะ evaluation, gold, metrics หรือเนื้อหาข้อสรุปเพื่อแก้ typography
- ไม่เปลี่ยน code points ลบวรรณยุกต์ แทรก space ในคำ หรือแปลงรายงานทั้งเล่มเป็นภาพ
- ตัวหนังสือสีดำ font ไทยมาตรฐาน embedded; 4–8 หน้า; ชื่ออาจารย์และรหัสนักศึกษาคงเดิม

## Review Focus

- สระบน+วรรณยุกต์ “นี้ ที่ ผู้ใช้ ชี้ ชั้น ตั้งขึ้น” ต้องไม่ชนกัน (Task 1)
- ตัวหนา/ตารางกับตัวปกติใช้ font face ต่างกัน ต้อง shape ถูกทั้งคู่ (Task 1)
- ข้อความไทย+อังกฤษ+ตัวเลขและจุดตัดบรรทัด ต้องไม่แยก grapheme ผิด (Task 1)
- คัดลอกจาก PDF ต้องยังได้ข้อความไทยเดิม ไม่หายวรรณยุกต์ (Task 2)
- เปลี่ยน font/renderer แล้วหน้าล้นหรือ glyph ตกหล่น ต้องตรวจทั้ง 8 หน้า ไม่ดูเฉพาะ specimen (Task 2)

---

### Task 1: หาสาเหตุและทำ specimen ที่อ่านถูก

**Files:** Create `scripts/check_thai_report_typography.py`; diagnostic outputs `private/report_typography/`; Read `scripts/build_submission_report.py`

**Interfaces:** `build_specimen(output: Path, font_path: Path, font_index: int, shaping: bool) -> Path`; ตรวจ installed ReportLab/HarfBuzz และ font cmap/mark positioning โดยไม่อ้างว่ามี shapable=True แล้วถูกแน่นอน

- [ ] สร้าง specimen เนื้อหา 16 pt และ bold 18/20 pt ใช้คำใน Review Focus, อักษรต่ำ/สูง, ตัวเลข 150 และ Recall@5 ทั้งคำเดี่ยวและท้ายบรรทัด
- [ ] Render ที่ 200–300 dpi และ crop คำชัด ๆ เพื่อยืนยัน reproduction ด้วย Angsana New TTC ปัจจุบัน เก็บภาพก่อนแก้
- [ ] ตรวจว่าฟอนต์มี mark positioning และ renderer shaping ทำงานจริงหรือไม่ เปรียบเทียบ shaping on/off กับ Thai TTF ที่มี mark anchors โดยยังไม่แก้ report production
- [ ] เสนอ candidate เดียวที่ผ่านภาพและการ extract text; ถ้าเครื่องมือปัจจุบันทำไม่ได้ เสนอเปลี่ยน renderer แยกก่อน implementation ไม่สุ่มเปลี่ยน font แล้วประกาศผ่าน

### Task 2: ใช้ผลที่พิสูจน์แล้วกับรายงาน

**Files:** Modify `scripts/build_submission_report.py`; output `output/pdf/NCD_EVIDENCE_SUBMISSION_67070060.pdf`; receipt `reports/report_typography_verification.json`

**Interfaces:** ใช้ font/renderer configuration ที่ Task 1 ตรวจผ่าน; receipt มี fonts/versions, shaping setting, specimen images, page count, extracted text/color validation และหน้าที่ตรวจภาพ

- [ ] แก้ registration/shaping เฉพาะสาเหตุที่ Task 1 ยืนยัน โดยคง text และข้อมูลเดิม หากต้องเปลี่ยน engine ทั้งตัวให้ส่งแผนเฉพาะเพิ่มก่อน
- [ ] สร้าง PDF ใหม่แล้วตรวจจำนวนหน้า 4–8, text colors=[0], embedded fonts และเทียบ normalized extracted text กับ source เพื่อจับสระ/วรรณยุกต์หาย
- [ ] Render ทุกหน้า ตรวจคำตัวอย่างในบทคัดย่อ หัวข้อ ตาราง และท้ายบรรทัดที่ขยาย 200–300%; ตรวจไม่ทับ/ไม่ตัด ไม่ยอมรับจาก text extraction อย่างเดียว
- [ ] ส่งภาพก่อน/หลังและ PDF ให้ผู้ใช้ตรวจ; ไม่แก้เนื้อหาคะแนนจนกว่า eval ใหม่จะเสร็จและได้รับอนุมัติ

## Self-Review / Handoff

นี่เป็นแผน diagnosis ก่อนเลือกวิธีแก้ ไม่อ้าง root cause จากภาพเพียงอย่างเดียว Review Focus ทั้งห้าครอบคลุมโดย specimen/visual/full-document checks งานนี้แยกจาก eval และรอคำสั่งผู้ใช้เช่นกัน
