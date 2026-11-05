# สร้างรายงาน PDF

ต้นฉบับที่แก้ไขคือ `docs/PROJECT_REPORT_SUBMISSION_TH.md` คำสั่งสร้างรายงานตรวจว่าตัวเลขหลักตรงกับผลประเมินที่เผยแพร่ก่อนพิมพ์ PDF และไม่เขียนเนื้อหาทับต้นฉบับ

ใช้ Windows ที่มีฟอนต์ Angsana New, Python และ Node.js เตรียมตัวพิมพ์ PDF ในโฟลเดอร์ที่ไม่เข้า Git:

```powershell
npm install --prefix private/report-runtime playwright@1.58.2
node private/report-runtime/node_modules/playwright/cli.js install chromium
.venv312\Scripts\python scripts/build_current_capstone_report.py
```

ได้ไฟล์ `output/pdf/NCD_EVIDENCE_SUBMISSION_67070060.pdf` และ HTML สำหรับตรวจรูปเล่ม ตัวพิมพ์ใช้ Chromium เพื่อจัดตำแหน่งสระและวรรณยุกต์ภาษาไทย โดยคงข้อความให้เลือกและค้นได้ ทุกข้อความรวมถึงตัวอักษรในแผนผังเป็นสีดำ ไม่มีวันที่ปรับปรุงในเนื้อหา

หากติดตั้ง Playwright ไว้ที่อื่น ให้ตั้ง `NCD_REPORT_PLAYWRIGHT_MODULE` เป็นพาธ `playwright/index.mjs` และตั้ง `PLAYWRIGHT_BROWSERS_PATH` ตามตำแหน่ง browser ที่ติดตั้ง ไม่จำเป็นต้องใช้พาธเครื่องของผู้จัดทำ

หลังแก้เนื้อหา ต้องตรวจจำนวนหน้าให้อยู่ในช่วง 4–8 หน้า เปิดดูทุกหน้า ตรวจขอบ ตาราง แผนผัง และคำที่มีสระกับวรรณยุกต์ เช่น “นี้” “ผู้ใช้” และ “ที่” ก่อนคัดลอกไฟล์ที่ตรวจแล้วไปยัง `docs/submission/` การผ่านการดึงข้อความอัตโนมัติอย่างเดียวไม่ยืนยันว่าจัดวางถูกต้อง
