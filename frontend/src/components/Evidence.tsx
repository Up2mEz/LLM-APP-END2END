import { useEffect, useRef } from 'react'
import { FileText, Quote } from 'lucide-react'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import type { Answer } from '@/lib/api'

export function Highlight({ content, quotes }: {content: string; quotes: string[]}) {
  const positions: number[] = []; let compact = ''
  for (let i=0; i<content.length; i++) if (!/\s/.test(content[i])) { compact += content[i]; positions.push(i) }
  const ranges: number[][] = []
  for (const quote of quotes) {
    const needle=quote.replace(/\s/g,''); if (!needle) continue
    let from=0, at: number
    while ((at=compact.indexOf(needle,from))!==-1) { ranges.push([positions[at],positions[at+needle.length-1]+1]); from=at+needle.length }
  }
  ranges.sort((a,b)=>a[0]-b[0]); const merged: number[][]=[]
  for (const range of ranges) { const last=merged.at(-1); if(last && range[0]<=last[1]) last[1]=Math.max(last[1],range[1]); else merged.push([...range]) }
  let cursor=0; const parts: React.ReactNode[]=[]
  merged.forEach(([start,end],i)=>{parts.push(content.slice(cursor,start),<mark key={i}>{content.slice(start,end)}</mark>);cursor=end})
  parts.push(content.slice(cursor)); return <>{parts}</>
}

export function Evidence({answer, sourceId, onSource, onClose}: {answer: Answer | null; sourceId: string; onSource:(id:string)=>void; onClose:()=>void}) {
  const body=useRef<HTMLDivElement>(null)
  const source=answer?.sources.find(s=>s.source_id===sourceId) ?? answer?.sources[0]
  const citations=answer?.citations.filter(c=>c.source_id===source?.source_id) ?? []
  useEffect(()=>{body.current?.scrollTo(0,0)},[sourceId,answer])
  return <Sheet open={!!answer} onOpenChange={open=>{if(!open)onClose()}}>
    <SheetContent className="evidence-sheet" onCloseAutoFocus={e=>{e.preventDefault(); document.querySelector<HTMLElement>('[data-evidence-return="true"]')?.focus()}}>
      <SheetHeader><SheetTitle><FileText size={18} aria-hidden="true"/> อ่านหลักฐาน</SheetTitle><SheetDescription>ข้อความที่ค้นมาให้โมเดลอ่าน ไม่ใช่ทุกส่วนจะถูกใช้ตอบ</SheetDescription></SheetHeader>
      <div className="evidence-body" ref={body}>
      {source ? <>
        <label className="field-label" htmlFor="source-select">ข้อความที่ค้นพบ ({answer?.sources.length})</label>
        <select id="source-select" value={source.source_id} onChange={e=>onSource(e.target.value)} className="source-select">{answer?.sources.map(s=><option key={s.source_id} value={s.source_id}>{s.source_id} · {s.header_text || s.document_id || 'เอกสาร'}{answer.citations.some(c=>c.source_id===s.source_id)?' · อ้างอิงในคำตอบ':''}</option>)}</select>
        <div className="source-meta"><span className="source-id">{source.source_id}</span><span>{citations.length?'อ้างอิงในคำตอบ':'ค้นมาแล้ว · ไม่ได้อ้างอิง'}</span></div>
        <h3>{source.header_text || source.document_id || 'เอกสารต้นทาง'}</h3>
        <p className="page-location">หน้า PDF {source.pdf_page_start ?? '—'}{source.pdf_page_end!==source.pdf_page_start?`–${source.pdf_page_end ?? '—'}`:''}</p>
        <p className="highlight-key"><span aria-hidden="true"/> สีเหลืองคือข้อความที่คำตอบอ้างอิง</p>
        <div className="source-text" tabIndex={0} aria-label={`ข้อความต้นทาง ${source.source_id}`}><Highlight content={source.text} quotes={citations.map(c=>c.quote)}/></div>
        {source.text_truncated && <p className="fineprint">ข้อความส่วนนี้ถูกตัดตามขอบเขตบริบทที่ส่งให้โมเดล</p>}
        {citations.map((c,i)=><details className="quote-detail" key={i}><summary><Quote size={14} aria-hidden="true"/> ข้อความอ้างอิง{c.quote_format==='structured_pdf_cells'?'จากเซลล์ตาราง':''}</summary><blockquote>{c.quote}</blockquote></details>)}
        <details className="metadata"><summary>ข้อมูลเอกสารและคำค้น</summary><dl><dt>Document</dt><dd>{source.document_id || '—'}</dd><dt>Edition</dt><dd>{source.edition_id || '—'}</dd><dt>Section</dt><dd>{Array.isArray(source.section_path)?source.section_path.join(' › '):source.section_path || '—'}</dd></dl>{answer?.trace.filter(t=>t.event==='search_docs' && t.sources?.includes(source.source_id)).map((t,i)=><p key={i}>ค้นด้วย: {t.query}</p>)}</details>
      </> : <p>ยังไม่มีข้อความจากเอกสารในคำตอบนี้</p>}
      </div>
    </SheetContent>
  </Sheet>
}
