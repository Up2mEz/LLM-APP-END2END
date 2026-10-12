# ตรวจความพร้อมส่ง Project — 12 ตุลาคม 2026

> รายงานส่วนล่างเป็น snapshot ก่อนเตรียม public release ในวันเดียวกัน หลังจากนั้นผู้จัดทำแจ้งว่ามีหลักฐานอนุญาตให้เผยแพร่และโฮสต์ corpus เดิมแล้ว แต่ยังไม่ได้ส่งรายละเอียดหลักฐาน/ขอบเขตมาให้ตรวจใน repository จึงบันทึกเป็นคำยืนยันของผู้จัดทำ ไม่แก้สิทธิ์ manifest ต้นทาง สถานะ GitHub และ deployment ต้องตรวจซ้ำหลังเผยแพร่

ขอบเขตการตรวจครั้งนี้: โค้ด, dependency, tests, API/UI ในเครื่อง, ผลประเมิน, GitHub, สิทธิ์ข้อมูล และความเป็นไปได้ของ live URL **ไม่ตรวจหรือแก้ PDF ตามคำขอผู้จัดทำ** ไม่ได้สร้างคลิปหรือกด Submit ในเว็บรายวิชา

## ข้อสรุป

**ยังไม่พร้อมส่งครบสามช่อง** ตัวแอปในเครื่องใช้งานได้ แต่ public GitHub repo ยังว่างและข้อมูลที่จำเป็นต่อการรันซ้ำยังอยู่ในเครื่องเท่านั้น Live URL ทำได้ทางเทคนิคหลังเลือก corpus ที่มีสิทธิ์เผยแพร่/โฮสต์และเตรียม deployment ที่ป้องกัน proxy key กับการเรียก API โดยไม่จำกัด

| ช่องส่งตามโจทย์ | สถานะ 12 ต.ค. | เหตุที่ยังไม่ผ่าน |
|---|---|---|
| Q1 public GitHub repo | ไม่พร้อม | `Up2mEz/LLM-APP-END2END` เป็น public แต่ GitHub API รายงาน `size: 0`; ไม่มี commit จากเครื่องนี้บน remote. Local branch `master` มี 7 commits และไฟล์ที่ยังไม่ commit จำนวนมาก. `data/` กับ model cache ถูก ignore; README ให้ import จาก private path จึง clean-clone reproduce ไม่ได้ |
| Q2 รายงาน PDF | ไม่ประเมิน | ผู้จัดทำแจ้งว่า format ยังดูเป็น template/AI และขอข้าม PDF ในการตรวจรอบนี้ |
| Q3 demo URL หรือคลิป | ไม่พร้อม | `127.0.0.1:8765` ใช้ได้เฉพาะเครื่องนี้ ยังไม่มี live URL/คลิป. โจทย์รับ live app URL แทนคลิปได้ แต่ต้องให้ผู้ตรวจลองถามจริงและเห็นกรณีสำเร็จ/ไม่สำเร็จ |

## ผลตรวจที่ผ่าน

- `pytest -q`: **164 passed, 1 Starlette deprecation warning**, ไม่มี failed/error/skipped เมื่อรันในสภาพแวดล้อมที่เปิด local loopback ได้
- `uv pip check --python .venv312\Scripts\python.exe`: **72 packages compatible**. Environment นี้ไม่มีโมดูล `pip`; จึงใช้ `uv pip check` แทน
- `ncd_gemma.cli doctor`: proxy configured, model `gemma-4-E4B-it`, data present
- `doctor --live` ผ่านแต่เป็น cached probe; จึงยิง generic probe ใหม่ผ่าน OpenAI SDK ไป class proxy โดยไม่มี corpus/gold และได้ `finish_reason=stop` กลับจริง
- `/api/health`: `status=ready`, `retrieval_loaded=true`, `data_present=true`
- หน้าเว็บ local แสดงคำตอบจริงและ source citation จากคำถามที่ผู้ใช้ถามค้างอยู่; browser console ไม่มี error/warning ที่เห็นในรอบตรวจนี้
- `evaluate retrieval`: ตรวจ saved frozen runs 6 รายการ; B เทียบ A บน frozen test เพิ่ม Recall@5 `0.0769` และ MRR@10 `0.1193`. ค่านี้เป็นการคำนวณจาก saved hits ไม่ใช่การรัน retrieval ใหม่
- `git diff --check`: ผ่าน; ไม่มี `.env`, `data/`, `private/`, `.cache/` หรือ PDF ใน tracked files ณ เวลาตรวจ
- สแกน pattern ของ API key/private key ในไฟล์โค้ด เอกสาร และรายงานที่เตรียมขึ้น Git: ไม่พบ match (เป็นการสแกนรูปแบบ ไม่ใช่การรับรองว่าไม่มีข้อมูล internal ทุกชนิด)
- รายงาน v30 มีผล dev ชุดแรก 25/25 answerable และ extra-dev 30/30 หลังใช้ผลชุดนั้นปรับระบบแล้ว จึงเป็น **exposed development/regression**, ไม่ใช่ผลทดสอบอิสระหรือความถูกต้องทางคลินิก

## ตัวปิดกั้น live URL

1. **สิทธิ์ corpus**: handoff ต้นทาง `data/handoff/track_c_20261012/README.md` บรรทัด 33 ระบุว่าข้อความเอกสารบางส่วน (รวมแผ่นพับ Siriraj) ใช้ภายในทีมและห้ามขึ้น Git/เผยแพร่. การอนุญาตเดิมให้ส่ง *คำถามและหลักฐาน* ไป class proxy สำหรับการทดสอบ ไม่ครอบคลุมการโฮสต์ corpus, เปิด API สาธารณะ หรือส่งไฟล์ไป cloud provider. แม้ Git ignore ข้อมูลไว้, live app จะส่งข้อความหลักฐานกลับให้คนทั่วไปผ่าน `/api/ask` ได้
   ตรวจ `data/manifests/rights_review_20261005.json` ใน repo ต้นทางแล้ว: **75/75 records มี `redistribution_approved=false`**, 68 records ระบุอนุมัติใช้ภายในเพื่อศึกษา และ 7 records ยัง pending. แม้ผู้จัดทำเลือกใช้ corpus เดิม ก็ต้องมีหลักฐานสิทธิ์เผยแพร่/โฮสต์จากเจ้าของเอกสารก่อนขึ้น public
   โค้ด `src/ncdqa/retrieval` ก็คัดลอกจาก repo ทีมและไม่พบไฟล์ license ที่ root ของ repo ต้นทาง; ควรยืนยันสิทธิ์การนำโค้ดส่วนนี้ขึ้น public repo ด้วย
2. **แอปรองรับ localhost เท่านั้น**: CLI bind `127.0.0.1`; `TrustedHostMiddleware` ยอมรับแค่ `127.0.0.1`, `localhost`, `testserver`. ทดสอบ Host `demo.example` แล้วได้ HTTP 400 `Invalid host header`
3. **public API ยังไม่จำกัดผู้ใช้/คำขอ**: `/api/ask` ไม่มี auth หรือ per-user/IP rate limit; semaphore 1 ช่องเพียงจำกัดคำถามพร้อมกัน. หากเผยแพร่ URL อาจมีคนใช้ class proxy key ของผู้จัดทำโดยอ้อม, ดึงข้อความ corpus, หรือทำให้บริการไม่พร้อมใช้. ต้องกำหนด access policy, quota และ logging ที่ไม่เก็บข้อมูลละเอียดอ่อนเกินจำเป็น
4. **การติดตั้งและ cold start**: retriever ต้องมี index/chunks/table context และ Hugging Face cache ของ bge-m3 กับ bge-reranker-v2-m3 (สอง cache บนเครื่องนี้รวมประมาณ 6.41 GiB ก่อนนับ index, dependencies และ memory ตอนรัน). README ระบุ first load ในเครื่องนี้ประมาณ 298 วินาที. ยังไม่มี container manifest, Linux smoke test, การเตรียม model/data ที่ clean-clone ทำซ้ำได้ หรือ cloud egress test ไป class proxy
5. **หลักฐานประเมิน public**: Gold/reference answers ถูก ignore; หากผู้ตรวจได้เพียง public repo จะรัน evaluation ตาม README ไม่ได้. ต้องใช้ข้อมูล/สิทธิ์ที่เผยแพร่ได้และสร้างผล baseline + agent evaluation ใหม่บน snapshot เดียวกัน; ห้ามย้ายตัวเลขเก่ามาอ้างกับ corpus ใหม่

## เส้นทางที่แนะนำ

1. เลือกเอกสาร NCD ที่ตรวจสิทธิ์การเผยแพร่และการโฮสต์ได้ พร้อมบันทึก edition/URL/license. แยกเอกสาร internal ออก และประเมิน corpus ใหม่ด้วย gold ที่เผยแพร่ได้หรือ fetch ได้โดยผู้ตรวจ
2. ทำ setup บนเครื่องสะอาดหรือ container ให้ดึง/สร้าง index และ model cache ได้โดยไม่พึ่ง private path; pin versions และตรวจ hash
3. เตรียม hosting แบบ process อยู่ต่อเนื่องและมี RAM พอสำหรับ encoder/reranker/index; เก็บ class proxy key เป็น secret ของ host. ตั้ง public hostname ใน trusted hosts, เพิ่ม auth/quota/rate limit แล้วทดสอบ HTTPS, cold start, real question, error case และ proxy access จาก host จริง
4. ตรวจ tracked files รวมประวัติ commit ว่าไม่มี secret หรือข้อความ internal ก่อน push. Push โค้ด/README/evaluation ที่ reproduce ได้ไป public GitHub และตรวจจาก clean clone
5. ส่ง Q1 และ Q3 เมื่อ URL เปิดได้จากเครื่องอื่นและ rubric ยอมรับวิธีสาธิต. Q2 รอผู้จัดทำแก้และตรวจ PDF แยก; คลิปยังไม่ต้องตัดสินตอนนี้

ทางเลือก hosting ที่เป็นไปได้คือ Docker Space หรือ CPU web service ที่มี RAM/พื้นที่/เวลาบูตเพียงพอ; ยังไม่ได้เลือก provider, สร้าง account หรือ deploy. Hugging Face Spaces มี Docker, runtime secrets และ CPU hardware แต่ compute Space สำหรับบัญชีส่วนตัวต้องมีแพ็กเกจหรือ billing ตามเงื่อนไขปัจจุบัน; free CPU จะ sleep เมื่อไม่มีการใช้งาน จึงต้องทดสอบ cold start ก่อนใช้เป็นลิงก์ส่งงาน

## หลักฐานที่ใช้

- โจทย์ Project: https://courses.nat-d.uk/courses/building-llm-powered-applications/courseworks/20 (ตรวจหน้าเว็บขณะเข้าสู่ระบบ)
- Public repo metadata: GitHub API `repos/Up2mEz/LLM-APP-END2END` (อ่านอย่างเดียว 12 ต.ค. 2026)
- สิทธิ์ข้อมูล: handoff ต้นทาง `data/handoff/track_c_20261012/README.md` บรรทัด 33
- Host constraints: `src/ncd_gemma/cli.py`, `src/ncd_gemma/server.py`
- ผลรุ่นพัฒนา: `README.md`, `docs/IMPLEMENTATION_STATUS_TH.md`, `reports/extra_dev_v30_semantic_audit.json`
- Hosting reference: https://huggingface.co/docs/hub/spaces-overview และ https://huggingface.co/docs/hub/spaces-sdks-docker
