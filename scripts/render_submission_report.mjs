// Print the report with Chromium's Thai shaping, keeping selectable Unicode text.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.env.PLAYWRIGHT_BROWSERS_PATH='D:/skill ai/.tools/demo-runtime/browsers';
const {chromium}=await import('file:///D:/skill%20ai/.tools/demo-runtime/node_modules/playwright/index.mjs');
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const inline=s=>esc(s).replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2">$1</a>');
const text=fs.readFileSync(path.join(root,'docs/PROJECT_REPORT_SUBMISSION_TH.md'),'utf8');
const groups=text.split(/\n(?=## \d)/);
const sections=groups.map((group,index)=>{
 let rows=group.split('\n'),html='',table=false;
 for(const row of rows){
  if(row.startsWith('|')){
   if(/^\|[\s|:-]+$/.test(row))continue;
   if(!table){html+='<table>';table=true;}
   html+='<tr>'+row.split('|').slice(1,-1).map(x=>'<td>'+inline(x.trim())+'</td>').join('')+'</tr>';continue;
  }
  if(table){html+='</table>';table=false;}
  if(!row.trim())continue;
  const img=row.match(/^!\[([^\]]*)\]\(([^)]+)\)/);
  if(img){
   let target=path.resolve(root,'docs',img[2]);
   if(img[2].includes('architecture'))target=path.join(root,'output/pdf/assets/architecture-black-text.png');
   html+=`<figure><img src="${pathToFileURL(target).href}"><figcaption>${esc(img[1])}</figcaption></figure>`;continue;
  }
  if(row.startsWith('### '))html+='<h3>'+inline(row.slice(4))+'</h3>';
  else if(row.startsWith('## '))html+='<h2>'+inline(row.slice(3))+'</h2>';
  else if(row.startsWith('# '))html+='<h1>'+inline(row.slice(2))+'</h1>';
  else html+='<p>'+inline(row)+'</p>';
 }
 if(table)html+='</table>';
 return `<section class="page page-${index+1}">${html}</section>`;
});
const css=`@font-face{font-family:ReportThai;src:url('file:///C:/Windows/Fonts/angsana.ttc');font-weight:400} @font-face{font-family:ReportThaiBold;src:local('Angsana New Bold');font-weight:700}
@page{size:A4;margin:22mm 22mm 23mm}*{box-sizing:border-box;color:#000!important}body{font-family:'Angsana New',ReportThai,serif;font-size:16pt;line-height:1.05;margin:0}h1,h2,h3{font-weight:700;break-after:avoid;margin:0 0 7pt}h1{font-size:26pt;text-align:center}h2{font-size:20pt}h3{font-size:18pt;margin-top:8pt}p{margin:0 0 7pt;overflow-wrap:break-word}a{text-decoration:none}section.page{break-before:page}section.page:first-child{break-before:auto}.page-1>p:nth-of-type(-n+4){text-align:center;margin-bottom:6pt}table{border-collapse:collapse;width:100%;margin:5pt 0 8pt;font-size:14pt;line-height:1.05}tr{break-inside:avoid}td{padding:4pt 5pt;vertical-align:top}tr:first-child{font-weight:bold;background:#f2f2f2;border-top:1px solid #555;border-bottom:1px solid #aaa}tr:last-child{border-bottom:1px solid #555}figure{margin:5pt auto 9pt;text-align:center;break-inside:avoid}figure img{max-width:100%;width:137mm;max-height:115mm;object-fit:contain}figcaption{font-size:14pt;line-height:1.1}.page-7 figure img{width:125mm;max-height:90mm}`;
const html=`<!doctype html><html lang="th"><meta charset="utf-8"><title>NCD Evidence</title><style>${css}</style><body>${sections.join('\n')}</body></html>`;
const htmlPath=path.join(root,'output/pdf/report-print.html');fs.writeFileSync(htmlPath,html);
const browser=await chromium.launch({headless:true});const p=await browser.newPage();
await p.goto(pathToFileURL(htmlPath).href);await p.evaluate(()=>document.fonts.ready);
await p.pdf({path:path.join(root,'output/pdf/NCD_EVIDENCE_SUBMISSION_67070060.pdf'),format:'A4',printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="font-family:serif;font-size:9px;width:100%;text-align:center;color:#000"><span class="pageNumber"></span></div>',preferCSSPageSize:true});
await browser.close();console.log('Thai-shaped PDF rendered');
