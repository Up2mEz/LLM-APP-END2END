# NCD Evidence: Gemma ผ่าน class proxy

แอปถามตอบจากเอกสาร NCD ภาษาไทย ใช้ gold และ retrieval snapshot จาก Thai NCD Guideline QA แล้วต่อ `gemma-4-E4B-it` ผ่าน OpenAI SDK พร้อม native `search_docs` tool และ agent loop หน้าสาธิตแสดงคำตอบ ข้อความอ้างอิง เลขหน้า และ trace

โปรเจคนี้อยู่แยกจากต้นทางใน `D:\KMITL\LLMapp\ncd-gemma` ข้อมูลที่นำเข้าเป็นสำเนา ไม่มี runtime import หรือ write ไปที่ repository ต้นทาง

## เริ่มใช้งานบนเครื่องนี้

```powershell
cd D:\KMITL\LLMapp\ncd-gemma
.\run.ps1
```

เปิด `http://127.0.0.1:8765` การถามครั้งแรกจะโหลด bge-m3 และ index เข้า memory ครั้งต่อไปใช้ instance เดิม API รับคำถามครั้งละหนึ่งคำถามเพื่อจำกัดทรัพยากร การตรวจครั้งแรกบนเครื่องนี้ใช้เวลาโหลดประมาณ 298 วินาที และค้นหลักฐานจริงได้ 3 รายการ หากต้องการดูขั้นตอนโหลด ให้ตั้ง `$env:NCD_DEBUG_STARTUP='1'` ก่อนรัน

## ติดตั้งใน environment ใหม่

Environment ที่ทดสอบใช้ Python 3.12.13 และ CPU RAM เพียงพอสำหรับ bge-m3/index ไม่ต้องมี GPU

```powershell
py -3.12 -m venv .venv312
.venv312\Scripts\python -m pip install -r requirements-runtime.txt
Copy-Item .env.example .env
```

ตั้ง `OPENAI_API_KEY` และ `OPENAI_BASE_URL` เป็นค่าจาก class proxy ใน `.env` ไม่ส่ง key เข้า frontend และไม่ commit `.env` โมเดลถูกกำหนดเป็น `gemma-4-E4B-it` แอปตรวจ endpoint ว่าเป็น `https://llm.nat-d.uk` จึงไม่เผลอใช้ key กับบริการอื่น การอ่าน `.env` ของโปรเจคนี้จะ override ตัวแปรชื่อเดียวกันที่สืบทอดมาจาก shell

นำข้อมูลที่มีสิทธิ์ใช้จาก local repository เข้ามา:

```powershell
python scripts/import_source.py --source "D:\KMITL\NLP\NLP-Year3\team-project\thai-ncd-guideline-qa"
```

สคริปต์อ่าน allow-list 48 ไฟล์ ตรวจ SHA-256 ก่อนและหลัง copy และปฏิเสธการเขียนทับไฟล์ปลายทางที่เปลี่ยนไป ข้อมูลอยู่ใต้ `data/` ซึ่ง Git ignore ไว้ทั้งหมด ไม่มี secret ถูกคัดลอกด้วยสคริปต์นี้ ดูรายการต้นทางและ hashes ใน `provenance/source_snapshot.json`

ต้องมี Hugging Face cache ของ `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181` และ `refs/main` ของ cache ต้องตรง revision นี้ แอปตั้ง offline mode โดย default เพื่อไม่เปลี่ยน weights ระหว่างรัน หากติดตั้งเครื่องใหม่ ให้เตรียม cache revision นี้จากผู้ให้บริการโมเดลด้วยกระบวนการที่บันทึก version ชัดเจนก่อน การเปลี่ยน answer LLM ไม่ต้องสร้าง document vectors ใหม่

## คำสั่งตรวจและประเมินผล

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv312\Scripts\python -B -m ncd_gemma.cli doctor
.venv312\Scripts\python -B -m ncd_gemma.cli doctor --retrieval
.venv312\Scripts\python -B -m ncd_gemma.cli doctor --live
.venv312\Scripts\python -B -m pytest -q
.venv312\Scripts\python -B -m ncd_gemma.cli evaluate retrieval
.venv312\Scripts\python -B -m ncd_gemma.cli evaluate plan
.venv312\Scripts\python -B -m ncd_gemma.cli evaluate agent
```

`doctor --live` และ `evaluate agent` เรียก class proxy จริง `evaluate retrieval` คำนวณ metrics จาก saved ranked hits และตรวจ hash ไม่เรียกโมเดลหรือรัน test retrieval ใหม่ `evaluate plan` ล็อก dev sample 30 ข้อก่อนเรียกโมเดล การเปลี่ยนคำถามหรือ prompt หลังมีแผนต้องสร้าง version ใหม่ ไม่ปรับแผนตามผล

ผล aggregate อยู่ใน `reports/` ผลคำตอบพร้อมหลักฐานอยู่ใน `private/runs/` และ raw model cache อยู่ใน `.cache/llm/` ทั้งสองโฟลเดอร์ถูก ignore การรัน agent evaluation ซ้ำ resume จาก qid ที่มีอยู่แล้ว ไม่เรียก API ซ้ำโดยไม่จำเป็น Cache เก็บ response เต็มรวม tool calls และผูกกับ endpoint identity, model, messages, tools และ parameters

## โครงสร้าง

```text
src/ncd_gemma/     app, SDK adapter, validation, agent loop, evaluation
src/ncdqa/        สำเนา retrieval modules จากโปรเจคเดิม
configs/          frozen retrieval configuration
static/           หน้าเว็บภาษาไทย ไม่มี external scripts/fonts
schemas/          question/retrieval schemas จากต้นทาง
scripts/          import และเครื่องมือทำเอกสาร
tests/            protocol, citation, failure และ API tests
data/             corpus/index/gold/frozen runs (private, ignored)
reports/          aggregate metrics และเอกสารผลทดสอบ
private/          คำตอบจริงและ evidence (ignored)
provenance/       hashes และ attribution
```

## Architecture และขอบเขต tool

```mermaid
flowchart LR
    U[Thai question / Web UI] --> API[FastAPI POST /api/ask]
    API --> A[Bounded agent loop]
    A <--> G[OpenAI SDK / class proxy / Gemma]
    A --> V[Validate search_docs arguments]
    V --> R[Frozen B hybrid retrieval]
    R --> I[bge-m3 child index + BM25 parent chunks]
    R --> E[Evidence IDs / text / document / page]
    E --> A
    A --> C[Answer schema + citation quote validation]
    C --> U
    GOLD[Gold dev/test] --> EV[Evaluation only]
    EV --> M[Metrics / baseline comparison]
```

Gold ไม่ถูกโหลดโดย serving layer และไม่มี reference answers ถูกส่งให้ Gemma ฝั่ง retrieval ใช้ child 128 tokens, parent 512 tokens, bge-m3, BM25 char3, k1=2.18, b=0.86 และ min-max convex fusion alpha=0.6, pool=100 ตาม frozen config เดิม

Agent บังคับเริ่มด้วย `search_docs` จากนั้นเลือกค้นเพิ่มหรือตอบได้เอง เก็บ assistant tool calls และส่ง tool result กลับพร้อม `tool_call_id` ที่ตรงกัน จำกัด 4 model rounds, 3 searches, top_k ไม่เกิน 8 และ context รวม 18,000 ตัวอักษร ปฏิเสธ query/filter ซ้ำ ชื่อ tool อื่น และ filter ที่ไม่มีใน metadata รอบสุดท้ายปิดการเรียก tools มี request timeout และ agent deadline

Final answer ผ่าน Pydantic schema มีสถานะ answered หรือ insufficient_evidence ทุก citation ต้องอ้าง source ID ที่ tool ส่งมาจริง quote ต้องอยู่ในข้อความที่ model เห็น และ citation markers ในคำตอบต้องตรงกับรายการอ้างอิง ถ้าผิดให้แก้ได้หนึ่งรอบ แล้วหยุดอย่างชัดเจน การตรวจนี้ยืนยันที่มาของ quote ไม่ได้พิสูจน์ความหมายของคำตอบทุกประโยค

## ผล retrieval และ baseline

ผลจาก saved frozen test มี 56 gold questions เป็น answerable 52 และ unanswerable 4 ข้อ ค่าเฉลี่ยต่อไปนี้ใช้ 52 ข้อที่ตอบได้

| ระบบ | Strict Recall@5 | Strict MRR@10 |
|---|---:|---:|
| A dense parent-child (baseline) | 0.8077 | 0.6181 |
| B hybrid parent-child (แอปเลือกใช้) | 0.8846 | 0.7374 |
| C hybrid + reranker (ผลทดลองเดิม) | 0.9135 | 0.7706 |

B เพิ่ม Recall@5 7.69 percentage points และ MRR@10 0.1193 เมื่อเทียบ A ไม่ใช้ C ในแอปนี้เพื่อลดภาระ inference ของ reranker ผลนี้เป็น retrieval quality เดิม ไม่ใช่ answer accuracy หรือผลของ agent ที่เปลี่ยน query เอง

ชุดข้อมูลมี 177 แถว ใช้ gold 162 ข้อ (dev 106/test 56) และตัด rejected 15 ข้อ ผล agent evaluation ใช้ dev sample ที่ล็อก 30 ข้อ เป็น development result แยกจาก frozen test มี abstention decision accuracy, citation primary-evidence coverage และ character F1 โดย character F1 เป็นเพียง text overlap ไม่ใช่ความถูกต้องทางคลินิก ดูผลรันจริงและข้อจำกัดใน `reports/gemma_dev_metrics.json` เมื่อ evaluation เสร็จ

## สิ่งที่ตรงกับโจทย์ Project

| Capability | Implementation |
|---|---|
| 1 Structured output | Pydantic answer/tool schemas + bounded repair |
| 2 Retrieval/RAG | Frozen hybrid retrieval + evidence/citations |
| 3 Retrieval evaluation | Gold labels + reproducible saved-hit metrics + A/B baseline |
| 4 Agentic tool calling | Gemma native search_docs loop + stop conditions |
| 6 Served interface | FastAPI REST API + Thai browser UI |

มี incremental Git commits สำหรับงานนี้ อ่าน proposal และ demo script ใน `docs/` และรายงานผลจริงใน `reports/` ยังต้องตรวจความพร้อมของ public corpus/repository และส่ง PDF/demo URL ตามรายการส่งจริง

## สถานะการตรวจล่าสุด

- Unit/API tests ผ่าน 30 ข้อ ครอบคลุม protocol, validation, budget, error และ HTTP boundaries ด้วย model/retriever จำลอง
- เรียก Gemma ผ่าน class proxy จริงได้ และได้ native `search_docs` tool call กลับมา การตรวจนี้ยังไม่ได้ส่ง corpus ให้ model
- โหลด BGE-M3/index จากสำเนาในโปรเจคนี้และค้นหลักฐานจริงได้
- คำนวณ strict retrieval metrics จาก frozen ranked hits ได้ตรงเดิมทั้ง 6 runs
- SHA-256 ของไฟล์ต้นทางทั้ง 48 ไฟล์ที่อ่านยังตรงกับก่อนคัดลอก ดู `reports/source_integrity.json`
- Dev evaluation 30 ข้อยังไม่เริ่ม: ระบบอนุมัติการทำงานปฏิเสธการส่งคำถามและข้อความ corpus ไปยัง class proxy โดยขอสิทธิ์ส่งข้อมูลที่ชัดเจนเพิ่ม ยังไม่มีผล Gemma answer quality ให้สรุป
- API health ผ่าน แต่การเปิดแท็บใน Codex ติด webview attach timeout จึงยังไม่ได้ยืนยันหน้าเว็บด้วยภาพหรือการใช้งาน end-to-end

รายงาน PDF เป็นฉบับร่าง 6 หน้า สร้างได้ด้วย `.venv312\Scripts\python scripts/build_report.py` และเก็บที่ `output/pdf/NCD_GEMMA_PROJECT_REPORT_TH.pdf` ต้องรัน agent evaluation แล้วสร้างใหม่ก่อนใช้เป็นฉบับส่ง ข้อมูลผู้จัดทำและ public demo link ยังต้องเติม

## การเผยแพร่และข้อจำกัด

ต้นทางเป็น private repository และ handoff ระบุว่าบาง corpus text ใช้ภายในทีมเท่านั้น จึงไม่ได้ commit gold, chunks, index, raw answers หรือ source PDFs การมี import script จาก local private artifacts ยังไม่ทำให้ผู้ตรวจที่ไม่มีสิทธิ์เข้าถึงข้อมูล reproduce ได้จาก public GitHub เพียงอย่างเดียว **Q1 เรื่อง public reproducibility ยังต้องจัดการสิทธิ์หรือเลือก corpus ที่เผยแพร่ได้ก่อนส่ง** ถ้าเปลี่ยน corpus ต้อง version และประเมินชุดใหม่ ไม่คัดตัวเลข v12 ไปอ้างกับ subset

แอปนี้เป็นเครื่องมืออ่านเอกสาร ไม่ใช้วินิจฉัยรายบุคคล Gold เดิมตรวจความตรงกับเอกสาร ไม่ใช่การรับรองทางคลินิก Retrieval score ไม่ใช่ confidence ในคำตอบ ข้อจำกัดที่ต้องดูในการประเมินคือข้อมูลนอกขอบเขต เงื่อนไขเฉพาะกลุ่ม ตัวเลขจากตาราง และ citation ที่มี quote จริงแต่ไม่สนับสนุนคำตอบทั้งหมด

## Attribution และเอกสารอ้างอิง

- [Thai NCD Guideline QA](https://github.com/Chaiporn2005/thai-ncd-guideline-qa): retrieval modules, gold, artifacts และผล frozen ของทีม อ้าง snapshot ที่บันทึกไว้ใน provenance ไม่อ้างว่าเริ่มสร้างส่วนนี้ใหม่ในวิชา LLM
- [โจทย์ Project](https://courses.nat-d.uk/courses/building-llm-powered-applications/courseworks/20): class proxy/model, capability families, baseline, report 4–8 หน้า และ demo 3–6 นาที
- [OpenAI Docs: Function calling](https://developers.openai.com/api/docs/guides/function-calling): รูปแบบ assistant tool calls และ tool results ที่ใช้ tool_call_id
