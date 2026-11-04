export type Citation = { source_id: string; quote: string; document_id: string; edition_id: string; pdf_page_start: number; pdf_page_end: number; quote_format?: string }
export type Source = { source_id: string; text: string; document_id?: string; edition_id?: string; pdf_page_start?: number; pdf_page_end?: number; header_text?: string; section_path?: string[] | string; text_truncated?: boolean }
export type Trace = { event: string; query?: string; sources?: string[]; round?: number; cached?: boolean; reason?: string; category?: string }
export type Answer = { run_id?: string; status: 'answered' | 'insufficient_evidence' | 'out_of_scope' | 'error'; answer: string; sources: Source[]; citations: Citation[]; trace: Trace[]; stats: { searches: number; elapsed_ms: number; api_calls?: number; model_rounds?: number }; stop_reason: string; runtime_options?: { use_cache: boolean; use_reranker: boolean } }
const record = (x: unknown): x is Record<string, any> => !!x && typeof x === 'object' && !Array.isArray(x)
export function isAnswer(x: unknown): x is Answer {
  return record(x) && ['answered','insufficient_evidence','out_of_scope','error'].includes(x.status)
    && typeof x.answer === 'string' && typeof x.stop_reason === 'string'
    && Array.isArray(x.sources) && x.sources.every((s: unknown) => record(s) && typeof s.source_id === 'string' && typeof s.text === 'string'
      && typeof s.document_id === 'string' && typeof s.edition_id === 'string' && Number.isInteger(s.pdf_page_start) && Number.isInteger(s.pdf_page_end)
      && (s.header_text === undefined || typeof s.header_text === 'string')
      && (s.section_path === undefined || typeof s.section_path === 'string' || (Array.isArray(s.section_path) && s.section_path.every((a: unknown) => typeof a === 'string'))))
    && Array.isArray(x.citations) && x.citations.every((c: unknown) => record(c) && typeof c.source_id === 'string' && typeof c.quote === 'string' && typeof c.document_id === 'string' && typeof c.edition_id === 'string' && Number.isInteger(c.pdf_page_start) && Number.isInteger(c.pdf_page_end))
    && Array.isArray(x.trace) && x.trace.every((t: unknown) => record(t) && typeof t.event === 'string'
      && (t.reason === undefined || typeof t.reason === 'string') && (t.category === undefined || typeof t.category === 'string')
      && (t.round === undefined || Number.isFinite(t.round))
      && (t.event !== 'search_docs' || (typeof t.query === 'string' && Array.isArray(t.sources) && t.sources.every((s: unknown) => typeof s === 'string'))))
    && record(x.stats) && Number.isFinite(x.stats.searches) && Number.isFinite(x.stats.elapsed_ms)
    && (x.stats.api_calls === undefined || Number.isFinite(x.stats.api_calls))
    && (x.runtime_options === undefined || (record(x.runtime_options) && typeof x.runtime_options.use_cache === 'boolean' && typeof x.runtime_options.use_reranker === 'boolean'))
}
export async function ask(question: string, reranker: boolean, signal: AbortSignal): Promise<Answer> {
  const res = await fetch('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, use_cache:false, use_reranker:reranker}), signal})
  let data: unknown
  try { data = await res.json() } catch { throw new Error('บริการส่งข้อมูลกลับมาไม่สมบูรณ์ กรุณาลองส่งคำถามอีกครั้ง') }
  if (!res.ok && !isAnswer(data)) throw new Error(record(data) && typeof data.detail === 'string' ? data.detail : 'ส่งคำถามไม่สำเร็จ กรุณาลองใหม่อีกครั้ง')
  if (!isAnswer(data)) throw new Error('รูปแบบคำตอบไม่สมบูรณ์ กรุณาลองส่งคำถามอีกครั้ง')
  return data
}
