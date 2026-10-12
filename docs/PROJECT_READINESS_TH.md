# ความพร้อมเทียบโจทย์ end-to-end Project

อ้างข้อกำหนดจากหน้า coursework/20 ที่เก็บเมื่อ 11 ตุลาคม 2026 ใน D:\KMITL\LLMapp\coursework-notes\PROJECT.md และโฟลเดอร์ project-review-2026-10-11 ไม่ใช่การตรวจสถานะส่งงานในเว็บใหม่

## สิ่งที่ทำครบในเครื่อง

| ข้อกำหนด | หลักฐาน |
|---|---|
| Class proxy + OpenAI SDK + Gemma | src/ncd_gemma/llm.py; model gemma-4-E4B-it; API key/base URL จาก environment |
| อย่างน้อย 3 families รวม #3 และ agentic | มี #1 schema, #2 RAG, #3 retrieval evaluation, #4 native agent loop, #6 FastAPI/UI |
| Corpus ของโดเมนตัวเอง | NCD ภาษาไทย 66 เอกสารใน snapshot แยกจาก corpus ของ reference app; ระบุ attribution ส่วนที่ reuse |
| Curated evaluation ราว 30 ข้อ | เลือก dev 30 จาก gold เดิม ล็อก qids/hash/implementation ก่อนรัน; ไม่ส่ง gold ให้ model |
| ผลตอบคำถาม v30 | coding-agent review บน exposed dev 30 เดิม: สาระครบ 25/25 answerable และงดตรง label 5/5; extra-dev 30 เริ่ม v26 ถูกหรืองดถูก 19/30, v28 27/30, v29–v30 30/30 หลังใช้ผลปรับระบบแล้ว จึงแยก regression ออกจากผลก่อนปรับอย่างชัดเจน |
| Baseline และ measured improvement | Dense A เทียบ Hybrid B: Recall@5 0.8077 → 0.8846 บน 52 answerable frozen test; MRR 0.6181 → 0.7374 |
| ผลทำซ้ำได้ในเครื่องที่มีข้อมูล | evaluate retrieval ตรวจ hashes และคำนวณ saved hits; evaluate agent resume จาก version ที่ตรง; compare_agent_runs ตรวจชุดคำถามเดียวกัน |
| Tool boundaries | ชื่อ tool/arguments allow-list, safe native parser, timeout, configuration ทดสอบ 6 model rounds/3 searches, source/quote validation |
| ผลลัพธ์และ failure analysis | README, reports/agent_comparison.json, docs/DEV_COMPARISON_TH.md เก็บผลที่แย่ลงด้วย ไม่คัดเฉพาะรอบที่ดี |
| PDF 4–8 หน้า | scripts/build_report.py สร้างรายงาน 6 หน้า พร้อม architecture, baseline, development metrics, failure และข้อจำกัด |

## ยังไม่พร้อมถือว่าส่งครบ

| รายการส่ง | สถานะจริง | ขั้นตอนสุดท้าย |
|---|---|---|
| Q1 Public GitHub 90 คะแนน | origin คือ Up2mEz/LLM-APP-END2END; ยังไม่ push ตามขอบเขตใช้ corpus ในเครื่องก่อน | ตรวจสิทธิ์ข้อมูลหรือทำ public corpus/fetch script, eval data และ clean-clone reproduction; หากเปลี่ยน corpus ต้องประเมินใหม่ |
| Q2 PDF 70 คะแนน | มีรายงานจากผลจริง | เติมข้อมูลผู้จัดทำ ตรวจเนื้อหา แล้วอัปโหลด |
| Q3 URL 40 คะแนน | แอปทำงานที่ localhost และมี demo script | อัดวิดีโอพร้อมบรรยาย 3–6 นาทีและ URL ที่ดูได้ หรือ deploy ภายใต้สิทธิ์ข้อมูลที่เหมาะสม |
| Proposal / live defence | มี proposal และคำอธิบาย design/metrics | ผู้จัดทำยืนยัน scope กับผู้สอน เตรียมรับคำถามใหม่ และอธิบายผลด้วยตนเอง |

Public repo ที่มีเพียงโค้ดและ import script จาก private path ยังไม่ผ่านเงื่อนไขให้ผู้ตรวจ reproduce จาก public repo ได้ ไม่อ้างว่า localhost เป็น live deployed URL และยังไม่ได้ Submit Project

## สิ่งที่ควรพัฒนาก่อนขยายการใช้งาน

ผลล่าสุดและ failure analysis อยู่ใน docs/DEV_COMPARISON_TH.md และ docs/EXTRA_DEV_V26_REVIEW_TH.md แยกจำนวนตอบได้ออกจากความถูกต้องจริง ชุด dev เดิมถูกใช้ปรับระบบหลายรอบแล้ว ส่วน extra-dev ก็เปิดผลเพื่อแก้ v27–v30 จึงต้องมีคำถามใหม่และผู้ตรวจอิสระก่อนอ้างผลทั่วไป

ต้องมี independent review และชุดคำถามใหม่ก่อนอ้าง generalization การเพิ่ม SQL/MCP ยังไม่จำเป็นต่อ rubric เพราะมี agentic family #4 แล้ว งานที่มีผลต่อคะแนนส่งจริงมากกว่าคือสิทธิ์เผยแพร่ corpus/reproducibility, PDF ฉบับตรวจชื่อผู้จัดทำ และ demo URL วิดีโอหรือ deployment
