# สถานะงาน 12 ตุลาคม 2026

เวอร์ชันที่รันในเครื่องคือ v30. แอปอยู่ที่ `D:\KMITL\LLMapp\ncd-gemma` แยกจาก repo Thai NCD Guideline QA ต้นทาง ใช้ snapshot ที่มี hash ใน `provenance/source_snapshot.json` โดยไม่มี runtime import จากต้นทาง ไม่แก้ gold และไม่แก้ repo ต้นทาง

- Tests 164 ผ่าน, failed/error/skipped 0; มี Starlette deprecation warning 1 รายการ ผล test ใช้ fake model/retriever ส่วนผล Gemma จริงบันทึกแยก
- Dev 30 ชุดแรก: v30 ตอบ 25 งด 5; ผลตรวจสาระที่สืบทอดจาก v29 คือ 25/25 answerable และงดตรง label 5/5 เพราะ answer/status/citations ทั้ง 30 ข้อตรงกันทุกข้อ ค่า citation primary-evidence hit 0.72 และ character F1 0.4453 ไม่ใช่ clinical accuracy
- Extra-dev 30 ที่ v26 ยังไม่เคยใช้ปรับ: ตรวจสาระถูกหรืองดถูก 19/30 (false abstention 6, wrong 2, answered-unanswerable 2, partial 1) v28 หลังแก้ได้ 27/30 โดยเหลือ false abstention q006/q107/q110; v29 และ v30 ได้ 30/30 โดยตอบ 26 งดตาม label 4 ข้อ การรัน v28–v30 เป็น regression บนชุดที่เปิดผลและใช้ปรับแล้ว
- v29 เพิ่มตัวอ่านหลักฐานแบบ source-bound สำหรับตาราง secondary MCD, คู่เปรียบเทียบการฟอกเลือด, และหน่วยคาร์บอาหาร พร้อมตรวจ source ID, edition, ข้อความอ้าง และค่าจริง v30 เพิ่ม guard คำถามปฏิเสธหรือเปลี่ยนกลุ่มโรคแล้วทดสอบ counterexamples เพื่อจำกัด false positive
- ทั้ง dev 30 และ extra-dev 30 ของ v30 บันทึก HTTP attempts ใหม่ 0 ครั้ง เพราะ tool/model payload ที่ต้องใช้ตรง cache เดิม ไม่ใช่การสุ่มผลใหม่หรือ external replication
- คำทักทายล้วน เช่น `hello` ตอบ `out_of_scope` ใน 0 model rounds; คำถามเอกสารใช้ native `search_docs` agent loop แล้วตรวจคำตอบก่อนส่งกลับ
- Source allow-list 48 ไฟล์, PDF ที่อ่าน 33 ไฟล์ และ gold SHA-256 ตรงกับ snapshot เดิม การตรวจนี้ครอบคลุมเฉพาะรายการที่นำเข้ามา ไม่ใช่การรับรอง clean tree ทุกไฟล์ของ repo ต้นทาง

Workflow อยู่ใน `docs/WORKFLOW_AND_REUSE_TH.md`; ผลรายข้อและข้อจำกัดอยู่ใน `docs/DEV_COMPARISON_TH.md` และ `reports/extra_dev_v30_semantic_audit.json`. ผล 25/25 และ 30/30 มาจาก development questions ที่ตรวจโดย coding agent ไม่ใช่ independent clinical expert review หรือ held-out test ใหม่ ยังมี OCR typo, คำตอบตารางยาว และการงด q118 ผ่าน reviewer rejection ที่ไม่พิสูจน์ว่าค้นเอกสารครบทุกหน้า

ชุดส่ง Project ยังไม่ครบ: corpus เดิมมีข้อจำกัดการเผยแพร่ จึงยังไม่ push ไป public GitHub, ยังต้องตรวจชื่อผู้จัดทำใน PDF และจัดทำ demo URL/วิดีโอที่ผู้ตรวจเข้าถึงได้ แล้วจึง Submit ตามขอบเขตที่ผู้ใช้กำหนดให้ใช้ corpus ในเครื่องก่อน
