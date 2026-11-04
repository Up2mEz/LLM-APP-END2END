import { useEffect, useRef, useState } from 'react'
import { ArrowUp, ArrowUpRight, BookOpen, Check, ChevronDown, Copy, FileText, LoaderCircle, Plus, SlidersHorizontal, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Switch } from '@/components/ui/switch'
import { Evidence } from '@/components/Evidence'
import { AboutSystem } from '@/components/AboutSystem'
import { ask, type Answer } from '@/lib/api'

const examples = [
  ['จัดจานอาหาร','ผู้เป็นเบาหวานควรจัดสัดส่วนอาหารในจานอย่างไร'],
  ['เป้าหมาย HbA1c','เป้าหมาย HbA1c ในผู้ป่วยเบาหวานคือเท่าไร'],
  ['การออกกำลังกาย','ผู้ใหญ่ควรออกกำลังกายแบบแอโรบิกระดับปานกลางกี่นาทีต่อสัปดาห์'],
  ['ลดโซเดียม','การลดเค็มช่วยควบคุมความดันอย่างไร'],
  ['โปรตีนวัยรุ่น','ตามตารางสารอาหารอ้างอิง พ.ศ. 2546 ผู้หญิงอายุ 13–15 ปีควรได้รับโปรตีนกี่กรัมต่อวัน'],
  ['ACEIs และ ARBs','แนวทางแนะนำให้ใช้ ACEIs ร่วมกับ ARBs หรือไม่ และมีระดับคำแนะนำกับหลักฐานเท่าไร'],
  ['ช่วง BMI','ในตารางประเมินโภชนาการผู้ป่วย nephrotic syndrome ช่วง BMI ของ Overweight คือเท่าไรและมีหน่วยอะไร'],
  ['แหล่งโซเดียม','อาหารกระป๋องและผงชูรสเกี่ยวข้องกับการได้รับโซเดียมอย่างไร'],
  ['อ่านฉลาก','ฉลากโภชนาการระบุปริมาณโซเดียมต่อหนึ่งหน่วยบริโภคอย่างไร'],
]
type Turn = {id: string; question: string; data: Answer; reranker: boolean}
const title = (a: Answer) => a.status==='answered'?'คำตอบจากเอกสาร':a.status==='out_of_scope'?'คำตอบ':a.status==='error'?'บริการขัดข้อง':'ยังยืนยันคำตอบไม่ได้'

function AnswerText({turn, open}: {turn:Turn; open:(turn:Turn,id:string,el:HTMLElement)=>void}) {
  const parts = turn.data.answer.split(/(\[S\d+(?:\s*[,;]\s*S\d+)*\])/g)
  return <div className="answer-text">{parts.map((part,i)=>{
    if (!/^\[S\d/.test(part)) return part
    const ids=part.match(/S\d+/g) ?? []
    if (!ids.every(id=>turn.data.sources.some(s=>s.source_id===id) && turn.data.citations.some(c=>c.source_id===id))) return part
    return <span className="citation-group" key={i}>{ids.map(id=><button key={id} className="citation" aria-label={`อ่านหลักฐาน ${id}`} onClick={e=>open(turn,id,e.currentTarget)}>{id}<ArrowUpRight size={10} aria-hidden="true"/></button>)}</span>
  })}</div>
}

function ResponseTurn({turn, open}: {turn:Turn; open:(turn:Turn,id:string,el:HTMLElement)=>void}) {
  const [copy,setCopy]=useState('')
  const a=turn.data
  const copyAnswer=async()=>{
    try { await navigator.clipboard.writeText(`${turn.question}\n\n${a.answer}`+a.citations.map(c=>`\n\n[${c.source_id}] ${c.document_id} · หน้า PDF ${c.pdf_page_start}–${c.pdf_page_end}\n${c.quote}`).join(''));setCopy('คัดลอกแล้ว') }
    catch {setCopy('คัดลอกไม่ได้ กรุณาเลือกข้อความแล้วคัดลอกด้วยตนเอง')}
  }
  return <article className="turn">
    <div className="user-question"><span className="sr-only">คำถาม: </span>{turn.question}</div>
    <div className="answer-label"><BookOpen size={17} aria-hidden="true"/><h2>{title(a)}</h2>{a.status==='answered' && <span className="answer-check"><Check size={13} aria-hidden="true"/> มีหลักฐานอ้างอิง</span>}</div>
    <AnswerText turn={turn} open={open}/>
    {a.sources.length>0 && <button className="sources-entry" onClick={e=>open(turn,a.citations[0]?.source_id || a.sources[0].source_id,e.currentTarget)}><span className="sources-icon"><FileText size={17} aria-hidden="true"/></span><span><strong>{a.citations.length?'อ่านหลักฐานประกอบ':'ดูข้อความที่ค้นพบ'}</strong><small>{a.sources.length} ส่วนข้อความ · {new Set(a.sources.map(s=>s.document_id)).size} เอกสาร</small></span><ArrowUpRight size={17} aria-hidden="true"/></button>}
    <div className="answer-actions"><Button variant="ghost" size="sm" onClick={copyAnswer} aria-label="คัดลอกคำตอบพร้อมอ้างอิง">{copy==='คัดลอกแล้ว'?<Check/>:<Copy/>}<span>คัดลอก</span></Button><span className="fineprint">{a.stats.searches>0?`ค้น ${a.stats.searches} ครั้ง · ${(a.stats.elapsed_ms/1000).toFixed(1)} วินาที`:'ไม่ค้นเอกสาร'}</span></div>
    {copy && <p className="fineprint" role="status">{copy}</p>}
    <details className="run-details"><summary>รายละเอียดการค้นหา <ChevronDown size={13} aria-hidden="true"/></summary><div className="run-settings">Reranker {a.runtime_options?.use_reranker ?? turn.reranker ? 'ON':'OFF'} · Local cache {a.runtime_options?.use_cache ? 'ON':'OFF'} · API calls {a.stats.api_calls ?? '—'}</div><ol>{a.trace.map((t,i)=><li key={i}>{t.event==='search_docs'?`ค้น: ${t.query} → ${t.sources?.join(', ') || 'ไม่พบข้อความ'}`:t.event==='model'?`Model รอบ ${t.round ?? '—'}${t.cached?' · cache':''}`:`${t.event}${t.reason || t.category ? ` · ${t.reason || t.category}`:''}`}</li>)}</ol><p>Stop reason: {a.stop_reason}</p></details>
  </article>
}

export default function App() {
  const [question,setQuestion]=useState(''),[reranker,setReranker]=useState(true),[settingsOpen,setSettingsOpen]=useState(false)
  const [turns,setTurns]=useState<Turn[]>([]),[busy,setBusy]=useState(false),[pending,setPending]=useState(''),[elapsed,setElapsed]=useState(0)
  const [error,setError]=useState(''),[invalid,setInvalid]=useState(false),[more,setMore]=useState(false),[health,setHealth]=useState('กำลังเชื่อมต่อ')
  const [selected,setSelected]=useState<{turn:Turn;id:string}|null>(null)
  const input=useRef<HTMLTextAreaElement>(null), pendingEl=useRef<HTMLDivElement>(null), abort=useRef<AbortController|null>(null), sending=useRef(false)
  const refreshHealth=()=>fetch('/api/health').then(r=>{if(!r.ok)throw Error();return r.json()}).then(h=>setHealth(h.proxy_configured && h.data_present?(h.retrieval_loaded?'พร้อมค้นหา':'รอโหลดระบบ'):'ต้องตั้งค่าระบบ')).catch(()=>setHealth('ยังเชื่อมต่อไม่ได้'))
  useEffect(()=>{refreshHealth();return()=>abort.current?.abort()},[])
  useEffect(()=>{if(busy)pendingEl.current?.scrollIntoView({block:'nearest',behavior:'instant'})},[busy])
  useEffect(()=>{if(turns.length)document.querySelector('.turn:last-of-type')?.scrollIntoView({block:'start',behavior:'instant'})},[turns.length])
  const openEvidence=(turn:Turn,id:string,el:HTMLElement)=>{
    document.querySelectorAll('[data-evidence-return]').forEach(e=>e.removeAttribute('data-evidence-return'))
    el.dataset.evidenceReturn='true';setSelected({turn,id})
  }
  const submit=async(e?:React.FormEvent)=>{
    e?.preventDefault();if(sending.current)return
    const q=question.trim();if(!q){setError('เขียนคำถามก่อนเริ่มค้นหา');setInvalid(true);input.current?.focus();return}
    sending.current=true;setBusy(true);setPending(q);setError('');setInvalid(false);setSettingsOpen(false);setElapsed(0)
    const controller=new AbortController();abort.current=controller
    const started=Date.now(), timer=window.setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000)
    const timeout=window.setTimeout(()=>controller.abort(),240000)
    try {
      const data=await ask(q,reranker,controller.signal)
      setTurns(old=>[...old,{id:crypto.randomUUID(),question:q,data,reranker}]);setQuestion('')
    } catch(err) {
      setError(err instanceof Error && err.name==='AbortError'?'รอนานกว่าปกติ ระบบอาจยังประมวลผลอยู่ กรุณารอสักครู่แล้วลองใหม่':err instanceof TypeError?'เชื่อมต่อระบบไม่สำเร็จ ตรวจการเชื่อมต่อแล้วลองใหม่':err instanceof Error?err.message:'ส่งคำถามไม่สำเร็จ กรุณาลองใหม่')
    } finally {window.clearInterval(timer);window.clearTimeout(timeout);sending.current=false;setBusy(false);setPending('');refreshHealth()}
  }
  const hasConversation=turns.length>0 || busy
  return <>
    <a href="#question" className="skip-link">ไปยังช่องคำถาม</a>
    <header className="app-header"><a className="wordmark" href="/" aria-label="NCD Evidence หน้าแรก"><BookOpen size={21} strokeWidth={1.7} aria-hidden="true"/><span>NCD <b>Evidence</b></span></a><div className="header-actions"><span className="health"><span className={health==='พร้อมค้นหา'?'ready':''}/>{health}</span>{turns.length>0 && <Button variant="ghost" disabled={busy} onClick={()=>{setTurns([]);setSelected(null);setError('');input.current?.focus()}}><Plus size={16}/>เริ่มใหม่</Button>}</div></header>
    <main className={hasConversation?'main conversation':'main welcome'}>
      {!hasConversation && <section className="welcome-heading"><span className="welcome-kicker">อ่านแนวทางสุขภาพ ด้วยหลักฐานที่ตรวจสอบได้</span><h1>อยากรู้เรื่องไหน<br/><span>เริ่มจากคำถามของคุณ</span></h1><p>ค้นจากเอกสาร NCD ภาษาไทย พร้อมข้อความต้นทางให้อ่านต่อ</p></section>}
      {hasConversation && <section className="turns" aria-label="คำถามและคำตอบ">{turns.map(turn=><ResponseTurn key={turn.id} turn={turn} open={openEvidence}/>)}{busy && <div className="pending" ref={pendingEl}><div className="user-question">{pending}</div><p role="status"><LoaderCircle className="spinner" size={17} aria-hidden="true"/> กำลังค้นเอกสารและเตรียมคำตอบ <span>{elapsed} วินาที</span></p><small>ครั้งแรกอาจใช้เวลาโหลดระบบเพิ่มเติม</small></div>}</section>}
      <div className="composer-area">
      <form onSubmit={submit} aria-busy={busy} className={`composer ${error?'has-error':''}`}>
        <label htmlFor="question" className="sr-only">คำถามเกี่ยวกับเอกสาร NCD</label>
        <Textarea ref={input} id="question" value={question} onChange={e=>{setQuestion(e.target.value);if(invalid){setInvalid(false);setError('')}}} maxLength={1500} readOnly={busy} aria-invalid={invalid} aria-describedby={`composer-hint${error?' request-error':''}`} placeholder={turns.length?'ถามคำถามใหม่จากเอกสาร…':'ถามเรื่องเบาหวาน ความดัน อาหาร หรือการดูแลสุขภาพ…'} onKeyDown={e=>{if(e.key==='Enter' && (e.ctrlKey || e.metaKey) && !e.nativeEvent.isComposing){e.preventDefault();submit()}}}/>
        <div className="composer-toolbar"><Popover open={settingsOpen} onOpenChange={setSettingsOpen}><PopoverTrigger asChild><Button type="button" variant="ghost" size="sm" disabled={busy} aria-label="ตั้งค่าการค้นหา"><SlidersHorizontal size={16}/><span>การค้นหา</span><ChevronDown size={12}/>{!reranker && <span className="mode-dot" aria-label="Reranker ปิด"/>}</Button></PopoverTrigger><PopoverContent align="start" className="settings-popover"><h3>ตั้งค่าการค้นหา</h3><div className="setting-row"><label htmlFor="reranker">จัดอันดับหลักฐานซ้ำ<span>Passage reranker</span></label><Switch id="reranker" checked={reranker} onCheckedChange={setReranker} disabled={busy}/></div><p>เปิดเพื่อให้โมเดลจัดอันดับข้อความก่อนตอบ ปิดเพื่อข้ามขั้นตอนนี้ ลำดับหลักฐานและคำตอบอาจเปลี่ยนไป</p><div className="cache-note"><Check size={14} aria-hidden="true"/><span>เรียกคำตอบใหม่ทุกครั้ง<small>ไม่อ่านหรือเขียนแคชคำตอบและคะแนน reranker ในเครื่อง</small></span></div></PopoverContent></Popover><div className="send-tools">{question.length>1200 && <span className="fineprint">{question.length}/1500</span>}<Button type="submit" className="send-button" size="icon" disabled={busy} aria-label={busy?'กำลังค้นหา':'ส่งคำถาม'}>{busy?<LoaderCircle className="spinner"/>:<ArrowUp size={20}/>}</Button></div></div>
      </form>
      {error && <p id="request-error" className="request-error" role="alert">{error}<button aria-label="ปิดข้อความผิดพลาด" onClick={()=>setError('')}><X size={14}/></button></p>}
      <p id="composer-hint" className="composer-hint">แต่ละคำถามค้นใหม่แยกกัน · Ctrl / ⌘ + Enter เพื่อส่ง</p>
      </div>
      {!hasConversation && <section className="example-section" aria-label="คำถามตัวอย่าง"><div className="examples">{examples.slice(0,more?examples.length:3).map(([label,q])=><button key={label} onClick={()=>{setQuestion(q);setError('');setInvalid(false);input.current?.focus()}}><span>{label}</span><ArrowUpRight size={13} aria-hidden="true"/></button>)}</div><button className="more-examples" aria-expanded={more} onClick={()=>setMore(!more)}>{more?'แสดงน้อยลง':'คำถามตัวอย่างเพิ่มเติม'}<ChevronDown size={12}/></button></section>}
    </main>
    <footer className="app-footer"><AboutSystem/><p>ใช้เพื่ออ่านและทำความเข้าใจเอกสาร คำตอบอาจคลาดเคลื่อน ควรตรวจหลักฐานก่อนนำไปใช้</p></footer>
    <span className="sr-only" aria-live="polite">{!busy && turns.length ? `คำตอบพร้อมแล้ว ${turns.length} คำถาม อ่านได้ในส่วนคำถามและคำตอบ` : ''}</span>
    <Evidence answer={selected?.turn.data ?? null} sourceId={selected?.id ?? ''} onSource={id=>setSelected(s=>s?{...s,id}:null)} onClose={()=>setSelected(null)}/>
  </>
}
