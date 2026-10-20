# ผล evaluation v32 เทียบ v30

ตรวจวันที่ 20 ตุลาคม 2569

## ข้อสรุป

แก้ hash guard ด้วยแผน evaluation ใหม่ที่ตรงกับโค้ดแล้ว การทดสอบ v32 ครบ 60 ข้อมีผลสำเร็จตามการตรวจสาระ 57/60 ข้อ เทียบ v30 ที่เคยได้ 60/60 จาก cache จึงไม่มีข้อที่ตอบถูกเพิ่ม และมี regression 3 ข้อคือ q082, q007 และ q063

โค้ด รายงานและเส้นทางเดโมมีให้ตรวจแล้ว แต่ยังไม่แนะนำให้ถือว่าพร้อมส่งแบบปิดงานแก้ไขครบ ควรแก้สามข้อนี้และทดสอบซ้ำใน evaluation version ถัดไปก่อน โดยยังคง gold และผลที่ล้มเหลวไว้

## สิ่งที่แก้ในรอบนี้

เพิ่ม versioned_evaluation.py และ CLI ที่รับ --version กับ --suite แผนจะล็อกโค้ด runtime และ evaluation harness, โค้ด retrieval ที่นำมาใช้, release data 34 ไฟล์, configs, schemas, prompt, settings และ cache policy ตรวจทั้งก่อนเริ่มและหลังจบ หากมีสิ่งใดเปลี่ยนต้องใช้เลขรุ่นใหม่

Resume ต้องมี run identity ที่ตรงกับ hash ของแผน ตรวจ qid ซ้ำ คำถาม reference answer และ prompt version ก่อนนำผลเก่ามาใช้ แยก cache ต่อ plan โดยเริ่มว่างในครั้งแรก ผล v30 เก็บใน history และ raw run เดิมอยู่ครบ ไม่มีการลบข้อผิดพลาดแล้วรันแทนในชื่อเดิม

ความต่างจาก runtime ที่ล็อกไว้ใน v30 มี llm.py และ config.py ซึ่งแก้ไว้ก่อนงานนี้ ส่วนรอบนี้ไม่ได้แก้ prompt, retrieval หรือ source bound readers Prompt version จึงยังเป็น ncd-gemma-v30 แม้ evaluation version เป็น v32

Gold SHA-256 ยังคงเป็น `680a752e738d7a60f463345c08e3e098934ab945df2183a8bb1e0d97b1f6ddea` โค้ด ข้อมูล config และค่ารันของ v32 ตรงกับ v31: true คำถามและลำดับทั้งสองชุดตรง v30 ทุกข้อ ไม่ได้ส่ง gold ให้โมเดล และไม่แก้ repo ต้นทาง

## เหตุใดจึงมีทั้ง v31 และ v32

v31 เป็นรอบแรกด้วยโค้ดปัจจุบันและ cache ใหม่ Dev เสร็จครบ แต่ extra-dev มี 19 ข้อได้รับผลกระทบจาก class proxy: 18 ข้อได้ HTTP 502 และ q084 ล้มเหลวขณะเรียก reviewer ต่อมาตรวจ endpoint พบ HTTP 530 และหน้า Cloudflare Tunnel error เก็บผลและ API attempts 144 ครั้งไว้ครบ

เมื่อ endpoint กลับมาตอบ HTTP 200 จึงสร้าง v32 ด้วยโค้ดเดียวกัน เริ่ม cache ใหม่ และรันทั้งสองชุดอีกครั้ง ไม่มีการใช้คำตอบจาก v31 เติมใน v32 การเรียกใหม่ยังมี cache ภายในรอบสำหรับ payload ซ้ำได้ จึงอ่าน API attempts และ model rounds แยกกัน

v32 บันทึก API attempts ใหม่ 180 ครั้ง แบ่ง dev 90 และ extra-dev 90 ครั้ง ไม่พบสถานะ error จาก proxy ในรอบนี้ ตัวเลขรวมคำขอที่ retry ไม่ใช่การยืนยันจำนวนครั้งที่ถูกคิดเงิน

## ผลเปรียบเทียบ

| รายการ | v30 | v31 | v32 |
|---|---:|---:|---:|
| Dev ได้สาระครบ | 25/25 | 24/25 | 24/25 |
| Dev งดตอบตรง label | 5/5 | 5/5 | 5/5 |
| Extra-dev ได้สาระครบ | 26/26 | 11 ข้อ ก่อนบริการขัดข้อง | 24/26 |
| Extra-dev งดตอบตรง label | 4/4 | วัดไม่ได้ | 4/4 |
| ผลสำเร็จรวมการงดตอบที่ถูกต้อง | 60/60 | 40/60 และบริการขัดข้อง 19 ข้อ | 57/60 |
| API attempts ใหม่ | 0 | 144 | 180 |

| Automatic metric | Dev v30 | Dev v32 | Extra-dev v32 |
|---|---:|---:|---:|
| Abstention decision accuracy | 1.0000 | 0.9667 | 0.9667 |
| Citation primary evidence hit | 0.7200 | 0.7200 | 0.7308 |
| Mean character F1 | 0.4453 | 0.4439 | 0.4852 |

Decision accuracy ไม่ตรวจว่าตอบสาระครบหรือไม่ เช่น q063 เลือกตอบถูกประเภทแต่ขาดประเด็นที่ถาม Citation hit ตรวจ primary evidence ของ gold ส่วน Character F1 เป็น text overlap ผล extra-dev v30 เดิมไม่ได้บันทึก citation hit และ character F1 ใน schema เดียวกัน จึงไม่ใส่ค่าประมาณแทน

## ข้อที่ยังผิดและสาเหตุ

| QID | สิ่งที่เกิดขึ้น | สิ่งที่ควรแก้ต่อ |
|---|---|---|
| q082 | พบตารางที่ตอบได้ 55 กรัมต่อวัน แต่โมเดลส่ง citations ไม่ครบ ต่อมาใช้ line แทน quote และไม่ส่ง table_cells จน answer_validation_failed พบซ้ำทั้ง v31 และ v32 | ทำ structured output และ repair ให้แยกรูปแบบตารางกับ claim ชัดเจน โดยไม่ผ่อนการตรวจคอลัมน์ |
| q007 | ค้นพบภาคผนวก nephrotic syndrome ซึ่งมี Overweight 25 ถึง 29.9 แล้ว แต่ quote ที่เลือกไม่ครอบคลุมประชากร จึงถูก scope guard ปฏิเสธซ้ำ และมี payload ซ้ำที่ใช้ cache ในรอบ repair | ผูกแถวตารางกับหัวข้อประชากรจาก source จริงและปรับ feedback ให้ซ่อมบริบท ไม่ตอบซ้ำเดิม ห้ามยืมเกณฑ์ BMI ของประชากรทั่วไป |
| q063 | ตอบว่าไม่ควรใช้ ACEIs ร่วมกับ ARBs แต่ไม่บอกคำแนะนำ III และหลักฐาน B ซึ่งอยู่ใน quote Reviewer กลับตัดสินว่าครบ | แยก requested fields และตรวจความครบของระดับคำแนะนำกับหลักฐานโดยตรง ลดการพึ่ง reviewer โมเดลเดียว |

q075, q061, q006, q107 และ q110 ที่เคยแก้มาก่อนยังได้สาระครบใน v32 ส่วน q124 งดตอบตรง gold แต่หยุดด้วย answer_validation_failed จึงไม่ควรอ้างว่าค้นครบทุกเอกสาร

## ผลรายข้อ

### Dev เดิม

| QID | ประเภท | ผล v32 | วิธีตรวจ |
|---|---|---|---|
| q014 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q017 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q113 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q126 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q079 | table | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q125 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q041 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q068 | fact | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q108 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q045 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q080 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q116 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q081 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q093 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q111 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q099 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q082 | table | งดเกินจำเป็น | ตรวจคำตอบกับ gold และ source ใหม่ |
| q120 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q075 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q083 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q115 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q011 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q098 | table | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q119 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q101 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q061 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q106 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q076 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q078 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q118 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |

### Extra-dev

| QID | ประเภท | ผล v32 | วิธีตรวจ |
|---|---|---|---|
| q044 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q065 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q033 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q104 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q039 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q054 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q127 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q049 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q064 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q137 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q024 | condition | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q084 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q018 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q053 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q100 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q058 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q016 | fact | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q091 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q132 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q063 | table | คำตอบไม่ครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q040 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q022 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q006 | table | ตอบได้สาระครบ | ตรวจคำตอบกับ gold และ source ใหม่ |
| q007 | table | งดเกินจำเป็น | ตรวจคำตอบกับ gold และ source ใหม่ |
| q123 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q121 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q122 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q124 | unanswerable | งดตอบถูก | ตรวจคำตอบกับ gold และ source ใหม่ |
| q107 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q110 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |

## การทดสอบและการทำซ้ำ

Tests ผ่าน 176 ข้อ ไม่มี failure, error หรือ skipped มี Starlette deprecation warning หนึ่งรายการ Frozen retrieval replay ตรงเดิมครบ 6 runs การตรวจไฟล์ที่ใช้จากต้นทาง 48 ไฟล์และ PDF 33 ไฟล์ยังได้ hash เดิม

หลังติดตั้งข้อมูลและโมเดลตาม README ใช้ `python -B -m ncd_gemma.cli evaluate plan --version v32 --suite both` เพื่อตรวจ hash guard และใช้ `evaluate agent` พร้อม arguments เดียวกันเพื่อรัน การเริ่มใน clean clone ใช้ class proxy จริง ส่วนเครื่องที่มีผลแล้วจะ resume หากต้องการรอบใหม่ให้เลือกเวอร์ชันใหม่ เช่น v33 ไม่ลบผลหรือแผนเดิม

Raw responses และ cache อยู่ใน ignored folders คำสั่ง `python -B scripts/audit_evaluation.py --version v32` ตรวจเทียบ raw runs ในเครื่องนี้กับ verdict ที่ระบุไว้ ผู้ที่มีเพียง public repo สามารถรันคำตอบและ automatic metrics ใหม่ได้ แต่การตัดสิน semantic correctness ต้องอ่านคำตอบของรอบตนเอง ไม่คัดลอก verdict เดิม

ทั้ง 60 ข้อเป็น exposed development regression และ verdict เป็น coding-agent audit ไม่ใช่ held-out test หรือการรับรองจากผู้เชี่ยวชาญ ความต่างระหว่าง cache เก่ากับ fresh requests ยังมีความแปรผันของบริการร่วมด้วย จึงไม่อ้างว่าการเปลี่ยน evaluation harness ทำให้โมเดลเก่งขึ้นหรือแย่ลงโดยตรง

หลักฐาน: [ผลและแผน v32](../reports/evaluations/v32), [บันทึก outage v31](EVALUATION_V31_TH.md), [ผล tests](../reports/evaluation_tests_2026-10-20.json), [ผลตรวจเดโมล่าสุด](../reports/readiness_2026-10-20.json)
