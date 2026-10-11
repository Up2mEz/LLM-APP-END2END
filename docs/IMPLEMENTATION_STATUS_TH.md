# สถานะงาน 11 ตุลาคม 2026

แอปอยู่ใน `D:\KMITL\LLMapp\ncd-gemma` ใช้สำเนา gold, chunks, vectors และ retrieval code จากต้นทาง งานนี้ไม่มีการแก้ไฟล์ใน repository ต้นทาง ตรวจ SHA-256 ของไฟล์ที่อ่านทั้ง 48 ไฟล์แล้วไม่พบความเปลี่ยนแปลง ขอบเขตนี้ไม่ใช่การยืนยันว่า working tree ทั้ง repo ไม่มีงานของผู้อื่น

## ทำแล้ว

- สร้าง Git repository และ environment Python 3.12.13 แยกภายในโฟลเดอร์ใหม่
- นำเข้าไฟล์ตาม allow-list พร้อมบันทึก provenance และตรวจ SHA-256 ก่อน/หลัง copy
- ต่อ OpenAI SDK กับ `gemma-4-E4B-it` ผ่าน class proxy ของวิชา เก็บ key เฉพาะ `.env` ที่ Git ignore
- เพิ่ม native `search_docs`, agent loop, argument/answer validation, citation quote validation, bounded repair, timeout, cache และ trace
- ใช้ retrieval variant B เดิม ไม่มีการเปลี่ยน gold, chunking, vectors หรือ ranking algorithm
- เพิ่ม FastAPI และหน้าเว็บภาษาไทยสำหรับคำถาม คำตอบ แหล่งอ้างอิง และ trace
- ล็อก dev evaluation 30 ข้อ พร้อม evaluator ที่แยก reference answer ออกจาก model context
- เตรียม proposal, README, dependency lock, demo script และ PDF ฉบับร่าง 6 หน้า

## หลักฐานการตรวจ

| การตรวจ | ผลและขอบเขต |
|---|---|
| Unit/API tests | 30 passed, 0 failed/error/skipped; ใช้ fake model/retriever |
| Pytest JUnit | XML อ่านได้ครบ 30 ข้อ; runtime แจ้ง WMI exception ระหว่างดึง hostname ในขั้นสร้าง XML แต่ process exit 0 และ pytest สรุป 30 passed |
| Native proxy probe | เรียก class proxy จริง ได้ `search_docs` tool call; ยังไม่ได้ส่งข้อความ corpus |
| Retrieval probe | โหลด BGE-M3/index จริง สำเร็จในประมาณ 298 วินาที แล้วค้นได้ 3 hits |
| Frozen metrics | คำนวณซ้ำจาก saved ranked hits ตรงเดิมทั้ง dev/test A/B/C รวม 6 runs; ไม่ใช่รัน retrieval test ใหม่ |
| Source integrity | ไฟล์ต้นทางที่ใช้ทั้ง 48 ไฟล์ hash ไม่เปลี่ยน |
| Local HTTP health | HTTP endpoint ตอบพร้อม ตั้งค่า proxy และพบข้อมูล; server ยังไม่ได้โหลด retriever จนกว่าจะมีคำถาม |
| PDF | 6 หน้า ตรวจภาพ render ทั้ง 6 หน้าแล้ว ไม่มีข้อความล้นหรือ glyph ไทยหาย |

ผล frozen test ของ B: Recall@5 0.8846, MRR@10 0.7374 เทียบ A: 0.8077, 0.6181 ใช้ answerable 52 ข้อ ผลนี้ไม่ใช่ answer accuracy ของ Gemma

## ยังไม่เสร็จและเหตุผล

1. การรัน Gemma dev 30 ข้อยังไม่เริ่ม ระบบอนุมัติอัตโนมัติปฏิเสธการส่งคำถามและข้อความ corpus ภายในไปยัง `https://llm.nat-d.uk` โดยขอสิทธิ์ส่งข้อมูลเฉพาะส่วนนี้เพิ่ม มีคำถามยืนยันส่งให้ผู้ใช้แล้ว ไม่มีการเปลี่ยนช่องทางเพื่อหลบการปฏิเสธ
2. การตรวจ UI ด้วย browser ยังไม่สำเร็จ เพราะ Codex เปิด webview ใหม่ไม่ได้ (attach timeout) แม้ local HTTP health ตอบได้ จึงยังไม่มีหลักฐาน browser end-to-end
3. PDF เป็นฉบับร่าง ต้องเติมผลจริง ตัวอย่าง success/failure และข้อมูลผู้จัดทำหลังประเมินครบ
4. Q1 public reproducibility ยังติดสิทธิ์เผยแพร่ corpus เดิม ยังไม่มี remote repository หรือการ push ถ้าต้องใช้ public subset ให้ version และประเมินใหม่
5. Q3 มี demo script แต่ยังไม่มีวิดีโอ 3–6 นาทีหรือ deployed URL ที่ผู้ตรวจเข้าถึงได้

## ขั้นตอนต่อเมื่ออนุญาตส่งข้อมูลแล้ว

รัน `.venv312\Scripts\python -m ncd_gemma.cli evaluate agent` ตาม plan ที่ล็อกไว้ ตรวจคำตอบและ failure จากไฟล์จริง หากต้องแก้ prompt หรือ protocol ให้เก็บ version/ผลเก่าและสร้างแผน version ใหม่อย่างชัดเจน จากนั้นตรวจ UI, สร้าง PDF ใหม่ และจัด public deliverable ตามสิทธิ์ข้อมูลที่ยืนยันแล้ว
