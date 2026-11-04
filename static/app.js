'use strict';
const $ = id => document.getElementById(id);
const text = (tag, value, cls) => { const el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; };
const labels = {answered:'พบหลักฐานประกอบ',insufficient_evidence:'หลักฐานยังไม่เพียงพอ',out_of_scope:'เริ่มต้นถามได้เลย',error:'บริการขัดข้อง'};
function resultLabel(data) {
  return data.status === 'insufficient_evidence' && (data.sources?.length || data.stop_reason !== 'completed')
    ? 'ยังยืนยันคำตอบไม่ได้' : labels[data.status] || 'ตรวจสอบคำตอบ';
}
let busy = false;
let copyText = '';
const emptySources = $('sources').firstElementChild.cloneNode(true);
function updateInput() {
  $('counter').textContent = `${$('question').value.length} / 1500`;
  $('clear-question').disabled = busy || !$('question').value;
  if ($('question').value.trim() && $('question').getAttribute('aria-invalid') === 'true') {
    $('question').removeAttribute('aria-invalid');
    $('error').hidden = true;
  }
}
$('question').addEventListener('input', updateInput);
$('clear-question').addEventListener('click', () => { $('question').value = ''; updateInput(); $('question').focus(); });
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => {
  $('question').value = button.dataset.question; updateInput(); $('question').focus();
}));
$('help-open').addEventListener('click', () => $('help-dialog').showModal());
$('help-close').addEventListener('click', () => $('help-dialog').close());
$('help-done').addEventListener('click', () => { $('help-dialog').close(); $('question').focus(); });
$('copy-answer').addEventListener('click', async () => {
  if (!copyText) return;
  try { await navigator.clipboard.writeText(copyText); $('copy-status').textContent = 'คัดลอกคำตอบพร้อมแหล่งอ้างอิงแล้ว'; }
  catch { $('copy-status').textContent = 'คัดลอกไม่ได้ ลองเลือกข้อความในคำตอบแล้วคัดลอกด้วยตนเอง'; }
});
function refreshHealth() {
  return fetch('/api/health').then(r => { if (!r.ok) throw Error(); return r.json(); }).then(h => {
    const configured = h.proxy_configured && h.data_present;
    $('health').textContent = configured ? (h.retrieval_loaded ? 'โหลดระบบแล้ว' : 'รอโหลดระบบ') : 'ต้องตั้งค่าระบบ';
    $('health').classList.toggle('ok', Boolean(configured && h.retrieval_loaded));
  }).catch(() => {
    $('health').textContent = 'ยังเชื่อมต่อไม่ได้';
    $('health').classList.remove('ok');
  });
}
refreshHealth();
fetch('/api/evaluation').then(r => { if (!r.ok) throw Error(); return r.json(); }).then(data => {
  $('metrics').replaceChildren();
  for (const [label, value] of [['Dense · Recall@5', data.runs['test-A']['recall@5']], ['Hybrid · Recall@5', data.runs['test-B']['recall@5']], ['Hybrid · MRR@10', data.runs['test-B']['mrr@10']]]) {
    const card = text('div', '', 'metric'); card.append(text('span', label), text('strong', value.toFixed(4)), text('small', 'frozen test · 52 answerable')); $('metrics').append(card);
  }
}).catch(() => { $('metrics').textContent = 'ยังโหลดผลทดสอบไม่ได้ ลองรีเฟรชหน้าอีกครั้ง'; });
// Match verified quotes while preserving the original document whitespace.
function highlightedEvidence(content, quotes) {
  const full = text('div', '', 'source-full retrieved-text');
  const positions = []; let compact = '';
  for (let i = 0; i < content.length; i++) {
    if (!/\s/.test(content[i])) { compact += content[i]; positions.push(i); }
  }
  const ranges = [];
  for (const quote of quotes) {
    const needle = quote.replace(/\s/g, ''); if (!needle) continue;
    let from = 0, at;
    while ((at = compact.indexOf(needle, from)) !== -1) {
      ranges.push([positions[at], positions[at + needle.length - 1] + 1]); from = at + needle.length;
    }
  }
  ranges.sort((a,b) => a[0]-b[0]); const merged = [];
  for (const range of ranges) {
    const last = merged.at(-1);
    if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]); else merged.push([...range]);
  }
  let cursor = 0;
  for (const [start,end] of merged) {
    full.append(document.createTextNode(content.slice(cursor,start)), text('mark',content.slice(start,end))); cursor=end;
  }
  full.append(document.createTextNode(content.slice(cursor))); return full;
}
function showSources(data) {
  $('sources').replaceChildren(); $('citation-links').replaceChildren();
  $('source-count').textContent = String(data.sources.length);
  if (!data.sources.length) {
    const empty = text('div', '', 'empty');
    empty.append(text('h3', 'ยังไม่มีข้อความจากเอกสาร'), text('p', 'ลองระบุหัวข้อหรือกลุ่มคนที่ต้องการค้น')); $('sources').append(empty); return;
  }
  $('sources').append(text('p', 'พื้นสีฟ้า = ข้อความที่ค้นมาให้โมเดลอ่าน · สีเหลือง = ส่วนที่คำตอบอ้างอิง การค้นเจอไม่ได้แปลว่าใช้ยืนยันคำตอบได้', 'evidence-legend'));
  for (const source of data.sources) {
    const citations = data.citations.filter(c => c.source_id === source.source_id);
    const card = text('article', '', 'source-card'); card.id = `source-${source.source_id}`; card.tabIndex = -1;
    card.append(text('h3', `[${source.source_id}] ${citations.length ? 'อ้างอิงในคำตอบ' : 'ค้นมาแล้ว · ยังไม่ได้อ้างอิง'}`));
    card.append(text('p', `เอกสาร: ${source.document_id} · ฉบับ: ${source.edition_id}`, 'source-id'));
    card.append(text('p', `หน้า PDF ${source.pdf_page_start}–${source.pdf_page_end}${source.header_text ? ' · '+source.header_text : ''}`, 'source-location'));
    if (source.section_path?.length) card.append(text('p', `หัวข้อ: ${Array.isArray(source.section_path) ? source.section_path.join(' › ') : source.section_path}`, 'source-id'));
    const searches = data.trace.filter(t => t.event === 'search_docs' && t.sources.includes(source.source_id));
    for (const search of searches) card.append(text('p', `ค้นด้วย: ${search.query}`, 'source-id'));
    const details = text('details', ''); details.open = citations.length > 0;
    details.append(text('summary', 'ดูข้อความที่ค้นมาและส่วนที่อ้างอิง'));
    const full = highlightedEvidence(source.text, citations.map(c => c.quote));
    full.tabIndex = 0; full.setAttribute('aria-label', `ข้อความที่ค้นมา ${source.source_id}`); details.append(full);
    for (const citation of citations) {
      details.append(text('p', citation.quote_format === 'structured_pdf_cells' ? 'อ้างอิงจากเซลล์ตาราง PDF ที่จัดหัวคอลัมน์ใหม่:' : 'ข้อความที่คำตอบอ้างอิง:', 'source-id'), text('blockquote', citation.quote));
    }
    if (source.text_truncated) details.append(text('p', 'ส่วนข้อความนี้ถูกตัดตามขอบเขตบริบทที่ส่งให้โมเดล', 'source-id'));
    card.append(details); $('sources').append(card);
    if (citations.length) {
      const link = text('a', `หลักฐาน ${source.source_id}`); link.href = `#${card.id}`;
      link.addEventListener('click', () => { details.open = true; card.focus({preventScroll:true}); }); $('citation-links').append(link);
    }
  }
}
function showTrace(data) {
  $('trace').replaceChildren();
  for (const item of data.trace) {
    let line;
    if (item.event === 'search_docs') line = `ค้น: ${item.query} → ${item.sources.join(', ') || 'ไม่พบหลักฐาน'}`;
    else if (item.event === 'model') line = `Model รอบ ${item.round}${item.cached ? ' (ใช้ cache)' : ''}`;
    else line = `${item.event}: ${item.reason || item.category || ''}`;
    $('trace').append(text('li', line));
  }
  $('trace').append(text('li', `จบการทำงาน: ${data.stop_reason}`)); $('trace-panel').hidden = false;
}
async function readAskResponse(response) {
  let data;
  try { data = await response.json(); }
  catch {
    throw Error(response.ok ? 'ระบบส่งข้อมูลกลับมาไม่ครบ กรุณาลองค้นใหม่' : 'บริการขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง');
  }
  if (!response.ok && !data?.answer) {
    throw Error(typeof data?.detail === 'string' ? data.detail : 'ยังส่งคำถามไม่ได้ กรุณาตรวจคำถามแล้วลองใหม่');
  }
  const valid = data && Object.hasOwn(labels, data.status) && typeof data.answer === 'string'
    && Array.isArray(data.citations) && data.citations.every(c => c && typeof c.source_id === 'string'
      && typeof c.quote === 'string' && typeof c.document_id === 'string' && typeof c.edition_id === 'string'
      && Number.isInteger(c.pdf_page_start) && Number.isInteger(c.pdf_page_end))
    && Array.isArray(data.sources) && data.sources.every(s => s && typeof s.source_id === 'string' && typeof s.text === 'string')
    && Array.isArray(data.trace) && data.trace.every(t => t && typeof t.event === 'string'
      && (t.event !== 'search_docs' || (typeof t.query === 'string' && Array.isArray(t.sources))))
    && data.stats && Number.isFinite(data.stats.searches) && Number.isFinite(data.stats.elapsed_ms)
    && typeof data.stop_reason === 'string';
  if (!valid) throw Error('ระบบส่งข้อมูลกลับมาไม่ครบ กรุณาลองค้นใหม่');
  return data;
}
$('ask-form').addEventListener('submit', async event => {
  event.preventDefault(); const question = $('question').value.trim(); if (busy) return;
  if (!question) {
    $('error').textContent = 'กรุณาเขียนคำถามก่อนค้นหา'; $('error').hidden = false;
    $('question').setAttribute('aria-invalid', 'true'); $('question').focus(); return;
  }
  busy = true; $('search-mode').disabled = true; $('search-mode').dataset.state = 'loading'; copyText = ''; $('submit').disabled = true; $('question').readOnly = true; updateInput();
  document.querySelectorAll('[data-question]').forEach(button => { button.disabled = true; });
  $('submit-label').textContent = 'กำลังค้นหา'; $('ask-form').setAttribute('aria-busy', 'true');
  $('loading').hidden = false; $('error').hidden = true; $('result').hidden = true; $('trace-panel').hidden = true; $('copy-status').textContent = '';
  $('sources').replaceChildren(emptySources.cloneNode(true)); $('source-count').textContent = '0';
  $('announcement').textContent = 'กำลังค้นเอกสารและเตรียมคำตอบ';
  const start = Date.now(); $('elapsed').textContent = 'ผ่านไป 0 วินาที';
  const timer = setInterval(() => { $('elapsed').textContent = `ผ่านไป ${Math.floor((Date.now() - start) / 1000)} วินาที`; }, 1000);
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 240000);
  try {
    const response = await fetch('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question, use_cache:false, use_reranker:$('use-reranker').checked}), signal:controller.signal});
    const data = await readAskResponse(response);
    $('result').hidden = false; $('answer-heading').textContent = data.status === 'out_of_scope' ? 'ยินดีต้อนรับ' : 'คำตอบจากเอกสาร'; $('answer').textContent = data.answer;
    $('answer-status').textContent = resultLabel(data);
    $('answer-status').className = `badge ${['answered','out_of_scope'].includes(data.status) ? 'ok' : data.status === 'error' ? 'error' : 'warn'}`;
    $('stats').textContent = data.status === 'out_of_scope' ? 'คำทักทาย · ไม่ต้องค้นเอกสารหรือเรียกโมเดล' : `ค้น ${data.stats.searches} ครั้ง · ${(data.stats.elapsed_ms / 1000).toFixed(1)} วินาที`;
    if (data.runtime_options) $('stats').textContent += ` · reranker ${data.runtime_options.use_reranker ? 'ON' : 'OFF'} · Local cache ${data.runtime_options.use_cache ? 'ON' : 'OFF'}`;
    $('search-mode').dataset.state = 'success';
    showSources(data); showTrace(data);
    copyText = `${question}\n\n${data.answer}` + data.citations.map(c => `\n\n[${c.source_id}] ${c.document_id} · หน้า PDF ${c.pdf_page_start}–${c.pdf_page_end}\n${c.quote}`).join('');
    $('announcement').textContent = `${resultLabel(data)} อ่านได้ที่ส่วนคำตอบจากเอกสาร`;
  } catch (error) {
    $('search-mode').dataset.state = 'error';
    $('result').hidden = true; $('trace-panel').hidden = true; copyText = '';
    $('error').textContent = error.name === 'AbortError' ? 'รอนานกว่าปกติ กรุณาลองค้นใหม่อีกครั้ง'
      : error instanceof TypeError ? 'เชื่อมต่อระบบไม่สำเร็จ กรุณาลองใหม่'
      : error.message || 'เชื่อมต่อระบบไม่สำเร็จ กรุณาลองใหม่'; $('error').hidden = false;
  } finally {
    clearInterval(timer); clearTimeout(timeout); busy = false; $('search-mode').disabled = false; $('question').readOnly = false; $('submit').disabled = false; $('submit-label').textContent = 'ค้นหาคำตอบ';
    $('ask-form').setAttribute('aria-busy', 'false'); $('loading').hidden = true;
    document.querySelectorAll('[data-question]').forEach(button => { button.disabled = false; }); updateInput();
    refreshHealth();
  }
});

document.querySelectorAll('input[name="search-mode"]').forEach(input => input.addEventListener('change', () => {
  $('search-mode').dataset.state = 'default';
  $('search-mode-hint').textContent = $('use-reranker').checked
    ? 'Hybrid retrieval → Cross-encoder reranking → ส่งหลักฐานให้โมเดล'
    : 'Hybrid retrieval → ส่งหลักฐานให้โมเดลโดยไม่จัดอันดับซ้ำ';
}));
