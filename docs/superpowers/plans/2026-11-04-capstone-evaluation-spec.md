# ขอบเขตประเมิน Capstone รอบใหม่

สถานะ: ข้อเสนอเพื่อให้ผู้ใช้ตรวจ ยังไม่อนุมัติให้ลงมือ

## ข้อกำหนดเพิ่ม: ทำรายการงานต่อไปให้เสร็จก่อนสรุปรายงาน

ผู้ใช้ไม่ต้องการหัวข้อ “งานต่อไป” ในรายงาน และต้องการให้ทำเนื้อหาที่เคยเสนอไว้ให้สมบูรณ์ การลบข้อความไม่ใช่การปิดงาน ต้องทำรายการด้านล่างเป็นขั้นหลัง baseline รอบแรก ภายใต้แผนที่ผู้ใช้อนุมัติแยก ไม่รวมการแก้ production logic ใน capstone-current-v1:

- ตรวจ structured output และ schema repair จาก failure ของรอบใหม่ แล้ววางแผนแก้สาเหตุจริงโดยคง schema/การตรวจตารางและ gold เดิม ไม่ hard-code qid/คำตอบ
- ทดสอบคำถามใหม่: จัดชุดที่ไม่ใช้พัฒนา แยกจาก exposed dev 30 ข้อ ให้คนตรวจ gold ก่อนล็อกชุด ไม่แอบเรียก dev เดิมว่าใหม่ และไม่ใช้ผลของชุดนี้เลือกปรับ prompt
- Blind review: เตรียม packet ปิดชื่อแขนตามแผน eval แล้วให้ผู้ตรวจที่ระบุชื่อ/บทบาทตรวจจริง เก็บ verdict เหตุผล และการตัดสินกรณีเห็นต่าง ห้ามอ้าง human review ก่อนคนตรวจ
- Ablation: หลังได้ผล controlled dense/hybrid ที่คงส่วนอื่นเท่ากัน จัดคู่ reranker ON/OFF แยกต่างหากด้วยโค้ด/คำถาม/settings ชุดเดียวกันเพื่อวัดผลต่อคุณภาพและเวลาจริง ไม่สรุปจากการปิด toggle ครั้งเดียว
- หลังแก้ runtime ต้องเป็น run version ใหม่พร้อมเปรียบเทียบก่อน/หลัง ห้ามเขียนทับ v1 หรือใช้คะแนน v1 อ้างเป็นคะแนนระบบหลังแก้
- เมื่อครบจึงจัดรายงานหัวข้อท้ายเป็น “ข้อสรุปและข้อจำกัด” อธิบายงานที่ทำแล้วและผลที่ยืนยันได้ คงข้อจำกัดจริง ไม่ใส่รายการสัญญาว่าจะทำภายหลังหรืออ้างว่าปัญหาหายทั้งหมด

ลำดับเสนอเพื่ออนุมัติ: วินิจฉัย typography แยก → current-pipeline baseline → ดู failures → แผนแก้เฉพาะจุด → ล็อกและรันหลังแก้/ablation → blind review/ชุดใหม่ → จัดรายงานและคลิป การเพิ่มจำนวนข้อและ proxy calls นอกงบ v1 ต้องมีแผนงบใหม่ให้ผู้ใช้ตรวจ ไม่ถือว่าได้รับอนุมัติจากการเขียนรายการนี้

## ข้อกำหนดจากคำสั่งอาจารย์

- “Build your own evaluation set — roughly 30 examples — and beat a baseline you name” และ “The numbers must be reproducible from your repo.”
- “Show one measured improvement over a naive default” พร้อมตัวเลข before/after ไม่คาดเดา
- ต้องมีอย่างน้อย 3 capability families รวม #3 retrieval evaluation และ #4 agent loop หรือ #5 advanced agentic capability
- ใช้ `from openai import OpenAI`, class proxy และ `model="gemma-4-E4B-it"`; อ่าน key/base URL จาก environment
- “Set temperature=0 for anything you evaluate or that must be repeatable”
- รายงาน PDF 4–8 หน้า; เดโม 3–6 นาที มีเสียง กรณีสำเร็จและผิดพลาด; สาธิต input ใหม่ต่อหน้าต่างหาก

## ข้อกำหนดผู้ใช้

- ทำเฉพาะงาน `D:/KMITL/LLMapp/ncd-gemma` ไม่เอาคะแนนหรือหลักฐานของอีกงานมาอ้างเป็นผลทดลองนี้
- วางแผนก่อนทำ แล้วรอผู้ใช้บอกเอง ห้ามเริ่ม eval, แก้ implementation, commit/push หรือปรับรายงานในช่วงวางแผน
- Gold ผู้ใช้ให้ coding agent ร่างคำถาม/คำตอบ ผู้ใช้ตรวจ dev ทั้งหมด และแบ่งตรวจ test กับเพื่อนเท่า ๆ กัน
- ใช้ corpus/gold ที่มี provenance เป็นข้อมูลนำเข้าได้ แต่ห้ามโหลด saved predictions, frozen ranked hits หรือ verdict เดิมมาเป็นผลรอบใหม่
- งานแก้วรรณยุกต์ซ้อนสระใน PDF เป็นอีกแผนหนึ่ง ไม่เปลี่ยนคำถาม gold หรือผลวัดเพื่อแก้ปัญหารูปเล่ม

## การทดลองที่เสนอ

ชื่อชุดผลใหม่ `capstone-current-v1` แยกจาก v32 และงาน Thai NCD Guideline QA

ใช้ 30 ข้อจาก dev ของผู้ใช้: 6 ประเภทอย่างละ 5 ข้อ (25 answerable, 5 unanswerable) คัดด้วยวิธี deterministic เดิมเพื่อไม่เลือกข้อจากผลที่จะได้ บันทึก qids และ hashes ก่อนรัน ระบุว่าเป็น exposed development set ไม่ใช่ unseen/held-out ไม่ใช้ test มาปรับระบบ

เปรียบเทียบสองแขน: `dense_default` เรียก retriever variant A กับ `hybrid_current` เรียก variant B ทั้งคู่ใช้ app wrapper, table context, passage focus, reranker ON, prompt และ agent loop เดียวกัน เปลี่ยนเฉพาะวิธีค้นขั้นต้น ไม่เรียก dense_default ว่า no-RAG หรือ pure dense เพราะ downstream ยังเหมือนแอป เป้าหมายคือทดสอบเหตุผลที่เลือก hybrid ในแอปปัจจุบัน

ค่าที่เสนอให้ล็อก: temperature 0, max_steps 6, max_searches 3, request_timeout 45 s, agent_timeout 150 s, max_output_tokens 1400, context_chars 18000, max_sources 20, use_cache=false, use_reranker=true ต้องตรวจว่าเว็บที่จะส่งใช้ค่าเดียวกันก่อนรัน หากไม่ตรงให้หยุดแจ้ง ไม่เปลี่ยน setting เงียบ ๆ ผลไม่ครอบคลุม reranker OFF

1. Retrieval: เรียก `EvidenceRetriever.search(SearchArgs(query=question, top_k=5))` ใหม่ทั้ง 30 ข้อทั้งสองแขน เก็บ passages ที่คืนจริงก่อนเทียบ gold วัด Strict Recall@5, Hit@5, MRR@5 บน 25 ข้อที่ตอบได้ ไม่ใช้ parent text แทน passage ที่โมเดลจะเห็น ไม่อ้างว่าเป็นคะแนน query-refinement ทั้ง loop
2. End-to-end: 30 ข้อ × 2 แขน ผ่าน `/api/ask` ของแอปจริงใน local evaluation process ใช้ OpenAI proxy จริง ไม่มี gold ใน request/context เก็บ response, sources, trace, request options, model/API attempts และเวลาทุกรายการ ให้คำตอบถูกตรวจแยกจากการค้นพบหลักฐาน
3. เกณฑ์หลักอัตโนมัติคือ retrieval ข้างต้น; answer metrics ได้แก่ abstention decision accuracy, primary citation hit และ error rate ซึ่งไม่เท่ากับ semantic correctness จัด blind review packet ให้ตรวจสาระเทียบคำถาม gold และ source ด้วย rubric ประชากร/เงื่อนไข/ตัวเลข/หน่วย/ความครบ/การรองรับจากต้นทาง แยก human review กับ coding-agent review ตามผู้ตรวจจริง ห้ามเรียกว่าตรวจโดยคนหากยังไม่มีคนตรวจ
4. เก็บทุกข้อ รวม timeout, proxy errors และ false abstentions ค่า end-to-end denominator 30 ไม่ตัด error ออกจากคะแนนรวม แสดง service errors แยกเพื่ออธิบายสาเหตุ
5. สลับลำดับแขนแบบ deterministic ต่อ qid เพื่อลด order bias; concurrency=1 ไม่วัด latency แบบงาน benchmark และไม่นับ first-load เป็น inference latency ลับ ๆ
6. ก่อนชุดเต็มมี live preflight 1 ข้อ/แขนจากชุด 30 เดิม รวม 2 requests เก็บเป็น pilot ไม่รวมคะแนน; ชุดเต็มต้องรันใหม่ครบ 60 requests ไม่มีการเอา pilot มาเติม
7. ขอบเขตงบ: 62 app requests รวม pilot, ไม่เกิน 744 proxy attempts ตาม 6 model requests × retry สูงสุด 2 ต่อ request; หยุดเมื่อครบ 3 ชั่วโมงหรือ proxy failure 3 requests ติดต่อกัน เก็บ incomplete run ไม่ประกาศคะแนน complete; ไม่มีจ่ายเงิน/เพิ่มโควตาอัตโนมัติ ไม่เริ่ม retry batch ใหม่เอง
8. ถ้า hybrid ไม่ชนะ baseline ให้รายงานตามจริงและหยุดเสนอผล ไม่แก้ prompt/gold หรือทดลองหลายสูตรเพื่อเลือกคะแนนดีภายใต้ run เดิม เงื่อนไข measured improvement ของโจทย์ยังไม่ถือว่าปิดจนกว่าจะมีผลรองรับ

ผลเก่าเก็บเป็นประวัติได้ แต่ตารางหลักของงานนี้ต้องมี run ID, hash, configuration และ raw evidence ของรอบใหม่เท่านั้น การอัปเดตรายงาน/เว็บ/คลิปเป็นขั้นหลังผู้ใช้ตรวจผล ไม่รวมอนุมัติในแผนรันนี้
