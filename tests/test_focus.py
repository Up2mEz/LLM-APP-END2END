from ncd_gemma.focus import PassageFocus

def test_focus_selects_relevant_admitted_window_without_changing_parent():
    text='\n'.join(['เรื่องทั่วไปเกี่ยวกับขั้นตอนที่ไม่เกี่ยวข้อง '*8]*10+['กิจกรรมหุ่นยนต์สำหรับเยาวชนใช้ชุดทดลอง A และคู่มือ B']+['รายละเอียดอื่น '*30]*10)
    hit={'chunk_id':'synthetic','document_id':'doc','edition_id':'e1','text':text}
    focus=PassageFocus([hit])
    selected=focus.select(hit,'กิจกรรมหุ่นยนต์สำหรับเยาวชนใช้ชุดทดลองอะไร')
    assert any('ชุดทดลอง A' in p['text'] for p in selected)
    assert all(p['text'] in text and p['chunk_id']=='synthetic' for p in selected)
    assert hit['text']==text and len(selected)<=2

def test_focus_preserves_structured_tables_and_short_passages():
    hit={'chunk_id':'table','text':'หัวตารางและค่าที่ห้ามแยกออกจากกัน '*200,'table_provenance':[{'pdf_page':1}]}
    focus=PassageFocus([hit])
    assert focus.select(hit,'ค่าในตารางคืออะไร')==[hit]
    short={'chunk_id':'short','text':'ประโยคสั้นที่มีบริบทครบ'}
    assert focus.select(short,'คำถาม')==[short]
    html={'chunk_id':'html','text':'เอกสารประกอบ '*150+'<table><tr><th>ปี</th></tr><tr><td>2567</td><td>468 คน</td></tr></table>'}
    assert focus.select(html,'ปี 2567 เข้าร่วมกี่คน') == [html]
