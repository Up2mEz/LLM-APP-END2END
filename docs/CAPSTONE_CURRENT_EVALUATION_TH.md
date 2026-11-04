# ประเมินแอป Capstone ปัจจุบัน

ชุดรัน `capstone-current-v2` ใช้โค้ดแอปในเครื่องที่ล็อก hash ไว้ เทียบ `dense_default` (variant A) กับ `hybrid_current` (variant B) โดยคง passage focus, table context, reranker, prompt, model และ agent budget เหมือนกัน ไม่โหลดคำตอบหรือ ranked hits ของงานเดิมมาเป็นผลรอบนี้

## ชุดคำถามและค่ารัน

คัด 30 ข้อจาก gold dev ที่ผู้จัดทำตรวจเอง: condition, fact, multi_page, number_unit, table และ unanswerable อย่างละ 5 ข้อ เป็น exposed development set ไม่ใช่ held-out ข้อมูล gold อ่านเฉพาะขั้นเลือกชุดและให้คะแนน Request ที่เข้าแอปมีเพียงคำถามกับตัวเลือกการค้นหา

ใช้ gemma-4-E4B-it ผ่าน class proxy, temperature=0, max_steps=6, max_searches=3, timeout ต่อ request 45 วินาที/ต่อ agent 150 วินาที, use_cache=false และ use_reranker=true ผลไม่ครอบคลุมโหมดปิด reranker

## สิ่งที่วัด

- Retrieval: เรียก retriever ปัจจุบันด้วยคำถามเต็ม top_k=5 ใหม่ทุกข้อ วัด Strict Recall@5, Hit@5 และ MRR@5 บน 25 ข้อที่ตอบได้ ใช้ edition, หน้า และข้อความของ passage ที่คืนจริงตามเกณฑ์ quote coverage ใน scorer
- End-to-end: ส่ง 30 ข้อ × 2 แขนผ่าน FastAPI `/api/ask` ใน process สำหรับ eval ซึ่งใช้ Agent, ProxyClient และ EvidenceRetriever ตัวเดียวกับแอป มีเพียง adapter เลือก A/B และเก็บ trace; ไม่ได้ยิงเข้า server ที่ผู้ใช้เปิดอยู่
- Answer metrics: decision accuracy ของการตอบ/งดตอบ, primary citation hit และ error rate แยกจากการตัดสินความครบของสาระ
- LLM-as-judge: GPT-6-Luna, reasoningEffort=xhigh ผ่าน T3 delegated task แยกจากโมเดล Gemma ที่ตอบคำถาม ซ่อนชื่อแขนก่อนตรวจ อ้าง rubric และ packet hash ของแต่ละงาน ไม่มี human review รอบใหม่ และ transport นี้ไม่เปิดให้กำหนด temperature จึงไม่อ้างว่า judge ใช้ temperature=0

## Rubric ของ judge

Judge เห็นคำถาม คำตอบอ้างอิง หลักฐาน gold และคำตอบพร้อม sources/citations ของระบบ โดยไม่เห็นชื่อแขน คะแนน semantic success=1 เฉพาะ `correct` หรือ `correct_abstention`; ประเภทอื่นเป็น 0

| Verdict | ความหมาย |
|---|---|
| correct | ตอบสาระที่ถามครบ ตัวเลข/หน่วย/ประชากร/เงื่อนไขตรง และหลักฐานรองรับ |
| partial | มีส่วนถูก แต่ขาดประเด็นที่คำถามต้องการ |
| wrong | เนื้อหาหลักผิดหรือใช้เงื่อนไข/ประชากรผิด |
| unsupported | คำตอบดูถูกแต่หลักฐานที่อ้างไม่รองรับ |
| correct_abstention | gold ระบุว่าตอบไม่ได้ และระบบงดตอบโดยไม่เกิด service failure |
| false_abstention | gold มีคำตอบรองรับ แต่ระบบงดตอบ |
| service_error | บริการโมเดล/HTTP ขัดข้อง รวม verification_unavailable ไม่ให้เครดิตเป็นการงดตอบถูก |
| uncertain | หลักฐานใน packet ขัดกันหรือไม่พอให้ judge ตัดสิน ไม่แทนด้วย correct |

ให้ judge ระบุเหตุผลสั้น ๆ และ source ID/quote ที่รองรับการตัดสิน ไม่ให้คะแนนตามสำนวน ความยาว หรือการตรงถ้อยคำกับเฉลยเพียงอย่างเดียว ไม่แก้ gold จากความเห็น judge และไม่ส่ง verdict กลับไปซ่อมคำตอบใน run เดิม เก็บทุก verdict รวม uncertain และ service errors ใน denominator 30 ต่อแขน

## ทำซ้ำ

```powershell
$env:PYTHONPATH = "$PWD/src"
.venv312/Scripts/python.exe -m pytest tests/test_capstone_protocol.py tests/test_capstone_runner.py tests/test_capstone_metrics.py -q
.venv312/Scripts/python.exe -m ncd_gemma.capstone_eval verify --run capstone-current-v2
.venv312/Scripts/python.exe -m ncd_gemma.capstone_eval run --run capstone-current-v2
.venv312/Scripts/python.exe -m ncd_gemma.capstone_eval summarize --run capstone-current-v2
```

`plan` ใช้ตอนสร้าง manifest ครั้งแรกและปฏิเสธเขียนทับ; `run` resume เฉพาะรายการที่บันทึกครบและ identity ตรง หากมี in-flight request ที่ไม่ทราบผลจะหยุดแทนการเรียกซ้ำอัตโนมัติ ก่อนเริ่มและหลังจบตรวจ hash ข้อมูลทั้งหมด ระหว่างข้อเช็ก code/config/question drift ค่า judged score อาจเปลี่ยนเมื่อรันโมเดลใหม่ แม้ protocol เดิม

แยก raw ใน `private/capstone-current-v2/` และ manifest/aggregate ใน `reports/capstone-current-v2/` Pilot 2 requests ไม่รวมคะแนน จำกัดรอบเต็ม 60 requests; error เก็บเป็นผลไม่ลบทิ้ง เวลาที่บันทึกเป็นเวลาในเครื่อง ไม่ใช่ benchmark ข้าม hardware การวัดครั้งแรกไม่รับประกันว่าจะชนะ baseline

`capstone-current-v1` เก็บเป็น incomplete หลังตรวจพบช่องว่างของ harness ในการนับ verification outage และ resume reservation ไม่ใช้ผล v1 เติม v2

## ผลใหม่ที่รันครบแล้ว

รอบ v2 ตรวจ hash ผ่านและครบ retrieval 60 รายการ + answers 60 รายการ แยก pilot 2 requests รวมใช้ 62 app requests และ 201 proxy attempts ผล LLM-as-judge ตรวจครบ 60 รายการพร้อมเหตุผลและหลักฐาน ไม่ให้คะแนน semantic success จาก status เพียงอย่างเดียว

| Metric | Dense baseline | Hybrid current |
| --- | --- | --- |
| Strict Recall@5 (25 answerable) | 0.8200 | 0.9000 |
| Hit@5 | 0.8400 | 0.9200 |
| MRR@5 | 0.7047 | 0.7833 |
| Decision accuracy (30 ข้อ) | 0.8333 | 0.9333 |
| Primary citation hit (25 ข้อ) | 0.6400 | 0.6400 |
| Service errors | 1/30 | 2/30 |
| Semantic success โดย Luna xhigh | 23/30 (0.7667) | 28/30 (0.9333) |

Hybrid แบ่งเป็น correct 23, correct_abstention 5 และ service_error 2 ส่วน dense เป็น correct 19, correct_abstention 4, false_abstention 4, partial 1, wrong 1 และ service_error 1 ทุกประเภทอยู่ในตัวหาร ผลจาก Luna เป็น LLM-as-judge ไม่ใช่ human review

พบ encoding ของเหตุผลใน batch 04–10 ถูกแทนด้วยเครื่องหมายคำถามระหว่างบันทึก จึงเก็บต้นฉบับและให้ Luna xhigh อ่าน packet เดิมเพื่อเขียนเหตุผลใหม่เป็นภาษาอังกฤษ ไม่มี verdict เปลี่ยนหรือข้อโต้แย้ง Collector เพิ่มการปฏิเสธข้อความเสียและตรวจ hash ใหม่หลังแก้ เก็บ task receipts ของทั้งการตรวจและการซ่อมไว้ในโฟลเดอร์ผล

Recall@5 เพิ่ม 8 จุดเปอร์เซ็นต์ เป็น measured improvement ของวิธีค้นขั้นต้นบน pipeline ปัจจุบัน Service errors ทั้งสามเกิดจาก HTTP 429 ของ proxy (hybrid q093/q101 และ dense q119) ไม่แทนผลด้วยการ retry รอบใหม่และไม่ให้เครดิตเป็น abstention ที่ถูกต้อง

## Reranker ablation แยกต่างหาก

`capstone-reranker-ablation-v1` ใช้ ON arm ของ hybrid จากรอบ v2 เทียบกับ OFF ที่รันใหม่ 30 searches ภายใต้ code/data/query hashes เดิม ปิด cache ทั้งคู่ ไม่เรียก Gemma เพิ่ม ผลนี้เป็น retrieval-only ไม่ใช่คะแนนคำตอบโหมด OFF

| Metric | Reranker ON | Reranker OFF |
| --- | --- | --- |
| Strict Recall@5 | 0.9000 | 0.7400 |
| Hit@5 | 0.9200 | 0.7600 |
| MRR@5 | 0.7833 | 0.5320 |
| Median retrieval seconds | 14.4925 | 0.2350 |

การปิดลดเวลาค้นแต่พบหลักฐานน้อยลงในชุดนี้ เวลาวัดคนละช่วงในเครื่องเดียวกันและไม่รวมโหลดโมเดล/สร้างคำตอบ/verification จึงไม่กล่าวว่าแอปทั้งระบบเร็วขึ้นตามอัตราส่วนนี้ ทำซ้ำด้วย `python scripts/capstone_reranker_ablation.py` หลังรอบ v2 ครบ สคริปต์ปฏิเสธเขียนทับผลเดิม
