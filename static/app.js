'use strict';
const $ = id => document.getElementById(id);
const text = (tag, value, cls) => { const el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; };
const labels = {answered:'พบหลักฐานประกอบ',insufficient_evidence:'หลักฐานยังไม่เพียงพอ',error:'บริการขัดข้อง'};
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
  if ($('question').value.trim()) $('question').removeAttribute('aria-invalid');
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
fetch('/api/health').then(r => { if (!r.ok) throw Error(); return r.json(); }).then(h => {
  $('health').textContent = h.proxy_configured && h.data_present ? 'พร้อมรับคำถาม' : 'ต้องตั้งค่าระบบ';
  if (h.proxy_configured && h.data_present) $('health').classList.add('ok');
}).catch(() => { $('health').textContent = 'ยังเชื่อมต่อไม่ได้'; });
fetch('/api/evaluation').then(r => { if (!r.ok) throw Error(); return r.json(); }).then(data => {
  $('metrics').replaceChildren();
  for (const [label, value] of [['Dense · Recall@5', data.runs['test-A']['recall@5']], ['Hybrid · Recall@5', data.runs['test-B']['recall@5']], ['Hybrid · MRR@10', data.runs['test-B']['mrr@10']]]) {
    const card = text('div', '', 'metric'); card.append(text('span', label), text('strong', value.toFixed(4)), text('small', 'frozen test · 52 answerable')); $('metrics').append(card);
  }
}).catch(() => { $('metrics').textContent = 'ยังโหลดผลทดสอบไม่ได้ ลองรีเฟรชหน้าอีกครั้ง'; });
function showSources(data) {
  $('sources').replaceChildren(); $('citation-links').replaceChildren();
  const evidence = new Map((data.sources || []).map(source => [source.source_id, source]));
  $('source-count').textContent = String(data.citations.length);
  for (const citation of data.citations) {
    const card = text('article', '', 'source-card'); card.id = `source-${citation.source_id}`; card.tabIndex = -1;
    const page = citation.pdf_page_start === citation.pdf_page_end ? `${citation.pdf_page_start}` : `${citation.pdf_page_start}–${citation.pdf_page_end}`;
    card.append(text('h3', `[${citation.source_id}] หลักฐานประกอบคำตอบ`), text('p', `หน้า PDF ${page}`, 'source-location'), text('blockquote', citation.quote));
    if (citation.quote_format === 'structured_pdf_cells') card.append(text('p', 'ข้อความตารางจัดตามหัวคอลัมน์จาก PDF เพื่อให้อ่านคู่กับค่าได้ชัดขึ้น', 'source-id'));
    const details = text('details', ''); details.append(text('summary', 'ดูเอกสารและบริบทเพิ่มเติม'));
    details.append(text('p', `เอกสาร: ${citation.document_id}`, 'source-id'), text('p', `ฉบับ: ${citation.edition_id}`, 'source-id'));
    const source = evidence.get(citation.source_id);
    if (source) { const full = text('div', source.text, 'source-full'); full.tabIndex = 0; full.setAttribute('aria-label', `บริบทของ ${citation.source_id}`); details.append(full); if (source.text_truncated) details.append(text('p', 'ข้อความส่วนนี้ถูกย่อให้พอดีกับขอบเขตการค้น', 'source-id')); }
    card.append(details); $('sources').append(card);
    const link = text('a', `หลักฐาน ${citation.source_id}`); link.href = `#${card.id}`;
    link.addEventListener('click', () => card.focus({preventScroll:true})); $('citation-links').append(link);
  }
  if (!data.citations.length) {
    const empty = text('div', '', 'empty');
    const hint = data.sources?.length
      ? 'ค้นพบข้อความแล้ว แต่คำตอบยังไม่ผ่านการตรวจ จึงยังไม่แสดงเป็นคำตอบที่ยืนยันได้'
      : 'ลองระบุรายละเอียดเพิ่ม เช่น ชื่อเรื่อง กลุ่มคน หรือช่วงอายุที่สนใจ';
    empty.append(text('h3', 'ยังไม่มีหลักฐานที่ยืนยันคำตอบ'), text('p', hint)); $('sources').append(empty);
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
$('ask-form').addEventListener('submit', async event => {
  event.preventDefault(); const question = $('question').value.trim(); if (busy) return;
  if (!question) {
    $('error').textContent = 'กรุณาเขียนคำถามก่อนค้นหา'; $('error').hidden = false;
    $('question').setAttribute('aria-invalid', 'true'); $('question').focus(); return;
  }
  busy = true; copyText = ''; $('submit').disabled = true; $('question').readOnly = true; updateInput();
  document.querySelectorAll('[data-question]').forEach(button => { button.disabled = true; });
  $('submit-label').textContent = 'กำลังค้นหา'; $('ask-form').setAttribute('aria-busy', 'true');
  $('loading').hidden = false; $('error').hidden = true; $('result').hidden = true; $('trace-panel').hidden = true; $('copy-status').textContent = '';
  $('sources').replaceChildren(emptySources.cloneNode(true)); $('source-count').textContent = '0';
  $('announcement').textContent = 'กำลังค้นเอกสารและเตรียมคำตอบ';
  const start = Date.now(); $('elapsed').textContent = 'ผ่านไป 0 วินาที';
  const timer = setInterval(() => { $('elapsed').textContent = `ผ่านไป ${Math.floor((Date.now() - start) / 1000)} วินาที`; }, 1000);
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 240000);
  try {
    const response = await fetch('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question}), signal:controller.signal});
    const data = await response.json();
    if (!response.ok && !data.answer) throw Error(typeof data.detail === 'string' ? data.detail : 'คำถามไม่ผ่านการตรวจสอบ ลองปรับคำถามแล้วค้นใหม่');
    $('result').hidden = false; $('answer').textContent = data.answer;
    $('answer-status').textContent = resultLabel(data);
    $('answer-status').className = `badge ${data.status === 'answered' ? 'ok' : data.status === 'error' ? 'error' : 'warn'}`;
    $('stats').textContent = `ค้น ${data.stats.searches} ครั้ง · ${(data.stats.elapsed_ms / 1000).toFixed(1)} วินาที`;
    showSources(data); showTrace(data);
    copyText = `${question}\n\n${data.answer}` + data.citations.map(c => `\n\n[${c.source_id}] ${c.document_id} · หน้า PDF ${c.pdf_page_start}–${c.pdf_page_end}\n${c.quote}`).join('');
    $('announcement').textContent = `${resultLabel(data)} อ่านได้ที่ส่วนคำตอบจากเอกสาร`;
  } catch (error) {
    $('error').textContent = error.name === 'AbortError' ? 'รอนานกว่าปกติ กรุณาลองค้นใหม่อีกครั้ง' : error.message || 'เชื่อมต่อระบบไม่สำเร็จ กรุณาลองใหม่'; $('error').hidden = false;
  } finally {
    clearInterval(timer); clearTimeout(timeout); busy = false; $('question').readOnly = false; $('submit').disabled = false; $('submit-label').textContent = 'ค้นหาคำตอบ';
    $('ask-form').setAttribute('aria-busy', 'false'); $('loading').hidden = true;
    document.querySelectorAll('[data-question]').forEach(button => { button.disabled = false; }); updateInput();
  }
});
