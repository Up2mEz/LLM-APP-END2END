"""Build a six-page Thai course report from measured local artifacts."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/NCD_GEMMA_PROJECT_REPORT_TH.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
pdfmetrics.registerFont(TTFont("Thai", r"C:\Windows\Fonts\tahoma.ttf", shapable=True))
pdfmetrics.registerFont(TTFont("ThaiBold", r"C:\Windows\Fonts\tahomabd.ttf", shapable=True))
pdfmetrics.registerFontFamily("Thai", normal="Thai", bold="ThaiBold")
INK, GREEN, MUTED, LIGHT = map(colors.HexColor, ("#18364e", "#0964aa", "#52697e", "#edf6ff"))
styles = {
    "body": ParagraphStyle("body", fontName="Thai", fontSize=10.5, leading=17, textColor=INK,
                           wordWrap="CJK", shaping=True, spaceAfter=9, alignment=TA_LEFT),
    "h1": ParagraphStyle("h1", fontName="ThaiBold", fontSize=23, leading=33, textColor=INK,
                         wordWrap="CJK", shaping=True, spaceAfter=20),
    "h2": ParagraphStyle("h2", fontName="ThaiBold", fontSize=13, leading=22, textColor=GREEN,
                         wordWrap="CJK", shaping=True, spaceBefore=9, spaceAfter=8),
    "small": ParagraphStyle("small", fontName="Thai", fontSize=8.5, leading=14, textColor=MUTED,
                            wordWrap="CJK", shaping=True, spaceAfter=8),
}
story = []


def p(text, style="body"):
    return Paragraph(escape(str(text)), styles[style])


def add(text, style="body"):
    story.append(p(text, style))


def section(number, title):
    if number > 1:
        story.append(PageBreak())
    add(f"NCD EVIDENCE  /  {number:02d}", "small")
    add(title, "h1")


def table(headers, data, widths):
    cells = [[p(x, "small") for x in headers]] + [[p(x, "small") for x in row] for row in data]
    item = Table(cells, colWidths=[x * mm for x in widths], hAlign="LEFT")
    item.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), LIGHT), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                             ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d5dfd1")),
                             ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                             ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([item, Spacer(1, 10)])


class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 165 * mm, 65 * mm

    def draw(self):
        c = self.canv
        blocks = [(0, 110, 140, "Web UI / FastAPI"), (180, 110, 140, "Agent + validation"),
                  (360, 110, 105, "Gemma proxy"), (180, 40, 140, "search_docs / hybrid"),
                  (360, 40, 105, "Chunks + index")]
        for x, y, w, label in blocks:
            c.setFillColor(LIGHT); c.setStrokeColor(GREEN); c.roundRect(x, y, w, 40, 7, fill=1, stroke=1)
            c.setFillColor(INK); c.setFont("Thai", 9); c.drawCentredString(x+w/2, y+16, label)
        c.setStrokeColor(GREEN)
        for x1, y1, x2, y2 in [(140,130,180,130),(320,130,360,130),(250,110,250,80),(320,60,360,60)]:
            c.line(x1,y1,x2,y2)
        c.setFillColor(MUTED); c.setFont("Thai", 8)
        c.drawString(0, 7, "Gold labels are loaded only by the evaluation harness.")


def read_optional(name):
    path = ROOT / "reports" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


retrieval = read_optional("retrieval_metrics.json")
agent = read_optional("gemma_dev_metrics.json")
plan = read_optional("gemma_dev_plan.json")
validation = read_optional("validation.json")

section(1, "ผู้ช่วยค้นหลักฐาน NCD ภาษาไทย")
add("Project: Building LLM-Powered Applications", "h2")
if not agent:
    add("ฉบับร่าง: ยังไม่ได้ประเมินคำตอบ Gemma แบบ end-to-end", "small")
add("NCD Evidence ใช้ Gemma ผ่าน class proxy เพื่อช่วยค้นและสรุปหลักฐานจากเอกสาร NCD ภาษาไทย ผู้ใช้ถามเป็นภาษาธรรมชาติ แล้วระบบเรียก retrieval tool เพื่อเลือกข้อความที่เกี่ยวข้องก่อนตอบพร้อมเลขหน้า เป้าหมายคือช่วยผู้ใช้ทั่วไปและผู้อ่านแนวทางกลับไปตรวจเอกสารได้สะดวก ไม่ใช้วินิจฉัยหรือสั่งยารายบุคคล")
add("ส่วนที่นำมาใช้ต่อและส่วนที่พัฒนาเพิ่ม", "h2")
add("งานนี้นำ corpus, gold, chunking, document vectors และ hybrid retrieval จาก Thai NCD Guideline QA ของทีมมาใช้ต่อ ส่วนที่เพิ่มสำหรับวิชา LLM คือ OpenAI SDK adapter, native tool calling, agent loop, answer/citation validation, หน้าเว็บ และ evaluation ของการสร้างคำตอบ ไม่ได้อ้างว่าสร้างข้อมูลและ retrieval ใหม่ทั้งหมด")
table(["Capability family", "สิ่งที่ทำในแอป"], [
    ("1 Structured output", "ตรวจ search arguments และ answer JSON ด้วย Pydantic"),
    ("2 Retrieval / RAG", "Hybrid retrieval พร้อมข้อความอ้างอิงและเลขหน้า"),
    ("3 Evaluation", "Gold set, Recall@5, MRR@10 และ dense baseline"),
    ("4 Agent loop", "Gemma เรียก search_docs และมี stop conditions"),
    ("6 Served interface", "FastAPI REST API และหน้าเว็บภาษาไทย")], [49, 116])
add("ขอบเขตการทำงาน", "h2")
add("โค้ดแอปและสำเนาข้อมูลอยู่ใน D:\\KMITL\\LLMapp\\ncd-gemma แยกจาก repository ต้นทาง ข้อมูลที่มีข้อจำกัดการเผยแพร่อยู่ในโฟลเดอร์ที่ Git ignore ไว้ การเตรียม public deliverable ต้องจัดสิทธิ์ข้อมูลก่อนเผยแพร่")

section(2, "การออกแบบและการทำงานของ agent")
story.append(Architecture())
add("เส้นทางจากคำถามถึงคำตอบ", "h2")
add("เมื่อรับคำถาม ระบบบังคับให้ Gemma เริ่มด้วย search_docs ผ่าน native function calling โค้ดตรวจชื่อ tool และ arguments ก่อนเรียก retrieval ผลค้นถูกส่งกลับเป็น tool message พร้อม tool_call_id ที่ตรงกับ assistant message จากนั้น model เลือกค้นเพิ่มหรือสรุปคำตอบเป็น JSON ได้")
add("Retrieval ใช้ child chunks ขนาด 128 tokens เพื่อค้น dense แล้วคืน parent chunks ขนาด 512 tokens รวมกับ BM25 char3 ด้วย convex fusion ค่า alpha=0.6 และ candidate pool=100 ตาม frozen config เดิม แอปใช้ variant B เป็นค่าเดียวในการตอบ จึงไม่เพิ่มภาระ reranker ของ variant C")
add("การจำกัดและตรวจผล", "h2")
add("กำหนดไม่เกิน 4 model rounds รวมรอบตรวจคำตอบ และ 3 searches ต่อคำถาม จำกัด top_k ที่ 8 และข้อความ context รวม 18,000 ตัวอักษร ปฏิเสธการค้น query/filter ซ้ำ มี request timeout และ deadline ของ agent ก่อนแสดงคำตอบให้ Gemma ตรวจความตรงกับคำถามและหลักฐานอีกหนึ่งรอบ หากตรวจไม่ได้จะงดตอบ Tool ที่อนุญาตมีเพียง search_docs จึงไม่มีเส้นทางเรียก shell หรืออ่านไฟล์ตามคำสั่งจาก model")
add("คำตอบที่สถานะ answered ต้องมี source ID ที่ปรากฏในผลค้นจริง quote ต้องอยู่ในข้อความที่ model ได้รับ และ citation markers ต้องตรงกับรายการอ้างอิง หาก validation ไม่ผ่านให้แก้ได้หนึ่งรอบ ถ้ายังผิดหรือครบ budget จะหยุดโดยแสดงสถานะชัดเจน ทั้งนี้ quote ที่มีอยู่จริงยังไม่รับรองว่าคำตอบทุกประโยคสอดคล้องกับความหมายของหลักฐาน")
add("การเรียกโมเดล", "h2")
add("ใช้ from openai import OpenAI และ OpenAI() อ่าน OPENAI_API_KEY/OPENAI_BASE_URL จาก environment กำหนด model เป็น gemma-4-E4B-it และ temperature=0 เก็บ cache ของ response รวม tool calls โดยผูกกับ endpoint, model, messages และ parameters ไม่มี API key ถูกส่งให้ frontend")

section(3, "ข้อมูลและผล retrieval ที่ทำซ้ำได้")
add("ชุดข้อมูลที่นำมาใช้", "h2")
add("ไฟล์คำถามมี 177 แถว เป็น gold 162 ข้อและ rejected 15 ข้อที่ตัดออก แบ่ง gold เป็น dev 106 และ test 56 ข้อ ชุด test มี answerable 52 และ unanswerable 4 ข้อ การวัด Recall และ MRR ใช้เฉพาะข้อที่ตอบได้ตาม protocol เดิม")
table(["Artifact", "จำนวน / version"], [("Retrieval corpus", "normalized-v12: 66 เอกสารที่มี chunks"),
    ("Child / parent chunks", "23,819 / 4,347"), ("Dense index", "BAAI/bge-m3, vectors 23,819 × 1,024"),
    ("Gold", "dev 106 / test 56; มี reviewer ตาม metadata"),
    ("Integrity", "SHA-256 ของข้อมูลและผลดิบตรงกับ manifests")], [65,100])
add("Baseline และนิยาม metric", "h2")
add("กำหนด A dense parent-child เป็น baseline และเปรียบเทียบ B hybrid ซึ่งแอปนำมาใช้ Strict relevance ต้องตรง edition และช่วงหน้า พร้อมพบ quote อย่างน้อยครึ่งหนึ่ง Recall@k วัดสัดส่วน evidence ที่ top-k ครอบคลุม ส่วน MRR@k วัด reciprocal rank ของผลที่เกี่ยวข้องรายการแรก")
table(["Frozen test", "Recall@5", "MRR@10"], [("A dense baseline","0.8077","0.6181"),
    ("B hybrid","0.8846","0.7374"),("C hybrid + reranker","0.9135","0.7706")], [75,45,45])
add("B เพิ่ม Recall@5 เท่ากับ 0.0769 หรือ 7.69 percentage points และ MRR@10 เท่ากับ 0.1193 เมื่อเทียบ A การคำนวณใหม่จาก saved ranked hits ได้ค่าตรงกับ metrics เดิมทั้ง dev/test ของ A/B/C")
add("ข้อจำกัด: ไม่ได้รัน test retrieval ใหม่เพื่อปรับค่า ผล test ชุดนี้เคยถูกใช้ในโปรเจคเดิมแล้ว และตัวเลขข้างต้นไม่ใช่ความถูกต้องของคำตอบ Gemma หรือ agent ที่เลือก query ใหม่เอง", "small")

section(4, "การประเมินส่วน Gemma ที่เพิ่มใหม่")
add("ล็อกแผนก่อนเรียกโมเดล", "h2")
add("เลือก dev sample 30 ข้อโดยวนตามประเภทคำถาม และเรียงด้วย SHA-256 ของ qid ในแต่ละประเภท ได้ condition, fact, multi_page, number_unit, table และ unanswerable อย่างละ 5 ข้อ เก็บ qids, prompt hash, gold hash, model และ temperature ใน plan ก่อนเริ่มรัน การประเมินนี้เป็น development result ไม่ใช่ held-out test")
if agent:
    table(["Metric", "ผลจริง"], [("จำนวนคำถาม",str(agent["n"])), ("Stop reason completed (รวมงดตอบ)",str(agent["completed_rate"])),
        ("Abstention decision accuracy",str(agent["abstention_decision_accuracy"])),
        ("Citation primary-evidence hit rate",str(agent["citation_primary_evidence_hit_rate_answerable"])),
        ("Mean character F1 (lexical proxy)",str(agent["mean_character_f1_answerable"])),
        ("Status counts",json.dumps(agent["status_counts"],ensure_ascii=False))], [105,60])
else:
    add("ยังไม่มีผล aggregate ของ Gemma evaluation ใน artifacts ที่ใช้สร้าง PDF รอบนี้ จึงยังไม่ใส่ค่าความแม่นยำหรืออ้างว่าผ่านการประเมิน end-to-end ให้รัน evaluate agent แล้วสร้างรายงานใหม่ก่อนใช้เป็นฉบับส่ง")
add("รุ่น " + agent["plan_id"] + ": เก็บผลรุ่นก่อนหน้ารวมรอบที่ล้มเหลวไว้ครบใน reports/history และ private/runs; รายการตรวจทั้ง 30 ข้ออยู่ใน docs/ANSWER_REVIEW_TH.md", "small")
add("การตีความ metric", "h2")
add("Abstention decision accuracy ตรวจว่าระบบตอบหรือเว้นตอบสอดคล้องกับ answerable label หรือไม่ ไม่ใช่คะแนนความถูกต้องของเนื้อหาคำตอบ Citation primary-evidence hit rate ตรวจ source ที่อ้างกับ primary evidence เดิม ส่วน character F1 วัดเพียงสัดส่วนอักษรร่วมกับ reference answer จึงไม่ใช้แทนการตรวจความหมายหรือความถูกต้องทางคลินิก")
add("ไม่มี reference answer ถูกส่งให้ model ระหว่าง serving หรือ evaluation แอปได้รับเฉพาะคำถามและหลักฐานจาก retrieval ส่วน labels ถูกใช้ภายหลังเพื่อคำนวณ metric ผลดิบและ cache อยู่ในโฟลเดอร์ private เพื่อเก็บ trace และกลับมาตรวจ failure ได้")
add("เทียบ v5 → v8: ตอบ 18 → 11 ข้อ, abstention decision accuracy 0.7000 → 0.5333 ระงับคำตอบผิดเดิม q113/q080 และคำตอบไม่ครบ q120 ได้ แต่มี false abstention เพิ่ม จึงไม่อ้างว่า overall accuracy ดีขึ้น ใช้ completions ที่ cache เมื่อ payload ตรงกัน; v8 ไม่เรียก API ใหม่", "small")

section(5, "ผลการทดสอบและ failure analysis")
add("การทดสอบขอบเขตระบบ", "h2")
add("ทดสอบ tool-call round trip, arguments ผิดชนิด/เกินขอบเขต, tool ที่ไม่อนุญาต, query ซ้ำ, tool_call_id ซ้ำ, deadline, proxy errors, prompt injection ในข้อความทดสอบ, quote ที่ model ไม่ได้เห็น และ citation ที่ไม่มีจริง รวมถึง API validation และการตอบเมื่อระบบยังไม่พร้อม")
if validation:
    add(f"ผล automated tests: {validation.get('tests_passed', 'ไม่ระบุ')} ข้อผ่าน ใช้ fake model/retriever เพื่อตรวจ edge cases แยกจากการค้นข้อมูลจริงและ proxy probe ดูขอบเขตใน reports/validation.json")
else:
    add("ยังไม่มี test receipt ใน artifacts ที่ใช้สร้างรายงานนี้ จึงไม่สรุปจำนวน tests ที่ผ่าน ให้รัน pytest และ scripts/record_validation.py ก่อนใช้เป็นฉบับส่ง")
answers_path = ROOT / f"private/runs/{plan['id']}/answers.jsonl"
answers = [json.loads(s) for s in answers_path.read_text(encoding="utf-8").splitlines()] if answers_path.exists() else []
success = next((r for r in answers if r["prediction"]["status"] == "answered"), None)
failure = next((r for r in answers if r["qid"] == "q076"), None)
for title, item in [("ตัวอย่างที่ตอบพร้อมหลักฐานได้",success),("ตัวอย่างข้อจำกัดที่พบจริง",failure)]:
    add(title,"h2")
    if item:
        prediction=item["prediction"]
        add(f"qid {item['qid']} | status {prediction['status']} | stop reason {prediction['stop_reason']}")
        add(item["question"])
        add(prediction["answer"][:500])
        if title.startswith("ตัวอย่างข้อจำกัด"):
            add("Reference: " + str(item["reference_answer"]) + " คำตอบใช้ค่า 150 นาทีจาก guideline ความดัน ขณะที่คำถามเรื่องไขมันและ reference ระบุช่วง 150–300 นาที จึงยังต้องตรวจความตรงบริบท แม้ verifier อนุมัติ", "small")
    else:
        add("ยังไม่มีตัวอย่างประเภทนี้ในไฟล์ผลรันที่ใช้สร้างรายงาน ไม่สร้างตัวอย่างผลสำเร็จหรือความผิดพลาดขึ้นเอง")
add("สิ่งที่ยังต้องตรวจด้วยคน", "h2")
add("ผู้ประเมินต้องตรวจเงื่อนไข ตัวเลข กลุ่มประชากร และคำถามหลายส่วน ใน v8 มี 14 false abstentions และคำตอบ q041/q076 ที่ยังต้องทบทวน ข้อ q113/q080 ถูกระงับ ไม่ได้แปลว่าแก้การอ่านตารางถูกแล้ว การตรวจ quote แยกประเด็นและซ่อมผลตรวจยังใช้ Gemma ตัวเดิม จึงไม่เป็น independent verification")

section(6, "การทำซ้ำ ข้อจำกัด และสิ่งที่ต้องส่ง")
add("วิธีตรวจผลงาน", "h2")
add("ติดตั้ง environment ตาม requirements-runtime.txt หรือ lock ที่บันทึกไว้ ตั้งค่า class proxy ใน .env นำข้อมูลจากแหล่งที่ได้รับสิทธิ์ด้วย scripts/import_source.py แล้วใช้ run.ps1 เพื่อเปิดหน้าเว็บ ใช้ evaluate retrieval เพื่อคำนวณผลจาก frozen ranked hits และ evaluate agent เพื่อรันตาม dev plan ที่ล็อกไว้")
table(["Deliverable", "สถานะที่ต้องตรวจเมื่อส่ง"], [("Q1 Public repository", "ตั้ง origin เป็น Up2mEz/LLM-APP-END2END แล้ว ยังไม่ push; ต้องจัดสิทธิ์ corpus และ public reproducibility ตามขอบเขตที่ตกลง"),
    ("Q2 PDF 4–8 หน้า", "รายงานฉบับนี้มี 6 หน้า ต้องตรวจผล evaluation และข้อมูลผู้จัดทำก่อนส่ง"),
    ("Q3 Demo URL", "มี local app และสคริปต์บรรยาย 3–6 นาที ยังต้องอัดวิดีโอหรือ deploy แล้วใช้ URL ที่ผู้ตรวจเข้าถึงได้")], [55,110])
add("ข้อจำกัดของ corpus และการเผยแพร่", "h2")
add("Handoff ต้นทางระบุว่ามีข้อความที่ใช้ภายในทีม จึงยังไม่เผยแพร่ gold/chunks/index ผ่าน Git การมี local import script ไม่ทำให้ public repo reproduce ได้สำหรับผู้ที่ไม่มีสิทธิ์ข้อมูล หากเปลี่ยน corpus เพื่อเผยแพร่ได้ ต้อง version และประเมินชุดส่งใหม่ ไม่ใช้ metrics ของ v12 อ้างแทน subset")
add("แนวทางพัฒนาต่อ", "h2")
add("ตรวจคำตอบจริงกับผู้มีความรู้ในโดเมน เพิ่ม independent claim-level faithfulness evaluation เพราะ same-model review ยังยอมรับคำตอบผิด และแยกความผิดพลาดตามชนิดคำถาม เตรียมตัวอย่างสำเร็จและ failure สำหรับ live defence พร้อมอธิบายเหตุผลเลือก hybrid และตัวหารของ metric ได้ งานเหล่านี้สำคัญกว่าการเพิ่ม tool หลายชนิดโดยไม่วัดผล")
add("แหล่งอ้างอิง", "h2")
add("Thai NCD Guideline QA: github.com/Chaiporn2005/thai-ncd-guideline-qa; source snapshot และ SHA-256 ใน provenance/source_snapshot.json", "small")
add("Project rubric: courses.nat-d.uk/courses/building-llm-powered-applications/courseworks/20", "small")
add("OpenAI Docs, Function calling: developers.openai.com/api/docs/guides/function-calling", "small")


def page(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#d5dfd1")); canvas.line(22*mm,19*mm,188*mm,19*mm)
    canvas.setFont("Thai",8); canvas.setFillColor(MUTED)
    canvas.drawString(22*mm,13*mm,"NCD Evidence | Building LLM-Powered Applications")
    canvas.drawRightString(188*mm,13*mm,str(doc.page))


doc = SimpleDocTemplate(str(OUT), pagesize=(210*mm,297*mm), rightMargin=22*mm,leftMargin=22*mm,
                        topMargin=20*mm,bottomMargin=25*mm,title="NCD Evidence - Project report",author="Project team")
doc.build(story,onFirstPage=page,onLaterPages=page)
print(OUT)
