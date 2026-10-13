"""Build a Thai report and matching Markdown from recorded evaluation artifacts.

Require complete artifacts, never a particular score. This report describes
exposed development results, not independent clinical validation.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/NCD_GEMMA_PROJECT_REPORT_TH.pdf"
READING = ROOT / "docs/PROJECT_REPORT_TH.md"
INK, BLUE, MUTED, LINE = map(colors.HexColor, ("#1c2934", "#14547c", "#52616d", "#cbd7df"))


def read(name):
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8"))


def main():
    retrieval = read("retrieval_metrics.json")
    current, audit = read("gemma_dev_metrics.json"), read("semantic_audit.json")
    validation = read("documentation_tests_2026-10-14.json")
    histories = {v: read(f"history/v{v}_gemma_dev_metrics.json") for v in (13, 24, 26, 27)}
    audits = {v: read(f"history/v{v}_semantic_audit.json") for v in (13, 24, 26, 27)}
    extras = {v: read(f"extra_dev_v{v}_semantic_audit.json") for v in (26, 28, 29, 30)}
    if current["plan_id"] != audit["current"] or current["n"] != sum(current["status_counts"].values()):
        raise ValueError("Current answer metrics and audit are inconsistent")
    for value in extras.values():
        if len(value["details"]) != value["n"]:
            raise ValueError("An extra-dev audit is incomplete")
    fonts = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Thai", str(fonts / "tahoma.ttf"), shapable=True))
    pdfmetrics.registerFont(TTFont("ThaiBold", str(fonts / "tahomabd.ttf"), shapable=True))
    pdfmetrics.registerFontFamily("Thai", normal="Thai", bold="ThaiBold")
    base = dict(fontName="Thai", textColor=INK, wordWrap="CJK", shaping=True, alignment=TA_LEFT)
    styles = {
        "body": ParagraphStyle("body", **base, fontSize=10.5, leading=17, spaceAfter=9),
        "title": ParagraphStyle("title", **{**base, "fontName":"ThaiBold", "alignment":TA_CENTER}, fontSize=21, leading=29, spaceAfter=9),
        "subtitle": ParagraphStyle("subtitle", **{**base, "alignment":TA_CENTER}, fontSize=12, leading=20, spaceAfter=10),
        "meta": ParagraphStyle("meta", **{**base, "alignment":TA_CENTER}, fontSize=10.5, leading=17, spaceAfter=5),
        "h1": ParagraphStyle("h1", **{**base, "fontName":"ThaiBold", "textColor":BLUE}, fontSize=15, leading=24, spaceAfter=12, keepWithNext=True),
        "h2": ParagraphStyle("h2", **{**base, "fontName":"ThaiBold"}, fontSize=11.5, leading=19, spaceBefore=8, spaceAfter=6, keepWithNext=True),
        "small": ParagraphStyle("small", **{**base, "textColor":MUTED}, fontSize=9, leading=14, spaceAfter=8),
        "cell": ParagraphStyle("cell", **base, fontSize=9, leading=14),
        "th": ParagraphStyle("th", **{**base, "fontName":"ThaiBold"}, fontSize=9, leading=14),
        "caption": ParagraphStyle("caption", **{**base, "alignment":TA_CENTER, "textColor":MUTED}, fontSize=9, leading=14, spaceAfter=10),
    }
    story, md = [], []

    def para(text, style="body"):
        return Paragraph(escape(str(text)), styles[style])

    def add(text, style="body"):
        story.append(para(text, style))
        prefix = {"title":"# ", "h1":"## ", "h2":"### "}.get(style, "")
        md.append(prefix + text + "\n")

    def section(title):
        story.append(PageBreak())
        add(title, "h1")

    def reference(number, label, detail, url):
        linked = f'{number}. <link href="{escape(url)}" color="#14547c">{escape(label)}</link>. {escape(detail)}'
        story.append(Paragraph(linked, styles["small"]))
        md.append(f"{number}. [{label}]({url}). {detail}\n")

    def table(caption, headers, rows, widths):
        add(caption, "small")
        data = [[para(c, "th") for c in headers]] + [[para(c, "cell") for c in row] for row in rows]
        item = Table(data, colWidths=[w * mm for w in widths], hAlign="LEFT", repeatRows=1)
        item.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef4f8")),
            ("LINEABOVE", (0,0), (-1,0), .7, BLUE), ("LINEBELOW", (0,0), (-1,0), .5, LINE),
            ("LINEBELOW", (0,-1), (-1,-1), .7, BLUE), ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ]))
        story.extend([item, Spacer(1,9)])
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            md.append("| " + " | ".join(str(c) for c in row) + " |")
        md.append("")

    def figure(name, caption, width_mm):
        from PIL import Image as PILImage
        path = ROOT / "docs/diagrams" / f"{name}.png"
        with PILImage.open(path) as im:
            w, h = im.size
        story.append(Image(str(path), width=width_mm*mm, height=width_mm*mm*h/w))
        story.append(para(caption, "caption"))
        md.append(f"![{caption}](diagrams/{name}.svg)\n")

    add("NCD Evidence", "title")
    add("ระบบถามตอบจากหลักฐานในเอกสาร NCD ภาษาไทย", "subtitle")
    add("รายงานโครงงานรายวิชา Building LLM-Powered Applications", "meta")
    add("ผู้จัดทำ นายธนกฤต เสมอหน้า   รหัสนักศึกษา 6707060", "meta")
    add("ผู้สอน ดร. ณัฏฐ์ ดิลกธนากุล", "meta")
    add("14 ตุลาคม 2569", "meta")
    story.append(Spacer(1,12))
    add("บทคัดย่อ", "h2")
    add("โครงงานนี้พัฒนาระบบถามตอบจากเอกสารโรคไม่ติดต่อเรื้อรัง หรือ NCD ภาษาไทย เพื่อช่วยผู้ใช้ค้นคำแนะนำและกลับไปตรวจข้อความอ้างอิงได้สะดวก ระบบนำ corpus และ hybrid retrieval จากโครงงาน Thai NCD Guideline QA มาใช้ต่อ แล้วเพิ่ม Gemma ผ่าน class proxy, native tool calling, agent loop และการตรวจคำตอบกับหลักฐาน หน้าจอแสดงคำตอบพร้อมเอกสาร ฉบับพิมพ์ เลขหน้า และข้อความที่ใช้อ้างอิง")
    add("ผลจาก frozen retrieval test พบว่า hybrid retrieval ให้ Strict Recall@5 เท่ากับ 0.8846 สูงกว่า dense baseline ที่ 0.8077 ส่วน dev ชุดเดิม 30 ข้อมีคำตอบที่ตรวจว่าได้สาระครบเพิ่มจาก 14 เป็น 25 ข้อในกลุ่มที่ตอบได้ 25 ข้อ และงดตอบตรง label อีก 5 ข้อ ชุด extra-dev อีก 30 ข้อเพิ่มจาก 19 เป็น 30 ข้อเมื่อรวมการงดตอบที่ถูกต้อง ผลด้านคำตอบเป็นการตรวจโดย coding agent บนชุดที่เปิดผลแล้วและใช้ปรับระบบ จึงแสดงความก้าวหน้าในการพัฒนา แต่ยังไม่ยืนยันคุณภาพบนคำถามใหม่หรือความถูกต้องทางคลินิก")
    add("1. ปัญหาและวัตถุประสงค์", "h2")
    add("เอกสารแนวทางมีหลายฉบับและมักอธิบายข้อแนะนำผ่านตารางหรือเงื่อนไขเฉพาะกลุ่ม การค้นพบข้อความที่มีคำตรงกันจึงยังไม่เพียงพอ ผู้ใช้ต้องรู้ด้วยว่าคำแนะนำนั้นใช้กับกลุ่มใดและอยู่ในบริบทใด ระบบนี้มุ่งช่วยผู้ใช้ทั่วไปและนักศึกษาที่ต้องการอ่านแนวทาง โดยลดเวลาค้นหาและทำให้ที่มาของคำตอบตรวจสอบได้")
    add("วัตถุประสงค์คือพัฒนาแอปที่ค้นหลักฐานก่อนตอบ เรียก tool ได้ภายในขอบเขตที่กำหนด และประเมินผลเทียบ baseline อย่างทำซ้ำได้ ขอบเขตของระบบคือการอ่านเอกสาร ไม่รวมการวินิจฉัย การสั่งยา หรือการจัดแผนรักษาเฉพาะบุคคล เมื่อข้อมูลไม่พอ ระบบควรงดตอบหรือขอรายละเอียดเพิ่มตามลักษณะคำถาม")

    section("2. สถาปัตยกรรมและการออกแบบระบบ")
    figure("architecture", "ภาพที่ 1 สถาปัตยกรรมของระบบและเส้นทางตอบคำถาม", 149)
    add("ระบบรับคำถามผ่านหน้าเว็บภาษาไทยและ FastAPI จากนั้นใช้ OpenAI SDK เรียกโมเดล gemma-4-E4B-it ที่ https://llm.nat-d.uk/v1 โดยอ่าน OPENAI_API_KEY และ OPENAI_BASE_URL จาก environment คำถามในขอบเขตต้องเริ่มด้วย native search_docs โค้ดตรวจชื่อ tool และ arguments ก่อนค้น และส่งผลกลับพร้อม tool_call_id ที่ตรงกัน คำทักทายล้วนตอบด้วยข้อความระบุขอบเขตโดยไม่เรียกโมเดล")
    add("เมื่อได้หลักฐาน ระบบใช้ source bound reader หากตรวจความสัมพันธ์ในข้อความได้ครบ มิฉะนั้นให้ Gemma เสนอคำตอบและตรวจอีกครั้งกับหลักฐาน ทุกเส้นทางต้องผ่านการตรวจ schema และ citation รวมถึงเงื่อนไขเฉพาะที่เกี่ยวข้อง กล่อง Grounding checks ในภาพรวมทั้งสองเส้นทางไว้ด้วยกัน ส่วน gold ถูกใช้เฉพาะการประเมินผล ไม่มีการอ่าน reference answer ใน serving layer")
    add("Configuration ที่ใช้ประเมินจำกัด 6 model rounds รวมรอบตรวจคำตอบ ค้นได้ไม่เกิน 3 ครั้ง top_k ไม่เกิน 8 และ context ไม่เกิน 18,000 ตัวอักษร กำหนด request timeout 45 วินาทีและเวลารวม 150 วินาที จึงหยุดได้เมื่อคำตอบผ่านเกณฑ์ หลักฐานไม่พอ หรือใช้ budget ครบ โดยไม่เปิดให้โมเดลเรียก shell หรือเลือกอ่านไฟล์ได้เอง", "small")

    section("3. ข้อมูล เทคนิค และส่วนที่พัฒนาเพิ่ม")
    add("3.1 ชุดข้อมูลและการนำงานเดิมมาใช้", "h2")
    add("ใช้ snapshot normalized-v12 จาก Thai NCD Guideline QA โดยคัดลอกข้อมูลและ retrieval modules มาไว้ใน repository ของโครงงานนี้ ไฟล์ต้นทางและ gold ไม่ถูกแก้ไข การนำเข้าบันทึก SHA-256 เพื่อให้ตรวจสอบย้อนกลับได้ Gold มี 162 ข้อจากไฟล์คำถามทั้งหมด 177 แถว ส่วน rejected 15 ข้อไม่นำมาประเมิน")
    table("ตารางที่ 1 ข้อมูลหลักที่ใช้ในระบบ", ["รายการ","รายละเอียด"], [
        ("Corpus","66 เอกสารที่มี chunks ใน snapshot normalized-v12"),
        ("Chunks และ index","Child 23,819 ชิ้น Parent 4,347 ชิ้น และ dense vectors ขนาด 1,024 มิติ"),
        ("Gold","Dev 106 ข้อ และ test 56 ข้อ โดย test ตอบได้ 52 ข้อ"),
        ("ชุดประเมินคำตอบ","Dev ชุดเดิม 30 ข้อ และ extra-dev อีก 30 ข้อที่ไม่ซ้ำกัน")], [45,121])
    add("3.2 เหตุผลของการเลือก retrieval", "h2")
    add("นำ variant B ซึ่งรวม dense search ของ bge-m3 กับ BM25 มาใช้เป็นแกนหลัก Dense search ช่วยค้นความหมาย ส่วน BM25 ช่วยรักษาคำเฉพาะ ชื่อยา และตัวเลข ใช้ child 128 tokens และ parent 512 tokens, BM25 char3 ที่ k1 เท่ากับ 2.18 และ b เท่ากับ 0.86 แล้วปรับคะแนนด้วย min-max ก่อน convex fusion ที่ alpha เท่ากับ 0.6 และ candidate pool 100 ค่าเหล่านี้สืบทอดจาก frozen configuration เดิม ไม่ได้ปรับจากผล test ในงานนี้")
    add("3.3 วิธีลดคำตอบผิดและการงดตอบเกินจำเป็น", "h2")
    add("ส่วนที่เพิ่มคือการต่อข้อความข้างเคียง การเลือก short passage และเรียงด้วย bge-reranker-v2-m3 รวมถึง exact lexical admission เฉพาะคำถามความสัมพันธ์ของ field ที่ตรวจตรงข้อความได้ สำหรับตาราง ใช้ PyMuPDF อ่านตำแหน่งเซลล์และหัวคอลัมน์ แล้วให้ระบบประกอบค่าที่เลือกจากเซลล์จริง แทนการให้โมเดลเขียนตัวเลขใหม่ทั้งหมด")
    add("ด้านคำตอบ ใช้ claim และ passage IDs เพื่อผูกข้อความกับ source ตรวจ quote แบบตรงข้อความ และตรวจความครบของหน่วย ตัวหาร ประชากร และเงื่อนไข คำถามบางกลุ่มมี source bound reader ที่อ่านค่าจากหลักฐานโดยตรง ไม่ใช้ qid หรือเฉลยกำหนดคำตอบ หากเงื่อนไขไม่ครบจะกลับสู่ Gemma และ reviewer การซ่อมรูปแบบกับการซ่อมเนื้อหาแยกกันและใช้ budget เดิม เทคนิคเหล่านี้ลดข้อผิดพลาดที่พบระหว่างพัฒนา แต่กฎยังอาจไม่ครอบคลุมสำนวนใหม่")

    section("4. วิธีประเมินและผลการค้นหลักฐาน")
    add("4.1 แยกการวัด retrieval ออกจากการวัดคำตอบ", "h2")
    add("การประเมิน retrieval ใช้ saved ranked hits ของระบบ A, B และ C เทียบ gold เดิมและคำนวณ metric ใหม่ จึงเป็นการ replay ผลค้นที่ตรึงไว้ ไม่ใช่การรัน retrieval ใหม่ ส่วนการประเมินคำตอบใช้คำถาม dev ที่ล็อกก่อนรัน โดยส่งให้ Gemma เฉพาะคำถามและหลักฐาน แล้วใช้ gold ตรวจผลภายหลัง แผนบันทึก qids, model, parameters และ hashes ของ implementation เพื่อระบุว่าแต่ละผลมาจากระบบรุ่นใด")
    add("4.2 Baseline และผลที่วัดได้", "h2")
    add("กำหนด A dense parent-child เป็น baseline Strict relevance ตรวจความตรงของ edition ช่วงหน้า และ quote ตาม protocol เดิม Recall@5 วัดสัดส่วนหลักฐานอ้างอิงที่พบในห้าอันดับแรก ส่วน MRR@10 วัดอันดับของผลที่เกี่ยวข้องรายการแรก ค่าเฉลี่ยใช้เฉพาะ test ที่ตอบได้ 52 ข้อ")
    rows = [(label,f"{retrieval['runs'][key]['recall@5']:.4f}",f"{retrieval['runs'][key]['mrr@10']:.4f}") for key,label in (
        ("test-A","A dense baseline"),("test-B","B hybrid ที่นำมาใช้"),("test-C","C hybrid และ reranker จากงานเดิม"))]
    table("ตารางที่ 2 ผล frozen retrieval test",["ระบบ","Recall@5","MRR@10"],rows,[100,33,33])
    delta = retrieval["test_B_minus_A"]
    add(f"B เพิ่ม Recall@5 เท่ากับ {delta['recall@5']:.4f} หรือ {delta['recall@5']*100:.2f} percentage points และเพิ่ม MRR@10 เท่ากับ {delta['mrr@10']:.4f} เมื่อเทียบ A ตัวเลขนี้สนับสนุนการเลือก hybrid มากกว่า dense เพียงอย่างเดียว แอปยังเพิ่ม passage reranking ซึ่งไม่ใช่ pipeline C เดิม จึงไม่ใช้คะแนน C อ้างเป็นผลของแอปหรือเป็นความถูกต้องของคำตอบ", "small")
    add("4.3 ความครบถ้วนตามขอบเขตโครงงาน", "h2")
    table("ตารางที่ 3 ความเชื่อมโยงกับ capability families ของโจทย์",["Family","หลักฐานในโครงงาน"],[
        ("1 Structured output","Pydantic schemas และ bounded format repair"),
        ("2 Retrieval และ RAG","Hybrid retrieval พร้อม source IDs และ citations"),
        ("3 Retrieval evaluation","Gold, dense baseline และ Recall กับ MRR"),
        ("4 Agent loop","Native search_docs และ stop conditions"),
        ("6 Served interface","FastAPI และหน้าเว็บภาษาไทย")],[55,111])

    section("5. ผลการประเมินคำตอบและการวิเคราะห์")
    add("5.1 Dev ชุดเดิม 30 ข้อ", "h2")
    add("ชุดเดิมประกอบด้วยคำถาม condition, fact, multi_page, number_unit, table และ unanswerable อย่างละ 5 ข้อ มีข้อที่ตอบได้ 25 ข้อและควรงดตอบ 5 ข้อ การตรวจสาระทำโดย coding agent เทียบคำตอบกับ gold และหลักฐาน ไม่ใช่ผู้เชี่ยวชาญอิสระ")
    def counts(a):
        if "core_correct_answerable" in a:
            return a["core_correct_answerable"], len(a["partial_answerable"])+len(a["wrong_answerable"]), len(a["false_abstentions"])
        return len(a["core_matches"]), len(a["incorrect_or_incomplete"])+len(a.get("partial_or_needs_context_review",[])), len(a["false_abstentions"])
    versions = [(str(v),audits[v],histories[v]) for v in (13,24,26,27)]+[("30",audit,current)]
    rows = [("v"+v,*counts(a),f"{m['citation_primary_evidence_hit_rate_answerable']:.4f}",f"{m['mean_character_f1_answerable']:.4f}") for v,a,m in versions]
    table("ตารางที่ 4 ผลคำตอบในกลุ่ม answerable 25 ข้อ",["รุ่น","สาระครบ","ผิดหรือไม่ครบ","งดเกิน","Citation hit","Char. F1"],rows,[19,25,32,22,34,34])
    gain = len(audit["core_matches"])-len(audits[13]["core_matches"])
    add(f"v30 มีคำตอบที่ตรวจว่าได้สาระครบ {len(audit['core_matches'])}/25 ข้อ เพิ่มจาก v13 จำนวน {gain} ข้อ และงดตอบตรง label อีก 5 ข้อ Abstention decision accuracy เท่ากับ {current['abstention_decision_accuracy']:.4f} อย่างไรก็ตาม metric นี้วัดเพียงการเลือกตอบหรืองด ส่วน Citation hit {current['citation_primary_evidence_hit_rate_answerable']:.4f} ตรวจ primary evidence ของ gold และ Character F1 {current['mean_character_f1_answerable']:.4f} วัดข้อความที่ทับซ้อน ไม่ใช่ความถูกต้องทางคลินิก")
    add("5.2 Extra-dev อีก 30 ข้อ", "h2")
    extra_rows = []
    for v,a in extras.items():
        c = a["verdict_counts"]
        extra_rows.append((f"v{v}",f"{a['strict_correct']}/30",c.get("correct",0),c.get("correct_abstention",0),c.get("false_abstention",0),a["n"]-a["strict_correct"]-c.get("false_abstention",0)))
    table("ตารางที่ 5 ผล extra-dev รวมการงดตอบที่ถูกต้อง",["รุ่น","ถูกทั้งหมด","ตอบถูก","งดถูก","งดเกิน","ผิดอื่น"],extra_rows,[20,34,28,28,28,28])
    add("v26 เป็นรอบแรกของชุดเพิ่มเติมและได้ 19/30 ข้อ หลังเปิดผลแล้วจึงแก้การอ่านตาราง เงื่อนไขและความครบถ้วนจน v29 ได้ 30/30 ข้อ ส่วน v30 เพิ่ม guard คำถามปฏิเสธและ replay แล้วได้คำตอบ สถานะและ citation ตรงกับ v29 ทั้งสองชุด โดยไม่มี API calls ใหม่ คะแนนหลังปรับจึงเป็น exposed regression ไม่ใช่ unseen test และไม่มี ablation ที่แยกผลของแต่ละเทคนิคออกจากกัน", "small")

    section("6. กรณีผิดพลาดและการตรวจระบบ")
    add("6.1 สิ่งที่พบจากคำตอบจริง", "h2")
    table("ตารางที่ 6 ตัวอย่างข้อผิดพลาดระหว่างพัฒนา",["กรณี","สาเหตุและการแก้ไข","ผลที่ตรวจได้"],[
        ("q076 ใน v13","คำตอบใช้ค่า 150 นาทีจากบริบทใกล้เคียง แทนช่วง 150 ถึง 300 นาทีที่ถาม จึงเพิ่มการรักษาหน่วย ช่วงค่า และบริบทใน claim","v30 ผ่านการตรวจสาระใน dev เดิม"),
        ("q108 ใน v27","คำตอบอธิบายโซเดียมไม่ครบด้านอาหารกระป๋อง จึงผูก reader กับข้อความที่มีทั้งบริบทการเติมเกลือและ MSG","แก้กลับใน v28 และคงผลถึง v30"),
        ("q006, q107, q110 ใน extra-dev v28","พบหลักฐานแล้วแต่ยังงดตอบ จึงเพิ่ม reader สำหรับความสัมพันธ์และแถวตารางที่ตรวจได้ตรง พร้อม guard ประชากรและคำปฏิเสธ","v29 ตอบได้ครบทั้งสามข้อ และ v30 ให้ผลเดิม")],[37,86,43])
    add("กรณีเหล่านี้แสดงว่า quote ที่มีอยู่จริงอาจไม่สนับสนุนทุกประเด็นในคำตอบ และ reviewer ที่ใช้โมเดลเดียวกับผู้ตอบอาจยอมรับข้อผิดพลาดร่วมกัน การตรวจ primary citation ต่ำกว่า 1.0 ยังต้องทบทวนว่ามาจากหลักฐานทางเลือกที่ถูกต้องหรือจากช่องว่างการอ้างอิง ไม่ควรตีความว่าคำตอบทั้งหมดได้รับการพิสูจน์แล้ว")
    add("6.2 ผลทดสอบซอฟต์แวร์", "h2")
    add(f"ตรวจซ้ำวันที่ 14 ตุลาคม 2569 ผ่าน {validation['tests_passed']} tests ไม่มี failure, error หรือ skipped และมี Starlette deprecation warning หนึ่งรายการ ครอบคลุม tool protocol, argument validation, schema, citation, timeout, proxy retry, scope guard, การอ่านตาราง, API และ public data round trip รอบใน sandbox ค้างที่ Windows socketpair ของ TestClient จึงยืนยันผลด้วยการรันนอก sandbox โดยไม่แก้โค้ดระบบ")
    add("Unit และ API tests ใช้ fake model และ retriever การผ่าน tests จึงยืนยันพฤติกรรมของโค้ดตามกรณีที่กำหนด ไม่ยืนยันว่า Gemma ตอบถูกทุกครั้ง การตรวจ retrieval จริงและ class proxy จริงบันทึกแยกจากผลเหล่านี้ หลังผล v30 มีการเพิ่ม connection retry และการตั้งค่าสำหรับ deployment ซึ่งผ่าน tests แล้ว แต่ยังไม่ได้ประเมินคำตอบทั้งชุดใหม่ด้วย implementation ที่เปลี่ยน")
    add("6.3 ข้อจำกัดของหลักฐานการประเมิน", "h2")
    add("ทั้งสองชุดคำตอบถูกใช้ปรับระบบแล้ว การคัด quote และ source bound reader ช่วยลดการแต่งเนื้อหาแต่ยังจำกัดตามรูปแบบภาษาที่รองรับ Corpus อาจไม่ครอบคลุมแนวทางทุกฉบับหรือข้อมูลปัจจุบัน ระบบยังต้องทดสอบคำถามใหม่และให้ผู้เชี่ยวชาญอ่านคำตอบก่อนนำผลไปกล่าวอ้างด้านคลินิก นอกจากนี้ test ของ retrieval เป็น snapshot จากงานเดิมซึ่งทีมเคยเห็นผลแล้ว")

    section("7. การทำซ้ำ ข้อสรุป และแนวทางพัฒนา")
    add("7.1 สิ่งที่ผู้ตรวจสามารถทำซ้ำได้", "h2")
    add("Public repository มีโค้ด คำสั่งติดตั้ง evaluation scripts และผล aggregate ชุด data-v12 release มีข้อมูลที่ extract แล้ว index, gold, frozen ranked hits และ table context รวม 34 ไฟล์ สคริปต์ public_data.py fetch ตรวจ SHA-256 ก่อนใช้งาน จึงไม่ต้องเข้าถึง source repository ในเครื่องของผู้จัดทำ ผู้จัดทำยืนยันสิทธิ์เผยแพร่ข้อมูล ส่วนเอกสารขอบเขตการอนุญาตไม่ได้แนบใน repository")
    add("ผู้ตรวจสร้าง Python environment ตาม README ดาวน์โหลด release และ model revisions ที่ตรึงไว้ แล้วตั้ง class proxy key ใน .env การเรียก evaluate retrieval คำนวณจาก frozen hits ได้ ส่วน evaluate agent ต้องผ่าน hash guard ของแผนก่อน ขณะนี้ llm.py และ config.py เปลี่ยนหลังแผน v30 จึงต้องสร้าง evaluation version ใหม่ก่อนรันคำตอบ ไม่ลบแผนเพื่ออ้างเป็นผลเดิม ผลคำตอบดิบและ cache ไม่อยู่ใน public repo การรันใหม่ต้องมี key และอ่านจำนวน API calls ประกอบ")
    add("วันที่ 12 ตุลาคม 2569 ตรวจ clean clone พร้อมดาวน์โหลด release และ replay retrieval ครบ 6 runs แล้ว มี FastAPI และหน้าเว็บใช้งานในเครื่อง รวมทั้ง temporary HTTPS demo ผ่าน Cloudflare Quick Tunnel ซึ่งต้องเปิดเครื่องและ tunnel ค้างไว้ URL เปลี่ยนได้เมื่อเริ่มใหม่ ส่วน Dockerfile มีให้แต่ยังไม่ยืนยันการรันทั้งระบบบน Linux host")
    add("7.2 ข้อสรุปและงานต่อไป", "h2")
    add("โครงงานต่อยอด retrieval เดิมให้เป็นแอปที่รับคำถาม ค้นหลักฐาน ตรวจและแสดงคำตอบได้ครบเส้นทาง ผลพัฒนาดีขึ้นทั้งการใช้หลักฐานและการลดการงดตอบในกรณีที่ทดสอบ งานต่อไปควรล็อก implementation แล้วประเมินชุดใหม่ที่ไม่ใช้ปรับระบบ จัด blind review โดยผู้เชี่ยวชาญ แยก ablation ของ reader กับ reranker และวัด latency กับค่าใช้จ่ายจาก fresh requests เพื่อประเมินประโยชน์ของแต่ละส่วนอย่างเป็นธรรม")
    add("เอกสารอ้างอิงและที่มาของงาน", "h2")
    reference(1,"Thai NCD Guideline QA","Corpus, gold และ frozen retrieval snapshot. GitHub: Chaiporn2005/thai-ncd-guideline-qa. Source commit ที่ตรวจ: 3fb287c; รายละเอียด hashes อยู่ใน provenance/source_snapshot.json","https://github.com/Chaiporn2005/thai-ncd-guideline-qa")
    reference(2,"NCD Evidence","โค้ดและผลการทดลองของโครงงานนี้. GitHub: Up2mEz/LLM-APP-END2END. ผลตัวเลขอยู่ใน reports และรายละเอียดรายข้ออยู่ใน docs/DEV_COMPARISON_TH.md","https://github.com/Up2mEz/LLM-APP-END2END")
    reference(3,"Building LLM-Powered Applications","Project specification, coursework 20. courses.nat-d.uk. ใช้ข้อกำหนดที่บันทึกเมื่อ 11 ตุลาคม 2569","https://courses.nat-d.uk/courses/building-llm-powered-applications/courseworks/20")

    def page_frame(canvas, doc):
        canvas.saveState()
        w,h = A4
        if doc.page > 1:
            canvas.setFont("Thai",8); canvas.setFillColor(MUTED)
            canvas.drawString(22*mm,h-15*mm,"NCD Evidence")
            canvas.drawRightString(w-22*mm,h-15*mm,"Building LLM-Powered Applications")
            canvas.setStrokeColor(LINE); canvas.line(22*mm,h-18*mm,w-22*mm,h-18*mm)
        canvas.setStrokeColor(LINE); canvas.line(22*mm,17*mm,w-22*mm,17*mm)
        canvas.setFont("Thai",8); canvas.setFillColor(MUTED)
        canvas.drawCentredString(w/2,11*mm,str(doc.page)); canvas.restoreState()

    OUT.parent.mkdir(parents=True,exist_ok=True)
    document = SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=22*mm,leftMargin=22*mm,topMargin=24*mm,bottomMargin=23*mm,
        title="NCD Evidence: ระบบถามตอบจากหลักฐานในเอกสาร NCD ภาษาไทย", author="นายธนกฤต เสมอหน้า",
        subject="Building LLM-Powered Applications project report")
    document.build(story,onFirstPage=page_frame,onLaterPages=page_frame)
    READING.write_text("\n".join(md).rstrip()+"\n",encoding="utf-8")
    print(OUT); print(READING)


if __name__ == "__main__":
    main()
