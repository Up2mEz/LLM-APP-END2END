> บันทึกการแก้ตารางในรอบ v8–v13 เก็บไว้เพื่อดูที่มา ผลปัจจุบันอ่าน [DEV_COMPARISON_TH.md](DEV_COMPARISON_TH.md) และ workflow ใหม่อ่าน [WORKFLOW_AND_REUSE_TH.md](WORKFLOW_AND_REUSE_TH.md)

# การอ่านตารางและลด false abstention

แก้เฉพาะแอปปลายทาง ใช้ gold และ frozen retrieval เดิม ไม่มี qid หรือ reference answer อยู่ใน serving code การเปรียบเทียบใช้ dev 30 ข้อเดิมที่เปิดใช้พัฒนาแล้ว ไม่ใช่ independent validation

## ปัญหาที่พบจากผลจริง

- v8 งดตอบทั้งที่ gold มีคำตอบ 14 ข้อ ส่วนหนึ่งเกิดจาก reviewer คัดข้อความไม่ตรงต้นฉบับ
- การต่อ chunk ข้างเคียงอย่างเดียวใน v9 ทำให้เห็นหัวตารางเพิ่ม แต่ Gemma ยังสลับโปรตีนจากนมกับจากอาหาร และเรียกค่ารวมเป็นส่วนประกอบ จึงยังแก้ปัญหาไม่สำเร็จ
- v10 อ่านค่าพลังงาน 219 และโปรตีน 5.4 ได้ใน candidate แต่ JSON มีเครื่องหมายคำพูดเกินหน้า `end_line` ทำให้คำตอบถูกปฏิเสธ
- v10/v11 มี HTTP 429 จาก token rate limit ของ class proxy ต้องแยก transport failures จาก semantic errors เก็บผลรอบเหล่านี้ไว้ใน history โดยไม่ลบทิ้ง

## สิ่งที่ปรับ

1. อ่านตำแหน่งเซลล์ใน PDF ด้วย PyMuPDF รวม parent header ที่คร่อมหลายคอลัมน์ และจับชื่อแถวทางซ้ายกรณีขอบตารางไม่ครบ ใช้ตำแหน่งกึ่งกลางคำเพื่อไม่ดึงข้อความของแถวข้างเคียงมาใส่ผิดแถว
2. สแกนเฉพาะหน้าที่มี candidate table ใน frozen parent chunks: 407 หน้า จาก PDF 33 ไฟล์ ได้ transcription ที่ผ่านเงื่อนไข 29 ตาราง ไม่ได้อ้างว่าอ่านตารางทุกชนิดได้แล้ว
3. เก็บชื่อคอลัมน์คู่ค่าจริง พร้อม document/edition, PDF page, bounding box และ PDF SHA-256 ไว้ใต้ data/table_context โดยไม่สร้าง index ใหม่หรือเปลี่ยนอันดับ frozen retrieval
4. ให้ Gemma เลือก source ID, บรรทัด และเซลล์ แทนพิมพ์ตัวเลขกับชื่อคอลัมน์ใหม่ ระบบเป็นผู้แสดงข้อมูลแถวที่ reviewer ใช้ยืนยัน จึงไม่เปลี่ยนค่ารวมให้กลายเป็นค่าจากอาหาร หากอ่านแถวผิดยังต้องตรวจเชิงความหมายต่อ
5. ให้ citation/reviewer เลือกเลขบรรทัด ระบบคัด quote จริงให้เอง กรณีข้อมูลตารางจัดรูปจะแจ้งชัดใน UI ว่าเป็นการเรียงเซลล์จาก PDF ไม่ใช่ข้อความร้อยแก้วต้นฉบับ
6. ซ่อมเฉพาะ duplicate opening quote ของ JSON property ที่พบจริง ไม่มี eval ไม่เติมเนื้อหาหรือเลขที่ขาด และยังผ่าน strict schema, source/range/marker checks เดิม
7. เมื่อมีเอกสารแต่ตอบไม่ได้ ให้โอกาสค้นประเด็นที่ขาดหรือแก้ตาม feedback อีกหนึ่งรอบ ภายใต้ 6 model rounds, 3 searches และ 150 วินาทีใน configuration ที่ทดสอบ ถ้า proxy ตอบ 429 ให้รอ Retry-After ได้ไม่เกิน 60 วินาทีและ retry หนึ่งครั้งเมื่อ deadline เหลือพอ นับ HTTP attempts จริง
8. ข้อความหน้าเว็บแยกระหว่างค้นไม่พบข้อมูลกับค้นพบข้อมูลแต่ยังยืนยันคำตอบไม่ได้ คำถามอาหารโรคไตที่ไม่ระบุระยะต้องไม่สั่งงดอาหารหลายหมวดแบบเหมารวม

## ทำซ้ำในเครื่องที่มีสิทธิ์ข้อมูล

หลัง import snapshot และติดตั้ง dev dependencies แล้ว ใช้คำสั่ง:

```powershell
.venv312\Scripts\python -B scripts/build_table_context.py --source "D:\KMITL\NLP\NLP-Year3\team-project\thai-ncd-guideline-qa"
.venv312\Scripts\python -B scripts/verify_table_sources.py
.venv312\Scripts\python -B -m ncd_gemma.cli evaluate plan
.venv312\Scripts\python -B -m ncd_gemma.cli evaluate agent
```

Serving อ่านไฟล์ derived ที่อยู่ในโปรเจคนี้ ไม่เปิด repo ต้นทางขณะตอบคำถาม แผน evaluation ล็อก table artifact hash และ implementation hashes เพิ่มจาก gold/prompt hashes

## ข้อจำกัดในการตีความผล

Citation primary-evidence hit rate ของรุ่นใหม่ใช้บริบทที่ขยายหน้าได้ จึงเทียบกับ v5/v8 โดยตรงได้เฉพาะในฐานะผล workflow ที่เปลี่ยนไป ไม่ใช่หลักฐานว่าตัว retriever ที่ frozen ดีขึ้น ต้องอ่าน semantic audit ควบคู่ และไม่ใช้ character F1 เป็น clinical accuracy

การใช้ reviewer จาก Gemma ตัวเดียวกันไม่ใช่ independent verification ต้องตรวจแถว กลุ่มประชากร หน่วย เงื่อนไข และคำถามหลายส่วนด้วยคน ผู้ตรวจทางคลินิกและชุดคำถามใหม่ยังจำเป็นก่อนขยายการใช้งาน

ผลทั้ง 30 ข้อและข้อจำกัดปัจจุบันอยู่ใน DEV_COMPARISON_TH.md และ reports/agent_comparison.json ส่วน ANSWER_REVIEW_TH.md เป็นบันทึกรุ่น v8
