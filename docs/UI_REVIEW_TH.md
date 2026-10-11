# ผลตรวจหน้าเว็บตาม Hallmark

ปรับหน้าเดิมใน static/index.html และ app.js เพิ่ม clinic.css และ tokens.css โดยรักษา style.css และ routes เดิม ใช้ custom clinic blue-white จาก brief ของผู้ใช้ Workbench สำหรับค้นจริง, N1 สองทางเลือก และ footer Ft2

- ฟอนต์ Leelawadee UI สำหรับหัวเรื่อง และ Tahoma สำหรับเนื้อหา เป็นการปรับสำหรับภาษาไทยและการเปิดในเครื่อง ไม่โหลด fonts/scripts ภายนอก
- CSS book mascot, เงาและแสงตามที่ผู้ใช้ขอ; ไม่มี stock image หรือ fake browser chrome
- Motion 3 กลุ่ม: result reveal, button press, loading spinner; reduced motion ทดสอบจริงแล้ว animation เป็น none และคืน override แล้ว
- ตรวจ 320/375/414/768 px: ไม่มี horizontal overflow; ปุ่ม/ลิงก์/summary ที่แสดงมีความสูงอย่างน้อย 44 px ไม่ตัดหรือซ้อนข้อความ
- Desktop 1280×800: ปุ่มค้นหาจบที่ y=740.9 px จึงอยู่ในจอแรก
- ใช้ minmax(0, …) ใน grid, overflow-x:clip ที่ html/body, heading overflow-wrap และ focus-visible
- ทดสอบ dialog และ focus, example, clear, answered q045, insufficient evidence q125, copy, source anchor, source details และอ่านข้อความบริบทด้วย keyboard ได้
- ไม่พบ console errors ในช่วงทดสอบ; ผลตอบจาก UI ใช้ cache จาก evaluation ส่วน retrieval ทำงานจริง
- คู่สีหลักที่อ่านจาก computed styles มี WCAG text contrast ตั้งแต่ 6.10:1 ขึ้นไป; focus บนพื้นขาว/ฟ้าอ่อน 7.76:1 ขึ้นไป ดู reports/ui_contrast.json เป็นการตรวจคู่สีตัวแทน ไม่ใช่ accessibility certification ทั้งเว็บไซต์

ตรวจ slop-test ของ Hallmark ตามส่วนที่ใช้กับแอปจริงแล้ว ไม่มีปัญหา mobile layout/contrast ที่ยังเปิดอยู่ ไม่อ้างตัวเลข 58/58 เนื่องจากกฎบางส่วนเป็นรูปแบบ marketing page และบางส่วนปรับตาม brief ที่ระบุให้มี mascot แสง เงา และใช้ฟอนต์ไทยในเครื่อง

Pre-emit critique: Philosophy 4, Hierarchy 4, Execution 4, Specificity 4, Restraint 4, Variety 4

หลักฐานภาพอยู่ใน output/ui/ (Git ignore เพราะภาพคำตอบอาจมีข้อความ corpus ภายใน) รายงาน browser_layout.json และ ui_contrast.json เก็บเฉพาะข้อมูลการทดสอบ layout/สี

## ตรวจซ้ำกับ backend v8

ทดสอบ success q045 และการระงับคำตอบ q113/q120 ผ่าน UI รุ่นใหม่ แยกข้อความ “ยังยืนยันคำตอบไม่ได้” เมื่อมี evidence แต่คำตอบไม่ผ่านตรวจ พบปุ่มล้างกว้าง 38.31 px จึงแก้ min-width เป็น 44 px และตรวจ 320/375/414/768 px ซ้ำพร้อมคำตอบจริงแล้วผ่านทั้ง overflow และ touch targets ดู reports/browser_layout_v8.json ไม่พบ console errors ในรอบนี้

## ตรวจซ้ำกับ backend v13 วันที่ 12 ตุลาคม 2026

ทดสอบผ่าน browser จริง: คำถามโรคไตแบบกว้างตอบได้พร้อมหลักฐานและถามระยะโรค; q113 แสดงค่าพลังงาน 219 และโปรตีน 5.4 พร้อม label ว่าเป็นตารางจัดรูปจาก PDF; q075 ยังงดตอบแต่แสดงว่าค้นพบเอกสารแล้ว ไม่ทำให้เข้าใจว่าไม่มี corpus

ตรวจ q113 ที่ viewport 375×812: scrollWidth 360 ไม่ล้นแนวนอน ตรวจภาพแล้วข้อความตัดบรรทัดอยู่ใน card คืน viewport เดิมแล้ว ไม่พบ browser console errors ในรอบนี้ ภาพหลักฐานอยู่ output/ui/kidney-v13.png และ output/ui/table-v13-mobile.png (local only) UI ใช้ cached model completions และค้น retrieval จริง
