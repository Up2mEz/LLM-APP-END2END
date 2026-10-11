# สถานะงาน 11 ตุลาคม 2026

แอปและ evaluation อยู่ใน D:\KMITL\LLMapp\ncd-gemma ใช้สำเนาข้อมูลจากต้นทาง ตรวจ SHA-256 ของไฟล์ต้นทางที่นำมาใช้ 48 ไฟล์แล้วไม่เปลี่ยน ไม่ใช่การยืนยันว่า repo ต้นทางทั้งชุดไม่มีงานของผู้อื่น

## ทำแล้ว

- Gemma ผ่าน class proxy/OpenAI SDK, native search_docs, safe arguments parser และแก้ HTTP 400 จาก tool history/empty tools
- Structured answer/citation validation, ตรวจคำตอบแยกประเด็นพร้อม evidence quotes และซ่อมผลตรวจได้หนึ่งครั้ง ภายใน 4 model calls/150 วินาที
- Quantity guard สำหรับคำถาม “กี่” ที่ไม่มีจำนวนในคำตอบ โดยไม่นับ source marker เป็นจำนวน ไม่มี qid/gold hard-code ใน serving
- ล็อก evaluation plan กับ qids, gold/prompt hashes และ hashes ของ implementation ป้องกัน resume ผลต่างรุ่นปนกัน
- UI ตาม Hallmark โทนฟ้า–ขาว, mascot หนังสือ, เงาและ motion, responsive, copy/clear/help/source disclosure, สถานะยังยืนยันคำตอบไม่ได้
- Unit/API tests 68 passed, 0 failed/error/skipped มี Starlette deprecation warning 1 รายการ
- Dev 30 ข้อเดิมครบ รุ่น v8: ตอบ 11 งดตอบ 19; completed 22, verification_invalid 5, unsupported_answer 2, answer_missing_quantity 1
- Abstention decision accuracy 0.5333, citation primary-evidence hit rate 0.3200, character F1 0.1319 ไม่ใช่ clinical accuracy
- Browser v8: success q045, ระงับ q113/q120, responsive 320/375/414/768 px ไม่มี overflow หรือ targets ต่ำกว่า 44×44 px หลังแก้ปุ่มล้าง; ไม่พบ console errors
- Frozen retrieval metrics ตรงเดิมทั้ง 6 runs: B Recall@5 0.8846, MRR@10 0.7374 บน answerable test 52 ข้อ
- รายงาน PDF 6 หน้าอัปเดตจากผลจริงและตรวจภาพครบทุกหน้าแล้ว

## ข้อจำกัดที่ยังเปิดอยู่

v8 ระงับคำตอบผิด/ไม่ครบเดิม q113/q080/q120 ได้ แต่ยังมี false abstention 14 ข้อ และ q041/q076 ที่ต้องทบทวนบริบทหรือความครบถ้วน รุ่นใหม่ตอบน้อยกว่า v5 จึงไม่อ้างว่า overall accuracy ดีขึ้น ความเข้มงวดของ reviewer ยังมีต้นทุนต่อ coverage

รอบ v6–v8 ใช้ cached candidates เมื่อ payload ตรงกัน และเรียก proxy ใหม่ 21, 15, 0 ครั้งตามลำดับ เก็บผลเดิมและรอบที่แย่ลงไว้ครบ ดู reports/agent_comparison.json และ docs/ANSWER_REVIEW_TH.md

## งานส่ง

มี capability families 1/2/3/4/6, baseline และ measured retrieval improvement ตาม rubric แต่ยังไม่ใช่การส่ง Project เสร็จ: public corpus/reproduction, push GitHub, ข้อมูลผู้จัดทำใน PDF, demo video/deployed URL และ Submit ยังเหลือ ตามขอบเขตที่ผู้ใช้เลือกให้ใช้ corpus ในเครื่องก่อน อ่าน PROJECT_READINESS_TH.md สำหรับสถานะแต่ละ deliverable
