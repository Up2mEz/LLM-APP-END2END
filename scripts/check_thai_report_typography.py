"""Render a reproducible mark-positioning specimen (no evaluation changes)."""
from pathlib import Path
import pymupdf
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

OUT=Path(__file__).resolve().parents[1]/'private/report_typography'
OUT.mkdir(parents=True,exist_ok=True)
for name,index in [('Thai',0),('ThaiBold',1)]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/angsana.ttc',subfontIndex=index,shapable=True))
sample='โครงงานนี้ ที่ ผู้ใช้ ชี้ ชั้น ตั้งขึ้น ผู้จัดทำ น้ำ หนึ่ง เครื่องมือ Recall@5 150 นาที'
for mode in ('CJK','LTR'):
    pdf=OUT/(mode+'.pdf');story=[]
    for font,size in [('Thai',16),('ThaiBold',18),('ThaiBold',20)]:
        story.extend([Paragraph(sample,ParagraphStyle(font,fontName=font,fontSize=size,leading=26,wordWrap=mode,shaping=True)),Spacer(1,20)])
    SimpleDocTemplate(str(pdf)).build(story)
    doc=pymupdf.open(pdf);doc[0].get_pixmap(matrix=pymupdf.Matrix(3,3)).save(OUT/(mode+'.png'))
    print(mode,repr(doc[0].get_text()))
