# แผนภาพ NCD Evidence

แผนภาพจัดทำด้วยสกิล Diagram Design โดยใช้โทนฟ้าขาวจาก `tokens.css` ของแอป ตัวหนังสือใช้ system font และไม่มีการโหลด font หรือ script จากภายนอก ไฟล์ HTML เป็นต้นฉบับแก้ไขได้ ส่วน SVG ใช้แสดงใน GitHub และ PNG ใช้ในรายงาน PDF

| ไฟล์ | เนื้อหา |
|---|---|
| [architecture.html](architecture.html) | สถาปัตยกรรมและเส้นทางตอบคำถาม |
| [evaluation.html](evaluation.html) | แยกการวัด retrieval ออกจากการวัดคำตอบ |

ใช้รูปแบบ Architecture ขนาด fit สำหรับผู้อ่านที่มีพื้นฐานด้านระบบ แผนภาพเดิมใน README มี 14 nodes และ 16 edges จึงแยกส่วนประเมินผลออกเป็นอีกภาพ ภาพหลักเหลือ 7 nodes และ 8 edges โดยรวม FastAPI, agent และ tool argument validation ไว้ในกล่องเดียว รวม dense search, BM25 และการเตรียมหลักฐานไว้ในกล่อง retrieval และรวม source bound readers กับเส้นทาง Gemma review ไว้ในกล่อง grounding checks

รายละเอียดจำนวนรอบ การซ่อมคำตอบและ retry อธิบายใน README และรายงานแทนการเพิ่มเส้นในภาพ ไม่มีการตัดความสัมพันธ์ระหว่าง agent, class proxy และ retrieval ออก Gold อยู่เฉพาะภาพการประเมินผล

สีหลักคือพื้นขาว `#ffffff` ตัวอักษร `#18364e` ข้อความรอง `#52697e` เส้น `#b7c9d8` และจุดเน้น `#0964aa` แต่ละภาพเน้นไม่เกินสองกล่อง เส้นเชื่อมใช้มุมฉาก ตัวหนังสือกับสีไม่ใช่วิธีเดียวที่ใช้แยกหน้าที่

การตรวจงานครอบคลุมโครงสร้าง SVG ที่รองรับ accessibility การแสดงผลจาก browser และการอ่านแผนภาพเมื่อวางใน PDF

ปรับคำอธิบายภาพ evaluation วันที่ 20 ตุลาคม 2569 ให้แยก v30 ที่ใช้ cached responses ออกจากรอบใหม่ที่ใช้ isolated cache โดยคงองค์ประกอบและสีเดิม ผลลัพธ์และ outage แสดงในตารางรายงานแทนการเพิ่ม nodes
