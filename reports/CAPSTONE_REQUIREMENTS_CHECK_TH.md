# ตรวจตามคำสั่ง Capstone

ใช้คำสั่งอาจารย์ที่ผู้จัดทำส่งเป็นเกณฑ์ ผลปัจจุบันอยู่ใน capstone-current-v2 ไม่ใช้ frozen retrieval หรือ v32 เป็นผลของแอปรอบนี้

| ข้อกำหนด | หลักฐานปัจจุบัน | สถานะ |
| --- | --- | --- |
| Class proxy, OpenAI SDK, gemma-4-E4B-it, environment config | src/ncd_gemma/llm.py, config.py และ trace ของรอบจริง | ยืนยันด้วยรอบประเมินใหม่ |
| อย่างน้อย 3 families รวม evaluation และ agentic | Pydantic, RAG/citations, retrieval evaluation, native search_docs + stop conditions, FastAPI/React | ครอบคลุม 1, 2, 3, 4, 6 |
| Corpus เฉพาะโดเมนและ raw/fetch script | NCD normalized-v12, scripts/public_data.py, provenance manifests | มี fetch script และ hashes |
| Own evaluation set ประมาณ 30 ข้อ | ผู้จัดทำให้ agent ร่างและตรวจ dev เองทั้งหมด; test แบ่งตรวจกับเพื่อน; รอบนี้คัด dev 30 ข้อ | ระบุ ownership และ exposed-dev scope |
| Quantitative metric + baseline + measured improvement | Fresh Recall@5 dense 0.82 → hybrid 0.90 บน 25 answerable | เพิ่ม 8 จุดเปอร์เซ็นต์เมื่อคงส่วนอื่นเหมือนกัน |
| Real answer evaluation | Luna 6 xhigh แบบซ่อนชื่อแขน: dense 23/30, hybrid 28/30 | ครบ 60 verdicts พร้อมเหตุผล; LLM review ไม่ใช่ human review |
| Honest failures | Dense มี wrong/partial/false abstention; proxy HTTP 429 dense 1 และ hybrid 2 | เก็บ service errors ในตัวหาร ไม่มี replacement calls |
| Reranker tradeoff | ON/OFF retrieval Recall@5 0.90/0.74, median 14.49/0.24 วินาที | Retrieval-only, ไม่อนุมานคะแนนคำตอบ OFF |
| ตรวจรุ่นเก่าเทียบรุ่นปัจจุบันด้วยเงื่อนไขเดียวกัน | 60 คู่คำถาม ปิดแคชทั้งคู่; Luna xhigh ตรวจซ่อนชื่อรุ่นครบ 120 คำตอบ | ผ่านเท่ากัน 56/60; ไม่อ้างว่ารุ่นใหม่แม่นยำกว่า; แยกจากผลเลือกวิธีค้น |
| Q1 repo/README/eval/history | README และ harness พร้อมคำถาม ผลประเมิน และประวัติ commits | ตรวจ clone แยกและ environment ใหม่ผ่าน 209 tests, build และค้นเอกสารจริง; ดู Q1_RELEASE_CHECK_2026-11-05.md |
| Q2 PDF 4–8 หน้า | output/pdf/NCD_EVIDENCE_SUBMISSION_67070060.pdf | 8 หน้า, architecture, protocol, baseline/results, failures, limitations; สีดำ Angsana New ไม่มีวันที่ปรับปรุง |
| Q3 narrated demo 3–6 นาที | ประกอบเสียง Arlo ใหม่และภาพ AboutSystem ผลปัจจุบันใน ncd-capstone-current-v2-demo | 4 นาที 49 วินาที; decode ผ่าน ไม่พบจอดำ/เงียบเกิน 1.5 วินาที; ยังไม่ได้ฟังตรวจตลอดคลิปหรือเผยแพร่ URL |
| Live defence | ต้องรับ input ใหม่และอธิบาย design choice/metric ต่อผู้สอน | วิดีโอและ dev score ไม่แทนการสาธิตต่อหน้า |

ตัวเลขทำซ้ำจาก raw ใน run เดียวกันได้ด้วย scorer และมี hashes ระบุ snapshot การเรียกโมเดลใหม่อาจได้ผลต่างจากรอบนี้ โดยเฉพาะ LLM-as-judge ซึ่ง T3 ไม่เปิดตัวเลือก temperature ส่วน Gemma ใช้ temperature=0

รายงานไม่มีหัวข้อสัญญางานต่อไป แต่ยังระบุข้อจำกัดจริง ไม่อ้างคะแนนเต็มหรือรับรองผลผ่านรายวิชา การเผยแพร่ repo/วิดีโอและการส่งช่อง Q1–Q3 ยังเป็นคนละขั้นกับการเตรียมไฟล์ในเครื่อง
