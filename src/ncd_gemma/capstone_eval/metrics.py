from __future__ import annotations
import json
from pathlib import Path
from .protocol import RUN, ARMS, json_hash, read_rows, write_json, verify_manifest, select_questions, digest
from .runner import validate_records, service_failure

def score_retrieval(records:list[dict],questions:list[dict]) -> dict:
    from ncdqa.retrieval.evaluate import score_question
    by={r['qid']:r for r in records};scores=[]
    for q in questions:
        if q['answerable']:scores.append(score_question(by[q['qid']].get('hits',[]),q['evidence'],(5,)))
    return dict(n=len(questions),answerable=len(scores),**{k:sum(s[k] for s in scores)/len(scores) for k in ('recall@5','hit@5','mrr@5')})

def score_answers(records:list[dict],questions:list[dict]) -> dict:
    from ncdqa.retrieval.evaluate import covers
    by={r['qid']:r['prediction'] for r in records};n=len(questions);decision=errors=hit=0;den=sum(q['answerable'] for q in questions)
    for q in questions:
        p=by[q['qid']];error=service_failure(p);errors+=error
        decision+=not error and ((p['status']=='answered')==q['answerable'])
        if q['answerable']:
            ids={c['source_id'] for c in p.get('citations',[])}
            hit+=any(covers(s,e) for s in p.get('sources',[]) if s['source_id'] in ids for e in q['evidence'])
    return dict(n=n,error_rate=errors/n,errors=errors,abstention_decision_accuracy=decision/n,primary_citation_hit=hit/den if den else None)

def make_review_packet(records:list[dict],questions:list[dict]):
    gold={q['qid']:q for q in questions};packet=[];key=[]
    for r in sorted(records,key=lambda r:json_hash([r['qid'],r['arm'],'blind-v1'])):
        ident=f'item-{len(packet)+1:03}';q=gold[r['qid']];p=r['prediction']
        packet.append(dict(item_id=ident,question=q['question'],reference_answer=q['answer'],answerable=q['answerable'],gold_evidence=q['evidence'],response={k:p.get(k) for k in ('status','answer','citations','sources')}))
        key.append(dict(item_id=ident,qid=r['qid'],arm=r['arm']))
    return packet,key

def summarize(root:Path,manifest:dict) -> dict:
    verify_manifest(root,manifest);folder=root/'private'/RUN;out=root/'reports'/RUN
    qs=select_questions(root/'data/gold/questions_all_reviewed.jsonl');result={}
    for stage in ('retrieval','answers'):
        rows=read_rows(folder/(stage+'.jsonl'))
        seen=validate_records(rows,json_hash(manifest),stage,manifest['qids'])
        if len(seen)!=60:raise ValueError('Incomplete '+stage)
        fn=score_retrieval if stage=='retrieval' else score_answers
        result[stage]={arm:fn([r for r in rows if r['arm']==arm],qs) for arm in ARMS}
        if stage=='answers':
            packet,key=make_review_packet(rows,qs)
            (out/'review_packet.jsonl').write_text('\n'.join(json.dumps(p,ensure_ascii=False) for p in packet)+'\n',encoding='utf-8')
            (folder/'review_key.jsonl').write_text('\n'.join(json.dumps(p) for p in key)+'\n',encoding='utf-8')
    a,b=result['retrieval']['dense_default'],result['retrieval']['hybrid_current']
    delta={k:b[k]-a[k] for k in ('recall@5','hit@5','mrr@5')}
    result.update(run_id=RUN,manifest_hash=json_hash(manifest),complete=True,retrieval_delta=delta,measured_retrieval_improvement=delta['recall@5']>0,
                  raw_hashes={s:digest(folder/(s+'.jsonl')) for s in ('retrieval','answers')},judge_status='pending',scope='Exposed dev; fresh current pipeline; no frozen predictions imported')
    write_json(out/'metrics.json',result)
    return result
