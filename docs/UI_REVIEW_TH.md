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


## ตรวจกับ backend v24 วันที่ 12 ตุลาคม 2026

ส่ง q075 และ q061 ผ่าน form จริง: q075 ตอบพร้อม citation S1 และหน้า PDF 19–21; q061 ยังงดตอบ โดย UI แสดงว่ามีข้อความค้นพบแต่คำตอบยังไม่ผ่าน validation ไม่ตีความว่าไม่มี corpus ไม่พบ console errors ในการตรวจรอบนี้ ใช้ cached model completions และ retrieval จริง ไม่ได้ตรวจ responsive/layout ใหม่ทั้งชุดในรอบนี้ ดู reports/browser_validation_v24.json และภาพ output/ui/q075-v24.png, output/ui/q061-v24.png

## ตรวจ live API กับ backend v25 วันที่ 12 ตุลาคม 2026

หลัง restart server ส่ง `hello` และ q111/q115/q061/q106 ผ่าน HTTP API ในเครื่องจริง `hello` ได้ `out_of_scope` โดยไม่ค้นหรือเรียก proxy ส่วนสี่คำถามได้ `answered` ผ่าน `grounded_route` พร้อม citations และค้นเอกสารอย่างละหนึ่งครั้ง ข้อมูลใน `reports/api_validation_v25.json` เป็น API smoke เท่านั้น ไม่ได้เป็นผลตรวจภาพ UI หรือการสุ่มคำตอบจากโมเดลใหม่ เพราะ native tool call ตรงกับ cache เดิม

เปิดแท็บหน้าเว็บเดิมแล้วพบว่า JavaScript ที่โหลดค้างจากก่อน restart ยังแสดง `hello` ด้วยข้อความทั่วไป หลัง reload หน้าเว็บและส่ง `hello` อีกครั้ง การ์ดแสดง “ยินดีต้อนรับ” และ “เริ่มต้นถามได้เลย” พร้อมข้อความว่าไม่ต้องค้นเอกสารหรือเรียกโมเดล ตรวจทั้ง accessibility tree และภาพบนจอแล้ว ไม่มีการแก้ JavaScript เพิ่มในขั้นตอนนี้ ผู้ใช้ที่เปิดแท็บค้างไว้ต้อง reload เพื่อรับหน้าเวอร์ชันใหม่

## ตรวจ live API กับ backend v26 วันที่ 12 ตุลาคม 2026

หลัง restart server v26 ส่ง `hello` และ q111/q115/q061/q106 เดิมผ่าน localhost อีกครั้ง: `hello` ได้ `out_of_scope` โดยไม่ค้นหรือเรียก proxy; สี่ข้อที่เหลือได้ `answered` ผ่าน `grounded_route` พร้อม citation 2/1/1/1 จุดตามลำดับ ค้นหนึ่งครั้งต่อข้อ และใช้ cached tool call ไม่มี HTTP attempt ใหม่ ดู `reports/api_validation_v26.json` นี่เป็น API smoke ไม่ใช่การตรวจภาพ browser ซ้ำหรือ unseen evaluation
