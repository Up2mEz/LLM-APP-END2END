const $ = id => document.getElementById(id);
const text = (tag, value, cls) => { const el = document.createElement(tag); el.textContent = value; if (cls) el.className = cls; return el; };
const labels = {answered:'มีหลักฐานอ้างอิง',insufficient_evidence:'หลักฐานยังไม่เพียงพอ',error:'บริการขัดข้อง'};
$('question').addEventListener('input',()=>{$('counter').textContent=`${$('question').value.length} / 1500`;});
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{$('question').value=button.dataset.question;$('question').dispatchEvent(new Event('input'));$('question').focus();}));
fetch('/api/health').then(r=>r.json()).then(h=>{$('health').textContent=h.proxy_configured&&h.data_present?'พร้อมรับคำถาม':'ต้องตั้งค่าระบบ';if(h.proxy_configured&&h.data_present)$('health').classList.add('ok');}).catch(()=>{$('health').textContent='ยังเชื่อมต่อระบบไม่ได้';});
fetch('/api/evaluation').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{
  $('metrics').replaceChildren();
  for(const [label,value] of [['Dense · Recall@5',data.runs['test-A']['recall@5']],['Hybrid · Recall@5',data.runs['test-B']['recall@5']],['Hybrid · MRR@10',data.runs['test-B']['mrr@10']]]){
    const card=text('div','', 'metric');card.append(text('span',label),text('strong',value.toFixed(4)),text('small','frozen test · 52 answerable'));$('metrics').append(card);
  }
}).catch(()=>{$('metrics').textContent='ยังไม่มีไฟล์ผลประเมิน';});
$('ask-form').addEventListener('submit',async event=>{
  event.preventDefault();const question=$('question').value.trim();if(!question)return;
  $('submit').disabled=true;$('loading').hidden=false;$('error').hidden=true;$('result').hidden=true;$('trace-panel').hidden=true;
  $('sources').replaceChildren();$('source-count').textContent='0';
  try{
    const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
    const data=await response.json();if(!response.ok&&!data.answer)throw Error(typeof data.detail==='string'?data.detail:'คำถามไม่ผ่านการตรวจสอบ');
    $('result').hidden=false;$('answer').textContent=data.answer;$('answer-status').textContent=labels[data.status]||data.status;
    $('answer-status').className='badge'+(data.status==='answered'?' ok':'');
    $('stats').textContent=`ค้น ${data.stats.searches} ครั้ง · ${(data.stats.elapsed_ms/1000).toFixed(1)} วินาที · ${data.model}`;
    $('source-count').textContent=String(data.citations.length);
    for(const citation of data.citations){const card=text('article','', 'source-card');card.append(text('h3',`[${citation.source_id}] ${citation.document_id}`),text('p',`ฉบับ ${citation.edition_id} · หน้า PDF ${citation.pdf_page_start}–${citation.pdf_page_end}`),text('blockquote',citation.quote));$('sources').append(card);}
    if(!data.citations.length)$('sources').append(text('p','ยังไม่มีหลักฐานที่นำมาอ้างอิงเป็นคำตอบได้','empty'));
    $('trace').replaceChildren();for(const item of data.trace){let line;if(item.event==='search_docs')line=`ค้น: ${item.query} → ${item.sources.join(', ')||'ไม่พบหลักฐาน'}`;else if(item.event==='model')line=`Model รอบ ${item.round}${item.cached?' (ใช้ cache)':''}`;else line=`${item.event}: ${item.reason||item.category||''}`;$('trace').append(text('li',line));}
    $('trace').append(text('li',`จบการทำงาน: ${data.stop_reason}`));$('trace-panel').hidden=false;
  }catch(error){$('error').textContent=error.message||'เชื่อมต่อระบบไม่สำเร็จ';$('error').hidden=false;}
  finally{$('submit').disabled=false;$('loading').hidden=true;}
});
