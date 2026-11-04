import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from '@/components/ui/sheet'

/* Hallmark · component: information sheet · existing paper theme
 * pre-emit critique: P4 H4 E4 S5 R5 V3 */
export function AboutSystem() {
  return <Sheet>
    <SheetTrigger asChild><Button variant="ghost" size="sm">เกี่ยวกับระบบ</Button></SheetTrigger>
    <SheetContent className="overflow-y-auto w-full sm:max-w-xl">
      <SheetHeader><SheetTitle>ระบบค้นคำตอบอย่างไร</SheetTitle><SheetDescription>เครื่องมือทดลองอ่านเอกสาร NCD ภาษาไทย พร้อมหลักฐานให้ตรวจสอบ</SheetDescription></SheetHeader>
      <div className="px-6 pb-8 space-y-6 text-sm leading-7">
        <section><h3 className="font-medium">จากคำถามถึงหลักฐาน</h3><ol className="list-decimal pl-5 space-y-2">
          <li>เว็บ React ส่งคำถามไปยัง FastAPI แต่ละคำถามเริ่มค้นใหม่แยกกัน</li>
          <li>Gemma เรียก search_docs เพื่อค้นด้วยความหมายผ่าน bge-m3 ร่วมกับคำเฉพาะผ่าน BM25</li>
          <li>ระบบจัดอันดับข้อความซ้ำเมื่อเปิด reranker แล้วใช้ข้อความที่ได้ประกอบคำตอบ</li>
          <li>ตรวจรูปแบบคำตอบและข้อความอ้างอิงก่อนแสดงผล ผู้ใช้เปิดต้นทางเพื่อตรวจบริบทได้</li>
        </ol></section>
        <section><h3 className="font-medium">ผลค้นหลักฐานรอบปัจจุบัน</h3><p>การค้นความหมายช่วยเมื่อใช้คำต่างจากเอกสาร ส่วน BM25 ช่วยค้นคำเฉพาะ รอบ capstone-current-v2 รันใหม่บน pipeline ปัจจุบันได้ Recall@5: dense 0.82 และ hybrid 0.90 เพิ่ม 8 จุดเปอร์เซ็นต์ บน 25 ข้อที่ตอบได้ โดยเปิด reranker และปิด cache ทั้งคู่</p><p className="text-muted-foreground">วัดการพบหลักฐานในห้าอันดับแรก แยกจากความถูกต้องของคำตอบ</p></section>
        <section><h3 className="font-medium">ผลประเมินคำตอบ</h3><p>Luna 6 xhigh ตรวจแบบซ่อนชื่อแขน: dense สำเร็จ 23/30 และ hybrid 28/30 รวมการงดตอบถูกต้องและนับข้อผิดพลาดบริการไว้ด้วย พบ HTTP 429 จำนวน 1 และ 2 ข้อตามลำดับ</p><p className="text-muted-foreground">เป็น LLM-as-judge บน dev ที่เคยใช้พัฒนา ไม่ใช่การตรวจโดยผู้เชี่ยวชาญหรือการรับรองทางคลินิก</p></section>
        <section><h3 className="font-medium">เมื่อปิด reranker</h3><p>การทดลองเฉพาะ retrieval ได้ Recall@5 ลดจาก 0.90 เป็น 0.74 เวลาค้นมัธยฐานลดจาก 14.49 เป็น 0.24 วินาทีในเครื่องนี้ ยังไม่รวมเวลาสร้างและตรวจคำตอบ</p></section>
        <section><h3 className="font-medium">สิ่งที่ยังต้องตรวจเอง</h3><p>ข้อความอ้างอิงอาจตรงต้นทาง แต่คำตอบยังอาจเลือกประชากรหรือเงื่อนไขผิด การไม่พบหลักฐานไม่ได้แปลว่าข้อเท็จจริงนั้นไม่มีอยู่ ใช้ระบบเพื่อช่วยอ่านเอกสารและตรวจคำตอบก่อนนำไปใช้</p></section>
      </div>
    </SheetContent>
  </Sheet>
}
