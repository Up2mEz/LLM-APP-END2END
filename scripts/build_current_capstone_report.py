"""Build the submission from a complete fresh run and complete blinded judgments."""
from __future__ import annotations
import json
from pathlib import Path
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[1]
RUN='capstone-current-v2'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def rows(path):return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
def fmt(x):return f'{x:.4f}'
def clean(s):return str(s).replace('|','/').replace('\n',' ').strip()

def main():
    out=ROOT/'reports'/RUN;private=ROOT/'private'/RUN
    m=read(out/'metrics.json');j=read(out/'judge_metrics.json')
    ab=read(ROOT/'reports/capstone-reranker-ablation-v1/metrics.json')
    if not ab.get('complete'):raise ValueError('Complete reranker ablation required')
    if not m.get('complete') or not j.get('complete') or m['run_id']!=RUN or j['run_id']!=RUN:raise ValueError('Complete fresh metrics and judgments required')
    raw=rows(private/'answers.jsonl');key={r['item_id']:r for r in rows(private/'review_key.jsonl')}
    answers={(r['qid'],r['arm']):r for r in raw};judgments=rows(out/'judge_verdicts.jsonl')
    a,b=m['retrieval']['dense_default'],m['retrieval']['hybrid_current'];ja,jb=j['arms']['dense_default'],j['arms']['hybrid_current']
    delta=b['recall@5']-a['recall@5']
    conclusion=('ผลรอบนี้สนับสนุนการเลือก hybrid เพราะเพิ่ม Recall@5 '+fmt(delta)+' เมื่อคงส่วนอื่นเหมือนกัน' if delta>0 else 'ผลรอบนี้ยังไม่สนับสนุนว่าการเลือก hybrid เพิ่ม Recall@5 เหนือ baseline จึงยังปิดเงื่อนไข measured improvement ของโจทย์ด้วย metric นี้ไม่ได้')
    retrieval_table='\n'.join(f"| {label} | {fmt(r['recall@5'])} | {fmt(r['hit@5'])} | {fmt(r['mrr@5'])} |" for label,r in [('Dense baseline',a),('Hybrid current',b)])
    answer_table='\n'.join(f"| {label} | {x['successes']}/30 | {fmt(x['semantic_success'])} | {fmt(m['answers'][arm]['abstention_decision_accuracy'])} | {m['answers'][arm]['errors']} |" for label,arm,x in [('Dense baseline','dense_default',ja),('Hybrid current','hybrid_current',jb)])
    verdict_table='\n'.join(f"| {v} | {ja['verdict_counts'].get(v,0)} | {jb['verdict_counts'].get(v,0)} |" for v in ['correct','partial','wrong','unsupported','correct_abstention','false_abstention','service_error','uncertain'])
    cases=[];case_types=set()
    ordered=sorted(judgments,key=lambda r:(key[r['item_id']]['arm']!='hybrid_current',r['item_id']))
    for r in ordered:
        if r['verdict'] in ('correct','correct_abstention'):continue
        if r['verdict'] in case_types:continue
        k=key[r['item_id']];record=answers[k['qid'],k['arm']]
        reason=clean(r['reason'])
        if record['prediction'].get('stop_reason')=='proxy_http_429':reason='Class proxy ส่ง HTTP 429 จึงไม่ได้คำตอบสมบูรณ์จากระบบ กรณีนี้เป็นความผิดพลาดของบริการและยังนับอยู่ในตัวหาร'
        cases.append(f"### {k['qid']} ({k['arm']}): {r['verdict']}\n\nคำถาม: {clean(record['question'])}\n\nผลตรวจ: {reason}\n\nระบบหยุดด้วย {clean(record['prediction'].get('stop_reason','ไม่ระบุ'))} หลักฐานการตัดสิน: {clean('; '.join(r['evidence_refs']))[:450]}")
        case_types.add(r['verdict'])
        if len(cases)==3:break
    if not cases:cases=['ไม่พบ failure ตาม rubric ใน 60 คำตอบรอบนี้ ผลบน dev ชุดเล็กยังไม่รับประกันว่าระบบจะตอบคำถามใหม่ได้ครบถ้วน']
    times={arm:statistics.median(r['elapsed_seconds'] for r in raw if r['arm']==arm) for arm in ('dense_default','hybrid_current')}
    paired_text=''
    paired_dir=ROOT/'reports/paired-agent-v30-current-20261105'
    if (paired_dir/'judge_metrics.json').exists():
        pj=read(paired_dir/'judge_metrics.json');ps=read(paired_dir/'paired_summary.json')
        if not pj.get('complete'):raise ValueError('Paired judgments incomplete')
        paired_text=f'''### การเทียบ agent รุ่นเก่ากับปัจจุบันภายใต้เงื่อนไขเดียวกัน

ทดลองเพิ่มด้วยคำถามเดิม 60 ข้อ รุ่นละหนึ่งคำตอบ ใช้โค้ด v30 ที่กู้และตรวจ hashes แล้ว เทียบรุ่นปัจจุบัน โดยใช้ตัวเชื่อมต่อโมเดล ค่าตั้ง และการปิดแคชชุดเดียวกัน ทั้งคู่ค้นแบบผสมและเปิด reranker สลับลำดับรุ่นที่ตอบก่อน แล้วให้ Luna 6 xhigh ตรวจแบบซ่อนชื่อรุ่น

| รายการ | รุ่นเก่า | รุ่นปัจจุบัน |
| --- | --- | --- |
| ผ่านเกณฑ์ รวมการงดตอบถูก | {ps['old_successes']}/60 | {ps['current_successes']}/60 |
| บริการล้มเหลวที่รวมในตัวหาร | {pj['arms']['old_v30']['verdict_counts'].get('service_error',0)} | {pj['arms']['current']['verdict_counts'].get('service_error',0)} |

ทั้งคู่ผ่านตรงกัน {ps['both_success']} ข้อ ไม่ผ่านตรงกัน {ps['both_fail']} ข้อ และแต่ละรุ่นผ่านฝ่ายเดียว 2 ข้อ ผลเสมอรอบนี้ยังไม่สนับสนุนว่ารุ่นใหม่ตอบถูกกว่า และไม่ได้พิสูจน์ว่าเทียบเท่ากันทุกคำถาม สามในสี่คู่ที่ผลต่างกันเกี่ยวข้องกับ HTTP 429 คงใช้รุ่นปัจจุบันเพื่อการควบคุมแคชและแสดงหลักฐาน ไม่อ้างว่าฉลาดขึ้นจากเลขรุ่น รายละเอียดอยู่ใน docs/PAIRED_AGENT_EVALUATION_TH.md

'''
    text=f'''# NCD Evidence

ระบบถามตอบจากหลักฐานในเอกสาร NCD ภาษาไทย

รายงานโครงงานรายวิชา Building LLM-Powered Applications

ผู้จัดทำ นายธนกฤต เสมอหน้า รหัสนักศึกษา 67070060

ผู้สอน ดร. ณัฏฐ์ ดิลกธนากุล

### บทคัดย่อ

โครงงานนี้พัฒนาแอปถามตอบจากเอกสารโรคไม่ติดต่อเรื้อรังภาษาไทย ผู้ใช้ถามด้วยภาษาธรรมชาติและเปิดดูเอกสาร ฉบับพิมพ์ หน้า และข้อความที่ใช้ตอบได้ ระบบใช้ Gemma ผ่าน class proxy ร่วมกับ retrieval, native tool calling และการตรวจ structured output เพื่อจำกัดคำตอบให้อ้างอิงหลักฐานที่ค้นพบ

ประเมิน pipeline ปัจจุบันใหม่ในชุด {RUN} ด้วย gold dev 30 ข้อ เทียบ dense baseline กับ hybrid โดยคงส่วนอื่นเหมือนกัน Strict Recall@5 บนข้อที่ตอบได้ 25 ข้อเท่ากับ {fmt(a['recall@5'])} และ {fmt(b['recall@5'])} ตามลำดับ การตรวจคำตอบแบบซ่อนชื่อแขนด้วย GPT-6-Luna xhigh ให้ semantic success {ja['successes']}/30 และ {jb['successes']}/30 ผลนี้เป็นการประเมินบนข้อมูลที่เคยใช้พัฒนาและมีความคลาดเคลื่อนจาก LLM-as-judge จึงไม่ใช้ยืนยันความถูกต้องทางคลินิก

### 1. ปัญหา ผู้ใช้ และวัตถุประสงค์

แนวทาง NCD มีหลายฉบับ หลายกลุ่มประชากร และตารางที่ต้องอ่านร่วมกับหัวคอลัมน์ การค้นพบคำตรงกันอาจนำไปสู่คำตอบผิดบริบท แอปช่วยนักศึกษาและผู้ที่อ่านเอกสารลดเวลาค้น พร้อมตรวจที่มาของคำตอบได้ วัตถุประสงค์คือสร้างระบบครบเส้นทางจากคำถามถึงหลักฐานและวัดคุณภาพเทียบ baseline ขอบเขตคือการช่วยอ่านเอกสาร ไม่รวมการวินิจฉัยหรือจัดแผนรักษาเฉพาะบุคคล

## 2. สถาปัตยกรรมและการออกแบบ

![ภาพที่ 1 สถาปัตยกรรมและเส้นทางตอบคำถาม](diagrams/architecture.svg)

React รับคำถามและส่งผ่าน FastAPI ไปยัง Agent ซึ่งใช้ from openai import OpenAI เรียก gemma-4-E4B-it ผ่าน class proxy อ่าน OPENAI_API_KEY และ OPENAI_BASE_URL จาก environment คำถามในขอบเขตเริ่มด้วย native search_docs โค้ดตรวจชื่อ tool และ SearchArgs ก่อนเรียก retrieval และคืนผลพร้อม tool_call_id ที่ตรงกัน

Agent ใช้หลักฐานที่ค้นได้สร้างคำตอบแบบมี schema พร้อม citations จากนั้นตรวจ source IDs, quote และเงื่อนไขที่เกี่ยวข้อง บางคำถามใช้ source-bound reader อ่านค่าที่ตรวจตรงหลักฐานได้ กรณีอื่นให้ Gemma เสนอและตรวจคำตอบ หาก schema หรือหลักฐานไม่ผ่านจะซ่อมภายใน budget หรืองดตอบ ไม่ส่ง gold answer เข้าเส้นทางให้บริการ

กำหนด temperature=0, ไม่เกิน 6 model rounds และ 3 searches, request timeout 45 วินาที เวลารวม 150 วินาที และ context 18,000 ตัวอักษร หยุดเมื่อคำตอบผ่าน หลักฐานไม่พอ หรือถึงขีดจำกัด ไม่มี tool สำหรับ shell หรือการอ่านไฟล์ตามคำสั่งโมเดล

## 3. ข้อมูลและเทคนิคที่ใช้

Corpus ใช้ snapshot normalized-v12 ที่มี 66 เอกสาร Child chunks 23,819 ชิ้น Parent chunks 4,347 ชิ้น และ dense vectors 1,024 มิติ Gold มี 162 ข้อ (dev 106 และ test 56) จากทั้งหมด 177 แถว ส่วน rejected 15 ข้อไม่นำมาประเมิน ข้อมูลและโมดูล retrieval ที่นำมาใช้มี provenance และ hashes ใน repository

ผู้จัดทำให้ coding agent ร่างคำถามและคำตอบ จากนั้นตรวจ gold ร่วมกับเพื่อน ผู้จัดทำตรวจ dev ทั้งหมดเอง และแบ่งตรวจ test กับเพื่อนเท่า ๆ กัน การตรวจ gold นี้แยกจากการให้ LLM-as-judge ตรวจคำตอบแอปในรอบปัจจุบัน

Dense search ใช้ bge-m3 ส่วน hybrid รวม dense กับ BM25 char3 ผ่าน min-max normalization และ convex fusion alpha=0.6 ใช้ candidate pool 100 ค่าตั้งต้นสืบทอดจาก retrieval configuration แอปเพิ่ม passage focus, ข้อความข้างเคียง, table context และ bge-reranker-v2-m3 ก่อนส่งหลักฐานให้ Agent

| Capability family | การใช้งานและเหตุผล |
| --- | --- |
| 1 Structured output | Pydantic ตรวจชนิดข้อมูลและ citations เพื่อให้ API รับผลที่มีรูปแบบแน่นอน |
| 2 Retrieval / RAG | ค้นเอกสารก่อนตอบและแสดง quote ให้ผู้ใช้ตรวจที่มา |
| 3 Retrieval evaluation | วัด Recall@5, Hit@5 และ MRR@5 บน gold พร้อม baseline |
| 4 Agent loop | โมเดลเรียก search_docs ภายใต้ allow-list และ stop conditions |
| 6 Served interface | FastAPI เชื่อมหน้าเว็บ React สำหรับถามและตรวจหลักฐาน |

ทั้งห้าครอบคลุม evaluation และ agentic family ตามโจทย์ ไม่จำเป็นต้องเพิ่มทุกเทคนิคในรายวิชา

## 4. วิธีประเมิน pipeline ปัจจุบัน

ล็อกชุด {RUN} และ hash ของโค้ด ข้อมูล คำถาม และ configuration ก่อนรัน คัด dev 30 ข้อด้วย SHA-256 ตามกฎที่บันทึกไว้ มี condition, fact, multi_page, number_unit, table และ unanswerable อย่างละ 5 ข้อ เป็น answerable 25 ข้อและ unanswerable 5 ข้อ ชุดนี้เป็น exposed dev ไม่ใช่ held-out

Baseline ใช้ variant A (dense) ส่วนระบบปัจจุบันใช้ variant B (hybrid) ทั้งคู่คง passage focus, table context, reranker ON, prompt, model และ agent budget เหมือนกัน จึงวัดผลของวิธีค้นขั้นต้น และไม่เรียก baseline นี้ว่า no-RAG หรือ dense ล้วน

Retrieval stage เรียก retriever จริงใหม่ด้วยคำถามเต็ม top_k=5 ทั้ง 60 รายการ ไม่อ่าน saved ranked hits คะแนน strict relevance ตรวจ edition หน้า และ quote coverage ของ passage ที่คืนจริง Recall@5 เป็นค่าเฉลี่ยสัดส่วน gold evidence ที่พบต่อข้อ Hit@5 วัดว่ามีหลักฐานตรงอย่างน้อยหนึ่งรายการ และ MRR@5 วัดส่วนกลับอันดับแรกที่เกี่ยวข้อง ใช้ตัวหาร 25 ข้อที่ตอบได้

Answer stage ส่ง 30 ข้อ × 2 แขนผ่าน /api/ask ของ FastAPI instance สำหรับ eval ใช้ Agent, ProxyClient และ EvidenceRetriever ตัวเดียวกับแอป เปิด use_cache=false ทุกคำขอ มี pilot 2 requests ซึ่งไม่รวมคะแนน จำกัดรอบทั้งหมด 62 app requests และ 744 proxy attempts เก็บ service errors ไว้ในผลและหยุดเมื่อเกิดติดกันสามครั้ง

GPT-6-Luna reasoningEffort=xhigh ตรวจ packet ที่ซ่อนชื่อแขน โดยเห็นคำถาม gold หลักฐาน และคำตอบพร้อม citations ให้คะแนนสำเร็จเฉพาะ correct หรือ correct_abstention ทุก verdict รวม uncertain และ service_error อยู่ในตัวหาร 30 ต่อแขน T3 transport ไม่เปิดการตั้ง temperature ของ judge จึงไม่อ้างว่า judge ใช้ 0 ส่วน Gemma ที่ตอบใช้ 0 ทุกข้อ

## 5. ผลการทดลองและการแปลผล

ตารางที่ 1 ผล retrieval ใหม่บน answerable dev 25 ข้อ

| ระบบ | Strict Recall@5 | Hit@5 | MRR@5 |
| --- | --- | --- | --- |
{retrieval_table}

{conclusion} การวัดนี้ใช้คำถามเต็มค้นครั้งเดียวต่อข้อ ส่วน Agent อาจเปลี่ยน query ระหว่างตอบ จึงแยกผล retrieval จากผลคำตอบตลอดเส้นทาง

ตารางที่ 2 ผลคำตอบบน dev 30 ข้อ รวมการงดตอบและบริการขัดข้อง

| ระบบ | สำเร็จตาม judge | Semantic success | Decision accuracy | Service errors |
| --- | --- | --- | --- | --- |
{answer_table}

Semantic success ต้องตอบสาระที่ถามครบและหลักฐานรองรับ หรือเป็นการงดตอบที่ถูกต้อง ส่วน decision accuracy วัดเพียงการเลือกตอบหรืองด จึงอาจได้คะแนนดีแม้เนื้อหาผิด Primary citation hit เท่ากับ {fmt(m['answers']['dense_default']['primary_citation_hit'])} และ {fmt(m['answers']['hybrid_current']['primary_citation_hit'])} ตามลำดับ ใช้ตัวหาร 25 ข้อและตรวจหลักฐานที่ถูกอ้าง ไม่ได้ยืนยันความครบของคำตอบทั้งหมด

ค่ามัธยฐานเวลาต่อคำถามในเครื่องนี้คือ dense {times['dense_default']:.1f} วินาที และ hybrid {times['hybrid_current']:.1f} วินาที เวลารวม retrieval, model และ verification หลังโหลดโมเดลแล้ว ผลขึ้นกับฮาร์ดแวร์ บริการ และลำดับคำถาม จึงใช้บอกประสบการณ์ของรอบนี้และไม่อ้างเป็น benchmark ข้ามเครื่อง

การทดลองแยกเปิด/ปิด reranker บน hybrid และคำถามชุดเดียวกันให้ Recall@5 {fmt(ab['reranker_on']['recall@5'])} / {fmt(ab['reranker_off']['recall@5'])} เวลามัธยฐานเฉพาะ retrieval {ab['median_seconds_on']:.2f} / {ab['median_seconds_off']:.2f} วินาที การปิดช่วยลดเวลาค้นแต่พบหลักฐานน้อยลง ผลนี้รองรับการให้ผู้ใช้เลือกโหมด แต่ไม่ได้วัดคุณภาพคำตอบ end-to-end เมื่อปิด reranker

## 6. กรณีผิดพลาดและการวิเคราะห์

{'\n\n'.join(cases)}

ตารางที่ 3 การแจกแจง verdict จาก LLM-as-judge

| Verdict | Dense | Hybrid |
| --- | --- | --- |
{verdict_table}

รอบนี้พบ class proxy ตอบ HTTP 429 จำนวน 3 รายการ (dense 1 และ hybrid 2) เก็บเป็น service errors และไม่เรียกซ้ำแทนผลเดิม การให้คะแนนยังป้องกัน verification_unavailable ถูกนับเป็น correct_abstention แม้ API ส่ง status ว่า insufficient_evidence คำตอบที่ตรวจไม่ได้ใช้ uncertain และอยู่ในตัวหาร การให้ judge เป็นโมเดลยังอาจอ่านเงื่อนไขหรือหลักฐานผิด ต้องอ่านเหตุผลรายข้อประกอบคะแนน

## 7. การทำซ้ำและการตรวจสอบหลักฐาน

{paired_text}

README ระบุการสร้าง Python environment ตั้งค่า class proxy ดาวน์โหลดข้อมูลด้วย scripts/public_data.py fetch เตรียมโมเดล และ build frontend ก่อนใช้ run.ps1 ไม่มี API key ใน manifest หรือรายงาน หลักฐานรอบนี้อยู่ที่ reports/{RUN}/ ส่วน raw และ trace อยู่ใน private/{RUN}/ สำหรับการตรวจในเครื่อง

คำสั่ง python -m ncd_gemma.capstone_eval verify --run {RUN} ตรวจ hash โดยไม่เรียกโมเดล จากนั้น run ใช้ pipeline จริงและ summarize คำนวณผลจาก raw ที่ครบสองแขน คำสั่ง plan ปฏิเสธเขียนทับ manifest เดิม การ resume ข้ามเฉพาะคำขอที่มีผลบันทึกครบ หากมีคำขอค้างไม่ทราบผลจะหยุดแทนการยิงซ้ำโดยอัตโนมัติ

ชุดทดสอบ harness ตรวจการสลับ variant โดยคง options, การแยก pilot, การปฏิเสธข้อมูลซ้ำหรือผิด run, การหยุดเมื่อ outage และการเก็บ errors ในตัวหาร มี regression test สำหรับ verification failure และการขัดข้องระหว่างบันทึก budget กับผลตอบ การทดสอบโค้ดใช้ fixture ส่วนผลในตารางมาจากการเรียกจริง

Judge packet และ rubric มี hash แยก เก็บ verdict รายข้อพร้อมเหตุผลและ source references Collector ตรวจจำนวนและ item IDs ก่อนคำนวณคะแนน ไม่ตีความ status=answered เป็นคำตอบถูก และไม่แก้ gold ตามความเห็น judge คะแนน LLM-as-judge อาจต่างเมื่อเรียกโมเดลใหม่แม้ใช้ protocol เดิม

## 8. ข้อสรุปและข้อจำกัด

โครงงานเชื่อมคำถามจริงกับ class proxy, agent tool, retrieval และหน้าเว็บที่ตรวจหลักฐานได้ มีการประเมินรอบใหม่เทียบ baseline บน pipeline ปัจจุบัน {conclusion} ผล semantic success ของ hybrid คือ {jb['successes']}/30 ตาม rubric ที่ระบุ ความสำเร็จด้านการค้นและด้านคำตอบต้องพิจารณาแยกกัน

ข้อจำกัดหลักคือใช้ exposed dev ขนาดเล็ก เฉพาะโดเมนและฉบับเอกสารใน corpus การเปลี่ยนสำนวน ประชากร หรือเงื่อนไขอาจทำให้ค้นผิดหรืองดตอบเกินจำเป็น การตรวจโดย Luna เป็น LLM-as-judge ไม่มีผู้เชี่ยวชาญตรวจคำตอบรอบนี้ คะแนนจึงไม่ใช่การรับรองความปลอดภัยในการรักษา Ablation วัดโหมดปิด reranker เฉพาะ retrieval และรันคนละช่วงเวลา จึงยังไม่ใช้อนุมานคะแนนคำตอบหรือความเร็วทั้งระบบ

สำหรับการสาธิต ต้องแสดงคำถามจริงหนึ่งกรณีที่สำเร็จและหนึ่งกรณีที่ผิดพลาด พร้อมเปิดข้อความอ้างอิง และพร้อมรับ input ใหม่ต่อหน้าผู้สอน การอธิบาย design choice ใช้ controlled dense/hybrid comparison และแสดงวิธีคำนวณ metric จากหลักฐานรายข้อ

### เอกสารและหลักฐานประกอบ

[Repository: LLM-APP-END2END](https://github.com/Up2mEz/LLM-APP-END2END) — โค้ด README และวิธีเตรียมข้อมูล

provenance/source_snapshot.json และ provenance/public_data_release.json — ที่มาข้อมูลและ hashes

reports/{RUN}/manifest.json, metrics.json, judge_metrics.json และ judge_verdicts.jsonl — การตั้งค่าและผลรอบปัจจุบัน

docs/CAPSTONE_CURRENT_EVALUATION_TH.md และ docs/CAPSTONE_JUDGE_RUBRIC.md — protocol, metric และเกณฑ์ตรวจคำตอบ
'''
    (ROOT/'docs/PROJECT_REPORT_SUBMISSION_TH.md').write_text(text,encoding='utf-8')
    subprocess.run(['node','scripts/render_submission_report.mjs'],cwd=ROOT,check=True)

if __name__=='__main__':main()
