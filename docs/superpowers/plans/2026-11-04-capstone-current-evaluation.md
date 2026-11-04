# Capstone Current Pipeline Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** วัด retrieval และคำตอบของแอป Capstone ปัจจุบันใหม่ เทียบ baseline ที่เปลี่ยนเพียงวิธีค้น โดยแยกหลักฐานจากงานเก่าอย่างตรวจย้อนกลับได้

**Architecture:** สร้าง harness เฉพาะงานนี้โดยนำเข้า production Agent, ProxyClient และ EvidenceRetriever ไม่คัดลอกหรือแก้ logic การตอบ ใช้ evaluation-only adapter เลือก variant A/B และ tracing search แล้วฉีด agent ใน FastAPI instance สำหรับ eval เพื่อใช้ route/validation/request options จริง ผลและ scorer อยู่คนละขั้นเพื่อไม่ส่ง gold เข้า runtime

**Tech Stack:** Python 3.12, pytest, FastAPI TestClient, OpenAI SDK, Pydantic, retriever ใน repo ปัจจุบัน; ไม่เพิ่ม dependency โดยไม่จำเป็น

**Spec:** `docs/superpowers/plans/2026-11-04-capstone-evaluation-spec.md`

## Global Constraints

- PLAN ONLY: รอคำสั่งผู้ใช้ก่อน implementation, model call, commit หรือ push
- Project root ต้องเป็น `D:/KMITL/LLMapp/ncd-gemma`; run namespace `capstone-current-v1`
- ห้ามเปลี่ยน production answering logic, gold, index หรืออีก repository เพื่อให้คะแนนดี
- Corpus/gold ใช้เป็น input พร้อม hash เท่านั้น; ห้ามอ่าน `data/frozen`, `reports/evaluations/v32` หรือคำตอบเก่าเข้า runner/scorer
- `model="gemma-4-E4B-it"`, temperature=0, use_cache=false, use_reranker=true; ค่า budget ทั้งหมดตาม spec
- คงไฟล์แก้ค้างของผู้ใช้ ไม่ reset/stash/drop; commit เฉพาะไฟล์ที่เกี่ยวข้องเมื่อได้รับอนุญาต execution และตรวจ staging แล้ว ไม่มี push ในแผน
- ไม่แก้ UI จึงไม่ต้องเปลี่ยน design contract; หากภายหลังแตะ UI ต้องอ่าน design.md/component.md และ Hallmark + ui-ux-pro-max ก่อน

## Review Focus

- Gold/ผลอีกงานหลุดเข้า inference หรือ scoring: ต้อง reject foreign run identity และ gold request payload (Tasks 1–2)
- โค้ด/settings เปลี่ยนระหว่างรัน รวม ContextVar cache/reranker: ต้องหยุด ไม่ปนผล (Tasks 1–2)
- ข้อหลายหน้า/ฉบับหรือประชากรผิดและ passage สั้น: ต้องวัดหลักฐานที่คืนจริง ไม่ใช้ parent ช่วยเพิ่มคะแนน (Task 3)
- Proxy ขัดข้อง/รันขาด/response ซ้ำ: ต้องเก็บ error และปฏิเสธ complete report เมื่อไม่ครบ (Tasks 2–4)
- Baseline ไม่แพ้หรือ reviewer เห็นชื่อแขนก่อนตรวจ: ต้องไม่ประกาศ improvement และต้องสร้าง review packet แบบปิดชื่อแขน (Tasks 3–4)

---

## File Structure

สร้าง package `src/ncd_gemma/capstone_eval/` มี `__init__.py`, `protocol.py` (manifest/selection/hash), `runner.py` (adapters/live paths/checkpoints), `metrics.py` (scoring/review export), `__main__.py` (CLI) ไม่แก้ CLI รุ่นเก่าที่ `evaluate retrieval` ยังเป็น frozen replay

สร้าง tests `tests/test_capstone_protocol.py`, `tests/test_capstone_runner.py`, `tests/test_capstone_metrics.py` และ `docs/CAPSTONE_CURRENT_EVALUATION_TH.md`

ผลใหม่: `reports/capstone-current-v1/manifest.json`, `questions.jsonl`, `metrics.json`, `review_packet.jsonl`, `verification.json`; raw private: `private/capstone-current-v1/{pilot,retrieval,answers,review_key}.jsonl` ไม่เขียนทับไฟล์เดิม ไม่ commit raw โดยอัตโนมัติ

### Task 1: ล็อก protocol และชุดคำถาม

**Files:** Create `src/ncd_gemma/capstone_eval/{__init__,protocol}.py`; Test `tests/test_capstone_protocol.py`

**Interfaces:** `select_questions(gold_path: Path) -> list[dict]`; `build_manifest(root: Path, questions: list[dict]) -> dict`; `verify_manifest(root: Path, manifest: dict) -> None`. Manifest มี project_id, run_id, code/data/config/question/prompt hashes, full settings, versions, ordered qids, arms, budgets และ selection rule; ห้าม key/secret อยู่ใน manifest

- [ ] เขียน tests: `test_selection_30_six_types` asserts len=30, แต่ละ type=5, answerable=25, qids deterministic; `test_foreign_project_rejected` raises ValueError; `test_code_or_settings_drift_rejected` แก้ fixture byte/option แล้ว verify ต้อง fail; `test_manifest_contains_no_credentials` ยืนยันไม่มีค่าจำลอง secret
- [ ] รัน `.venv312/Scripts/python.exe -m pytest tests/test_capstone_protocol.py -q` ต้อง FAIL เพราะ module ยังไม่มี
- [ ] Implement interfaces ตาม spec: ใช้ round-robin types และ SHA256(`ncd-gemma-dev-v1:qid`) แบบ selection เดิม อ่าน gold โดยตรง ไม่ import frozen metrics; hash `src/ncd_gemma/**/*.py`, `src/ncdqa/**/*.py`, configs, schemas, corpus/index/table artifacts และ lockfiles ที่ runtime ใช้ บันทึก dirty snapshot hashes ควบคู่ commit ไม่ใช้ commit อย่างเดียว
- [ ] รัน tests เดิม ต้อง PASS; ตรวจ settings ของ launcher ที่จะส่งกับค่าที่เสนอโดยแสดงเฉพาะ non-secret หากไม่ตรงหยุดให้ผู้ใช้ตัดสิน
- [ ] ตรวจ diff และ commit เฉพาะ task นี้เมื่อได้รับอนุญาต execution: `feat: lock capstone evaluation protocol`

### Task 2: Runner ใช้ pipeline ปัจจุบันและ baseline แบบควบคุม

**Files:** Create `src/ncd_gemma/capstone_eval/runner.py`; Test `tests/test_capstone_runner.py`

**Interfaces:** `ArmRetriever(base: EvidenceRetriever, variant: str)` มี `search(args: SearchArgs) -> list[dict]` เรียก `base.search(args, variant=variant)` และบันทึกผลทุก call; `run_retrieval(root: Path, manifest: dict) -> Path`; `run_answers(root: Path, manifest: dict, *, pilot: bool=False) -> Path`. Consumes Task 1 verify/selection. Produces JSONL มี run/manifest/arm/qid/question hashes, stage, status, timing, actual sources/trace และ error category

- [ ] เขียน tests: `test_only_variant_differs` spy เห็น A/B แต่ SearchArgs/settings เท่ากัน; `test_http_path_uses_real_request_options` fake model ที่ขอบ network เห็น cache=false/reranker=true และ flags reset หลัง error; `test_gold_never_enters_runtime` spy ยืนยัน request มี question/options เท่านั้น ไม่เห็น answer/evidence labels; `test_resume_rejects_foreign_or_duplicate_records` raises ValueError; `test_outage_stops_at_three` มี error records 3 รายการและไม่เรียกข้อถัดไป
- [ ] รัน `.venv312/Scripts/python.exe -m pytest tests/test_capstone_runner.py -q` ต้อง FAIL จาก module/interfaces ที่ยังไม่มี
- [ ] Implement adapters ใน isolated evaluation process: import server app, จัด `server._agent` เป็น Agent ที่ใช้ ProxyClient จริงและ ArmRetriever; TestClient POST `/api/ask` โดยไม่เรียก production server ที่ผู้ใช้เปิดอยู่ ไม่ mock ผลใน live mode ไม่แก้ route หรือ agent code คืน global state ใน finally; ใช้ client credentials จาก env หากเปิด auth และไม่ log header
- [ ] Implement run ledger ตาม spec: ต่อ qid สลับ A/B ด้วย parity ของ SHA256(qid), concurrency=1; flag context ทั้ง retrieval/answers; hash verify ก่อนเริ่ม/ก่อนแต่ละ request/หลังจบ; checkpoint atomic; resume เฉพาะ completed records identity ตรง ไม่ลบ error แล้วเขียนผลดีแทน ยืนยัน code drift ทำ run incomplete
- [ ] รัน tests เดิม ต้อง PASS; เพิ่ม `test_drift_midrun_preserves_incomplete` และ `test_budget_stops_without_extra_call` ต้อง PASS ที่ 62 app requests/744 proxy attempts/3 ชั่วโมงตาม spec ไม่มี live call ใน tests
- [ ] ตรวจ diff และ commit เฉพาะ task นี้: `feat: run isolated current-pipeline evaluation`

### Task 3: Metrics และ review packet ที่ไม่ปนผลเก่า

**Files:** Create `src/ncd_gemma/capstone_eval/metrics.py`; Test `tests/test_capstone_metrics.py`

**Interfaces:** `score_retrieval(records: list[dict], questions: list[dict]) -> dict`; `score_answers(records: list[dict], questions: list[dict]) -> dict`; `make_review_packet(records: list[dict], questions: list[dict]) -> tuple[list[dict], list[dict]]`; `summarize(root: Path, manifest: dict) -> dict`. Return review tuple=(public anonymized packet, private arm key). Consumes raw record schema จาก Task 2 และ locked qids Task 1

- [ ] เขียน tests: `test_two_evidence_one_covered_recall_half` asserts Recall@5=.5; `test_wrong_edition_not_relevant` asserts 0; `test_passage_not_parent_scored` asserts 0 เมื่อ quote มีใน parent แต่ไม่มีใน returned passage; `test_error_kept_in_denominator` asserts n=30 และ 1 error ทำ error_rate=1/30; `test_missing_arm_record_blocks_complete` raises ValueError; `test_negative_delta_not_improvement` asserts improvement=False; `test_review_packet_hides_arm` asserts ไม่มี arm/variant/run filename ใน packet
- [ ] รัน `.venv312/Scripts/python.exe -m pytest tests/test_capstone_metrics.py -q` ต้อง FAIL ก่อน implementation
- [ ] Implement strict covers ตามกติกา edition/page/quote ใน `src/ncdqa/retrieval/evaluate.py` โดยนำเข้าเฉพาะ scoring functions ได้ ห้ามอ่าน saved hits; k=5 กับลำดับ passages จริง ใช้ 25 answerable สำหรับ retrieval; 30 ทั้งหมดสำหรับ decision/error metrics, 25 สำหรับ citation hit; เก็บค่าที่ไม่ปัดเศษก่อนคำนวณ delta
- [ ] Implement completeness checks: ต้องมี 30 qids × 2 arms ต่อ stage รวม errors ที่มี record; ห้ามเติม record จาก pilot/v32/frozen; API attempts และ model rounds แยกกัน; latency รายงานเชิงพรรณนาพร้อมข้อจำกัด warmup/order/hardware
- [ ] สร้าง review rubric ต่อข้อ: สาระครบ/บางส่วน/ผิด/งดถูก/งดเกิน/service error พร้อม source quote และเหตุผล แสดง reviewer identity/type และ pending count; ยังไม่สร้าง semantic success score หาก review ไม่ครบ ห้ามตั้ง verdict จาก status=answered
- [ ] รัน tests เดิม ต้อง PASS; ตรวจ diff และ commit: `feat: score fresh capstone evidence and export review packet`

### Task 4: CLI, preflight และรันจริงหลังผู้ใช้อนุมัติ

**Files:** Create `src/ncd_gemma/capstone_eval/__main__.py`, `docs/CAPSTONE_CURRENT_EVALUATION_TH.md`; outputs ตาม File Structure

**Interfaces:** `python -m ncd_gemma.capstone_eval {plan,verify,pilot,retrieval,answers,summarize} --run capstone-current-v1`. CLI ใช้ interfaces Tasks 1–3; คำสั่งอ่าน/verify ไม่เรียกโมเดล `plan` ปฏิเสธ overwrite ถ้า directory มีผลหรือ manifest ไม่ตรง

- [ ] เพิ่ม CLI tests ใน `tests/test_capstone_protocol.py`: `test_verify_makes_no_network_calls`, `test_plan_refuses_overwrite`, `test_old_artifacts_cannot_satisfy_new_run`; รันให้ FAIL ก่อน implementation
- [ ] Implement CLI และ README เฉพาะการประเมินใหม่นี้ พร้อม budget/วิธี resume/ข้อจำกัดข้อมูล exposed และผลกระทบของการเรียก proxy
- [ ] รัน `.venv312/Scripts/python.exe -m pytest tests/test_capstone_protocol.py tests/test_capstone_runner.py tests/test_capstone_metrics.py -q` ต้อง PASS แล้วรัน full pytest ครั้งเดียวเพื่อตรวจการ import server/state ไม่กระทบ tests เดิม
- [ ] ตั้ง `$env:PYTHONPATH="$PWD/src"`; รัน `.venv312/Scripts/python.exe -m ncd_gemma.capstone_eval plan --run capstone-current-v1` ต้องได้ manifest แยก มี 30 qids กับ 2 arms ไม่มี API calls; ผู้ใช้ต้องได้เห็น effective settings และข้อจำกัดก่อนเริ่ม live execution
- [ ] รัน `... pilot --run capstone-current-v1` 2 requests ตาม spec; ตรวจ native search_docs, no cache, settings และ request counts; หากเป็น proxy/config/schema blocker ให้หยุด ไม่อ้อม guard ผลคำตอบไม่ดีอย่างเดียวไม่ใช่เหตุให้เปลี่ยนโจทย์
- [ ] รัน `... retrieval --run capstone-current-v1` ต้องได้ 60 fresh records ไม่มี LLM calls; จากนั้น `... answers --run capstone-current-v1` ต้องได้ 60 records ของชุดเต็มหรือสถานะ incomplete ที่อธิบายสาเหตุ
- [ ] รัน `... verify --run capstone-current-v1` แล้ว `... summarize --run capstone-current-v1`; PASS หมายถึง provenance/completeness/metrics ถูกต้อง ไม่ได้หมายถึง baseline ถูกชนะ ส่งตาราง delta และ failure cases ให้ผู้ใช้ดู แม้ผลติดลบ
- [ ] หยุดให้ผู้ใช้ตรวจผลและ review packet ก่อนเปลี่ยนข้อความอ้างผลในรายงาน/เว็บ/คลิป การแก้เหล่านั้นเป็นแผนถัดไป ห้ามเอาผลเก่ามาปิดตัวเลขที่ยัง pending
- [ ] ตรวจ stage แล้ว commit harness/docs/aggregate ที่ตรวจแล้วเมื่ออยู่ในอนุมัติ execution; ไม่ commit secrets/raw automatically และไม่ push

## Self-Review

- Spec coverage: Task 1 dataset/provenance; Task 2 real app/proxy/controls; Task 3 labelled metrics/baseline/failures; Task 4 reproducibility/live budget/result handoff
- Scope exclusions: ไม่ปรับ pipeline เพื่อชนะ, ไม่ประเมิน reranker OFF, ไม่อ้าง held-out, ไม่ปรับรายงาน/คลิปอัตโนมัติ, ไม่ส่งงาน/เผยแพร่
- Interfaces และ paths ใช้ชุดเดียวทั้งเอกสาร; scoring ไม่มี dependency ต่อ results ของอีกงาน
- Review Focus ทั้ง 5 มี tests ที่ระบุชื่อและ expected assertions; tests ใช้ fake network ส่วน live run ใช้ proxy จริง แยกกัน
- Improvement เป็นผลที่ต้องวัด ไม่ใช่เกณฑ์ให้ runner วนหาคะแนนดี; ถ้าไม่ชนะต้องหารือแผนใหม่

## Handoff

รอผู้ใช้ตรวจ protocol, baseline, ชุดคำถาม และ budget ก่อนลงมือ แนะนำ Native สำหรับขอบเขตนี้เพื่อคุม harness กับเส้นทางแอปให้อยู่ในบริบทเดียว ผู้ใช้เลือก Native หรือ Subagent-driven ได้ภายหลัง ไม่มีการเริ่มงานหรือเรียก subagent จากแผนนี้เอง

คำสั่งเพิ่มของผู้ใช้ให้ทำรายการ “งานต่อไป” จนสมบูรณ์บันทึกไว้ใน Spec แล้ว แผน v1 นี้เป็นการวัดก่อนแก้ ไม่ใช่การปิดโครงการทั้งหมด หลังได้ failures จึงต้องเสนอแผนแก้ schema/repair และประเมินหลังแก้ แยก run version รวม blind review, ชุดคำถามใหม่ และ reranker ablation ก่อนปรับรายงานเป็นผลของงานที่ทำเสร็จ การอนุมัติ v1 ไม่ใช่การอนุมัติแก้ระบบหรือเรียก API แบบไม่จำกัด
