"""Mechanical paired-run audit, deliberately separate from answer correctness."""
import json
from pathlib import Path
from paired_agent_eval import ROOT,OUT,PRIVATE,verify,validate,json_hash,digest
from ncd_gemma.capstone_eval.runner import service_failure

def main():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'));verify(manifest)
    raw=PRIVATE/'answers.jsonl';rs=[json.loads(x) for x in raw.read_text(encoding='utf-8').splitlines()]
    if len(validate(rs,manifest['qids'],json_hash(manifest)))!=120:raise ValueError('Incomplete pairs')
    p={(r['qid'],r['arm']):r['prediction'] for r in rs};qs=manifest['qids']
    result=dict(run_id=manifest['run_id'],records=len(rs),pairs=len(qs),proxy_attempts=sum(r['prediction'].get('stats',{}).get('api_calls',0) for r in rs),
      same_status=sum(p[q,'old_v30']['status']==p[q,'current']['status'] for q in qs),
      identical_answer_text=sum(p[q,'old_v30'].get('answer')==p[q,'current'].get('answer') for q in qs),
      status_differences=[dict(qid=q,old_status=p[q,'old_v30']['status'],current_status=p[q,'current']['status']) for q in qs if p[q,'old_v30']['status']!=p[q,'current']['status']],
      service_failures=[dict(qid=r['qid'],arm=r['arm'],status=r['prediction']['status'],stop_reason=r['prediction'].get('stop_reason')) for r in rs if service_failure(r['prediction'])],
      raw_sha256=digest(raw),scope='Mechanical execution audit; equality and answer/abstain decisions are not semantic correctness')
    (OUT/'execution_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
