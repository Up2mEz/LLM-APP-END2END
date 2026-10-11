# สถานะงาน 11 ตุลาคม 2026

ทำงานใน D:\KMITL\LLMapp\ncd-gemma โดยใช้สำเนา gold, chunks, vectors และ retrieval เดิม ตรวจไฟล์ต้นทางที่เกี่ยวข้อง 48 ไฟล์แล้ว SHA-256 ไม่เปลี่ยน ขอบเขตนี้ไม่ใช่การยืนยันว่า repo ต้นทางทั้งชุดไม่มีงานของผู้อื่น

## ทำแล้ว

- OpenAI SDK + gemma-4-E4B-it ผ่าน class proxy, native search_docs, bounded agent loop, cache และ trace
- Safe parser สำหรับ Gemma native arguments, JSON normalization ก่อนส่ง tool history และละ tool_choice เมื่อไม่มี tools
- Answer schema, ตรวจ quote/source IDs รวม grouped citations และตรวจคำตอบกับหลักฐานอีกหนึ่งรอบด้วย Gemma ตัวเดิม รวมใน budget 4 calls/150 วินาที
- UI ภาษาไทยสำหรับผู้ใช้ทั่วไป โทนฟ้า–ขาวตาม Hallmark, mascot หนังสือ, copy/clear/help/source disclosure และ animation ที่รองรับ reduced motion
- Unit/API tests 50 passed, 0 failed/error/skipped มี Starlette deprecation warning 1 รายการ
- Dev 30 ข้อเดิมครบ: v5 ตอบ 18 งดตอบ 12; completion 28/30, abstention decision accuracy 0.7000, citation primary-evidence hit rate 0.5200, character F1 0.2344
- Browser tests: ตอบจริง q045, งดตอบ q125, copy, anchors, details, examples, clear และ dialog; UI ใช้ cached proxy completions จาก evaluation เพื่อไม่สิ้นเปลืองการเรียกซ้ำ
- ตรวจ layout 320/375/414/768 px และ desktop 1280×800; ทดสอบ reduced motion แล้วคืนค่า override
- Frozen retrieval metrics ตรงเดิม 6 runs: B Recall@5 0.8846, MRR@10 0.7374 บน answerable test 52 ข้อ ไม่ใช่ answer accuracy
- ตั้ง origin ไป Up2mEz/LLM-APP-END2END แล้ว ไม่มีการ push หรือเผยแพร่ corpus

## ข้อจำกัดที่พบจริง

อ่าน ANSWER_REVIEW_TH.md สำหรับทั้ง 30 ข้อ ยังมี table misreading, missing sub-answers, population/context mismatch และ false acceptance ของ verifier การทดสอบ code ผ่านไม่ได้แปลว่าคำตอบสุขภาพถูกทั้งหมด

v1 หยุดหลัง 17 ข้อเนื่องจาก native arguments/HTTP 400; v2–v3 ใช้ 30 ข้อเดิมเพื่อปรับ protocol/prompt; v4 รอบตรวจติด HTTP 400 จาก empty tools; v5 แก้ adapter แล้ว ใช้ cache ของ candidate responses โดยเพิ่ม live verification เท่าที่จำเป็น เก็บ raw runs/metrics เก่าไว้ครบ ไม่ลบข้อผิดพลาด

## งานส่งที่ยังเหลือ ตามขอบเขตที่ตกลง

1. ใช้ corpus ในเครื่องก่อนตามผู้ใช้สั่ง public reproducibility ยังต้องจัดสิทธิ์ข้อมูลหรือทำ public subset พร้อมประเมินใหม่
2. ต้องเติมชื่อผู้จัดทำในรายงานและตรวจเนื้อหาก่อนส่ง
3. มี demo script และ local app แต่ยังไม่มีวิดีโอ 3–6 นาทีหรือ deployed URL ที่ผู้ตรวจเข้าถึงได้
4. ต้องปรับและตรวจความถูกต้องของคำตอบกับผู้มีความรู้ก่อนใช้ตัดสินใจเรื่องสุขภาพ ไม่ถือว่า same-model verifier เป็นหลักประกัน
