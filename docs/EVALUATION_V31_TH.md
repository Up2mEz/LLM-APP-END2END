# ผล evaluation v31 เทียบ v30

ตรวจวันที่ 20 ตุลาคม 2569

เอกสารนี้เก็บเหตุการณ์รอบ v31 ขณะบริการขัดข้อง ผลหลังบริการกลับมาอยู่ใน [การประเมิน v32](EVALUATION_V32_TH.md)

## ข้อสรุป

Hash guard ใช้งานกับโค้ดล่าสุดได้แล้วโดยสร้างแผน v31 แยกจาก v30 ชุด dev เดิมได้สาระครบ 24/25 ข้อและงดตอบถูก 5/5 ข้อ เทียบ v30 ที่ได้ 25/25 และ 5/5 จึงตอบถูกเพิ่ม 0 ข้อและถอยลง 1 ข้อคือ q082

Extra-dev ยืนยันคำตอบถูกได้ 11/30 ข้อ อีก 19 ข้อได้รับผลกระทบจาก class proxy ขัดข้อง จึงยังวัดคุณภาพคำตอบทั้งชุดเทียบ v30 ไม่ได้ ไม่ตีความ 19 ข้อนี้ว่าโมเดลตอบผิด

Repository และเอกสารมีผลปัจจุบันพร้อมอธิบาย แต่ยังไม่พร้อมส่งเป็นเดโมที่มั่นใจว่าทำงานครบเส้นทาง ต้องรอ class proxy กลับมา ทดสอบใหม่ และจัดการ q082 รวมทั้งตรวจ public demo URL ในเวลาที่จะส่ง

## วิธีทดลองและความเปลี่ยนแปลง

ใช้ 30 qids เดิมและ extra-dev อีก 30 qids เดิม ลำดับเหมือน v30 ทุกข้อ Gold, corpus, table context และ repo ต้นทางไม่ได้ถูกแก้ แผนตรวจ release data ทั้ง 34 ไฟล์เทียบ SHA-256 เดิมก่อนประเมิน

Gold SHA-256: `680a752e738d7a60f463345c08e3e098934ab945df2183a8bb1e0d97b1f6ddea`

v31 เป็น evaluation version ส่วน prompt ยังใช้ ncd-gemma-v30 เพราะไม่ได้แก้ prompt หรือวิธีตอบในรอบนี้ ความต่างของ runtime จาก lock v30 คือ llm.py ที่มี connection retry และ config.py สำหรับ deployment ซึ่งแก้ไว้ก่อนหน้า งานรอบนี้เพิ่ม versioned evaluation harness และ CLI

แผนใหม่ล็อกโค้ด runtime และ harness, โค้ด retrieval ที่นำมาใช้, config, schemas, ข้อมูล, prompt และค่ารัน ทุกครั้งจะตรวจแผนก่อนเริ่มและหลังจบ ส่วน resume ตรวจ fingerprint ของแผน qid คำถาม reference answer และ prompt version ถ้าไม่ตรงจะหยุด ไม่เขียนทับแผนเดิม

ใช้ gemma-4-E4B-it, temperature 0 และไม่เกิน 6 model rounds ตาม budget ที่ v30 บันทึกไว้ ส่วน v31 ล็อกเพิ่มว่าใช้ 3 searches, request timeout 45 วินาที และเวลารวม 150 วินาทีต่อคำถาม แผน v30 ไม่ได้บันทึก settings ทุก field v31 เริ่ม cache แยกว่างต่อชุด ขณะที่ v30 replay จาก cached responses เดิม การทดลองนี้จึงตรวจการทำงานปัจจุบันได้ แต่แยกผลการแก้โค้ดจากความแปรผันของบริการไม่ได้

บันทึก API attempts ใหม่ 144 ครั้ง แบ่งเป็น dev 91 และ extra-dev 53 ครั้ง รวมคำขอที่ล้มเหลวด้วย ไม่ใช่จำนวนคำตอบสำเร็จหรือจำนวนครั้งที่ยืนยันว่าถูกคิดเงิน ไม่มีการส่ง gold หรือ reference answers ให้โมเดล

## ผลที่วัดได้

| รายการ | v30 | v31 |
|---|---:|---:|
| Dev ตอบได้สาระครบ | 25/25 | 24/25 |
| Dev งดตอบตรง label | 5/5 | 5/5 |
| Dev decision accuracy | 1.0000 | 0.9667 |
| Dev citation primary evidence hit | 0.7200 | 0.7200 |
| Dev character F1 | 0.4453 | 0.4439 |
| Extra-dev ยืนยันผลสำเร็จในรอบรัน | 30/30 | 11/30 |
| Extra-dev บริการขัดข้องจนวัดสาระไม่ได้ | 0 | 19 |
| API attempts ใหม่ทั้งสองชุด | 0 | 144 |

Dev มีคำตอบหรือหลักฐานเปลี่ยน 4 ข้อคือ q079, q068, q082 และ q098 ตรวจใหม่กับ gold และข้อความอ้างอิงแล้ว สามข้อยังได้สาระครบ ส่วน q082 งดตอบเกินจำเป็น Extra-dev มี q024 เปลี่ยนถ้อยคำแต่ยังครบ ส่วนคำตอบที่เหมือน v30 จะสืบทอด verdict ได้ต่อเมื่อ fingerprint ของ answer, status, citations และ cited sources ตรงกัน

## ข้อที่ยังมีปัญหา

q082 ถามโปรตีนสำหรับเด็กหญิงอายุ 13 ถึง 15 ปีในเกณฑ์ปี 2546 ซึ่ง gold ระบุ 55 กรัมต่อวัน Trace แสดงว่าค้นพบตารางแล้ว แต่คำตอบขาด citations จากนั้นใช้ line แทน quote และครั้งถัดไปไม่ส่ง table_cells ตาม schema จึงจบด้วย answer_validation_failed ภายใน 4 model rounds หลังปฏิเสธรูปแบบสามครั้ง ปัญหานี้เป็น structured output และ repair ไม่ใช่กรณีไม่มีเอกสาร

q084 สร้าง candidate แล้วแต่การเรียก reviewer ได้ HTTP 502 จึงจบด้วย verification_unavailable และ status insufficient_evidence Automatic metrics นับเป็น false abstention ตาม status แต่ audit แยกเป็น service_unavailable เพราะ trace ชี้ว่าบริการตรวจคำตอบล้มเหลว

อีก 18 ข้อจบด้วย proxy_http_502: q018, q053, q100, q058, q016, q091, q132, q063, q040, q022, q006, q007, q123, q121, q122, q124, q107, q110 ไม่มีคำตอบสมบูรณ์ให้ตรวจ semantic correctness

การตรวจ /v1/models หลังรันพบ HTTP 530 พร้อมหน้า Cloudflare Tunnel error ที่ llm.nat-d.uk เป็นหลักฐานว่าปลายทางให้บริการไม่สำเร็จ ณ เวลาตรวจ ไม่ใช่ข้อพิสูจน์ว่า API key ผิดหรือ hash guard มีปัญหา

ควรปรับการซ่อม JSON ให้ตรงชนิด structured output และเพิ่มการตรวจรูปแบบก่อนส่งซ่อม โดยคงการตรวจแถวและคอลัมน์ตาราง ส่วน outage ควรแยกสถานะ verification unavailable ออกจากหลักฐานไม่พอ และพิจารณา bounded backoff กับ circuit breaker สำหรับ 5xx โดยไม่วนเรียกไม่จำกัด ทั้งหมดนี้เป็นงานถัดไป ยังไม่ได้เปลี่ยน runtime ใน v31

## ผลรายข้อ

### Dev เดิม

| QID | ประเภท | ผล v31 | วิธีตรวจ |
|---|---|---|---|
| q014 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q017 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q113 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q126 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q079 | table | ตอบได้สาระครบ | ตรวจคำตอบและ trace ใหม่ |
| q125 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q041 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q068 | fact | ตอบได้สาระครบ | ตรวจคำตอบและ trace ใหม่ |
| q108 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q045 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q080 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q116 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q081 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q093 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q111 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q099 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q082 | table | งดเกินจำเป็น | ตรวจคำตอบและ trace ใหม่ |
| q120 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q075 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q083 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q115 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q011 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q098 | table | ตอบได้สาระครบ | ตรวจคำตอบและ trace ใหม่ |
| q119 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |
| q101 | condition | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q061 | fact | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q106 | multi_page | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q076 | number_unit | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q078 | table | ตอบได้สาระครบ | Fingerprint ตรง v30 |
| q118 | unanswerable | งดตอบถูก | Fingerprint ตรง v30 |

### Extra-dev

| QID | ประเภท | ผล v31 | วิธีตรวจ |
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
| q024 | condition | ตอบได้สาระครบ | ตรวจคำตอบและ trace ใหม่ |
| q084 | condition | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q018 | condition | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q053 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q100 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q058 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q016 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q091 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q132 | fact | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q063 | table | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q040 | table | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q022 | table | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q006 | table | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q007 | table | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q123 | unanswerable | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q121 | unanswerable | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q122 | unanswerable | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q124 | unanswerable | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q107 | multi_page | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |
| q110 | multi_page | บริการขัดข้อง | ตรวจคำตอบและ trace ใหม่ |

## การทำซ้ำและข้อจำกัด

รัน `python -B -m ncd_gemma.cli evaluate plan --version v31 --suite both` เพื่อตรวจแผน และใช้ `evaluate agent` ด้วย arguments เดียวกันเพื่อรันใน clean clone ที่มีข้อมูล โมเดลและ key ตาม README ในเครื่องที่มีผลแล้วคำสั่งจะ resume โดยไม่ลบผลผิดพลาด หากต้องเริ่มรอบใหม่ให้เลือกเลขรุ่นใหม่ เช่น v32

ผล unit/API tests ผ่าน 176 ข้อ มี deprecation warning หนึ่งรายการ Frozen retrieval คำนวณใหม่จาก saved hits ตรงเดิมครบ 6 runs ผลเหล่านี้ไม่ยืนยันว่า class proxy พร้อมให้บริการ

ทั้งสองชุดเปิดผลและใช้ปรับระบบมาก่อน การตรวจสาระเป็น coding-agent audit ไม่ใช่ blind review โดยแพทย์ ไม่ใช่ held-out accuracy และไม่ควรอ้างว่าระบบพร้อมใช้ตัดสินใจทางคลินิก

หลักฐาน: [แผนและผล v31](../reports/evaluations/v31), [บันทึก tests](../reports/evaluation_tests_2026-10-20.json), [แผนและผล v30 เดิม](../reports/history), [สถานะ proxy](../reports/evaluations/v31/proxy_availability.json)
