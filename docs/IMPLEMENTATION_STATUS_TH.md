# สถานะงาน 12 ตุลาคม 2026

แอปอยู่ใน D:\KMITL\LLMapp\ncd-gemma ใช้สำเนา gold/index เดิม ไม่แก้ repo ต้นทาง ตรวจ frozen source 48 ไฟล์และ PDF ที่อ่านเพิ่ม 33 ไฟล์ด้วย SHA-256 แล้วไม่เปลี่ยน ไม่ใช่การยืนยัน clean tree ทั้ง repo

## ทำแล้ว

- Gemma class proxy/OpenAI SDK และ native search_docs agent loop
- PDF table transcription จากตำแหน่งเซลล์ เก็บ merged headers/row labels และ provenance; ไม่สร้าง retrieval index ใหม่
- โมเดลเลือกเซลล์ ระบบแสดงชื่อคอลัมน์คู่ค่าจริง แก้การสลับค่ารวมกับอาหารใน q113/q079/q080
- Citation/reviewer ใช้ line selection, bounded evidence recovery, narrow duplicate-quote JSON repair และ rate-limit retry หนึ่งครั้งภายใต้ deadline
- Local configuration 6 model rounds, 3 searches, 150 วินาที และ HTTP attempts นับจริง แผน dev ล็อก implementation/table/gold/prompt hashes
- คำถามโรคไตแบบกว้างตอบคำแนะนำทั่วไปพร้อมถามระยะโรค ไม่เหมารวมอาหารที่ต้องงดทั้งหมด
- UI คลินิกเดิม เพิ่มข้อความสถานะที่แยกไม่พบเอกสารกับยังยืนยันคำตอบไม่ได้ และ label สำหรับข้อมูลตารางจัดรูป
- Tests 103 passed, 0 failed/error/skipped, Starlette deprecation warning 1 รายการ
- Dev 30 ข้อเดิม v13: ตอบ 23 งด 7; false abstention 2, answered-unanswerable 0; ไม่มี transport error
- Abstention decision accuracy 0.9333, citation hit 0.5600, character F1 0.2805 ไม่ใช่ clinical accuracy
- ตรวจเนื้อหา: สาระหลักตรง 14 ข้อ, ผิด/ไม่ครบชัดเจน 4, ต้องตรวจบริบท/ความครบถ้วน 5, false abstention 2, งดตรง label 5

## ข้อจำกัด

v8 มี false abstention 14 ข้อ รุ่นปัจจุบันตอบเพิ่ม 12 แต่เพียง 6 ข้อกลับมาตอบสาระหลักครบ อีก 6 ข้อยังมีปัญหา ตัวเลขตอบได้มากขึ้นจึงไม่ใช่หลักฐานว่าแก้คำตอบถูกทั้งหมด อ่าน DEV_COMPARISON_TH.md

v13 dev ใช้ cached payload เหมือน v12 และคำตอบ/citations ตรงกันทั้ง 30 ข้อ ไม่อ้างว่าเป็น independent repeat generation เก็บ v9–v11 ที่ยังผิดและติด HTTP 429 ครบ

## งานส่ง

มี capability families 1/2/3/4/6 และ measured retrieval baseline ตาม rubric แต่ยังไม่ส่ง Project: public corpus/reproduction, push GitHub, ผู้จัดทำใน PDF, demo video/deployed URL และ Submit ยังเหลือ ตามขอบเขตใช้ corpus ในเครื่องก่อน
