from __future__ import annotations
import json
import os
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from .protocol import RUN, ARMS, SETTINGS, json_hash, read_rows, write_json, verify_manifest, select_questions

class ArmRetriever:
    def __init__(self,base,variant):self.base,self.variant,self.calls=base,variant,[]
    def search(self,args):
        hits=self.base.search(args,variant=self.variant)
        self.calls.append(dict(args=args.model_dump(),hits=hits))
        return hits

class Budget:
    def __init__(self):self.requests=0;self.attempts=0;self.consecutive=0;self.started=time.time()
    def check(self):
        if self.consecutive>=3:raise RuntimeError('Three consecutive service errors')
        if self.requests>=62 or self.attempts>=744 or time.time()-self.started>=10800:raise RuntimeError('Evaluation budget reached')
    def record(self,attempts,service_error):
        self.requests+=1;self.attempts+=attempts
        self.consecutive=self.consecutive+1 if service_error else 0

def service_failure(prediction:dict) -> bool:
    return (prediction.get('status')=='error' or prediction.get('stop_reason')=='verification_unavailable'
            or any(t.get('event') in ('proxy_error','verification_error') for t in prediction.get('trace',[])))

def reserve_request(path:Path,budget:Budget,request_id:str) -> None:
    if path.exists() and not json.loads(path.read_text()).get('resolved'):
        raise RuntimeError('Unresolved in-flight request; do not retry automatically')
    budget.check()
    write_json(path,dict(request_id=request_id,budget_before=dict(budget.__dict__),resolved=False))

def reconcile_reservation(path:Path,records:list[dict],budget:Budget) -> None:
    if not path.exists():return
    state=json.loads(path.read_text())
    if state.get('resolved'):return
    matches=[r for r in records if r.get('request_id')==state['request_id']]
    if len(matches)!=1:raise RuntimeError('Unresolved in-flight request; preserve run, no automatic retry')
    budget.__dict__.update(state['budget_before'])
    p=matches[0]['prediction'];budget.record(p.get('stats',{}).get('api_calls',0),service_failure(p))
    write_json(path.parent/'budget.json',budget.__dict__)
    write_json(path,{**state,'resolved':True})

def validate_records(records,manifest_hash,stage,qids):
    seen=set()
    for r in records:
        key=(r['qid'],r['arm'])
        if r['run_id']!=RUN or r['manifest_hash']!=manifest_hash or r['stage']!=stage or r['qid'] not in qids or r['arm'] not in ARMS or key in seen:raise ValueError('Foreign/duplicate record')
        seen.add(key)
    return seen

@contextmanager
def request_options():
    from ncd_gemma import runtime_options as opts
    a=opts.use_cache.set(False);b=opts.use_reranker.set(True)
    try:yield
    finally:opts.use_cache.reset(a);opts.use_reranker.reset(b)

def append_record(path,record):
    with path.open('a',encoding='utf-8') as f:
        f.write(json.dumps(record,ensure_ascii=False,default=lambda x:x.item())+'\n');f.flush();os.fsync(f.fileno())

def run_stage(root: Path,manifest:dict,stage:str,base=None) -> Path:
    from ncd_gemma.config import Settings
    from ncd_gemma.schemas import SearchArgs
    from ncd_gemma.retrieval import EvidenceRetriever
    from ncd_gemma.agent import Agent
    from ncd_gemma.llm import ProxyClient
    from ncd_gemma import server
    from fastapi.testclient import TestClient
    verify_manifest(root,manifest)
    settings=Settings.from_env();actual=asdict(settings);actual.pop('cache_dir')
    if actual!=manifest['settings']:raise ValueError('Effective web settings differ from manifest: '+str(actual))
    folder=root/'private'/RUN;folder.mkdir(parents=True,exist_ok=True)
    output=folder/(stage+'.jsonl');identity=json_hash(manifest)
    qs=select_questions(root/'data/gold/questions_all_reviewed.jsonl')
    if stage=='pilot':qs=qs[:1]
    saved=read_rows(output);seen=validate_records(saved,identity,stage,[q['qid'] for q in qs])
    budget=Budget();bp=folder/'budget.json'
    if bp.exists():budget.__dict__.update(json.loads(bp.read_text()))
    elif stage!='retrieval':write_json(bp,budget.__dict__)
    reservation=folder/'reservation.json'
    reconcile_reservation(reservation,read_rows(folder/'pilot.jsonl')+read_rows(folder/'answers.jsonl'),budget)
    started=time.monotonic();base=base or EvidenceRetriever()
    write_json(folder/'startup.json',dict(load_seconds=time.monotonic()-started,stage=stage,not_included_in_request_latency=True))
    original_agent=server._agent
    auth=(os.getenv('NCD_DEMO_USER','demo'),os.environ['NCD_DEMO_PASSWORD']) if os.getenv('NCD_DEMO_PASSWORD') else None
    try:
        with TestClient(server.app) as client:
            for q in qs:
                arms=list(ARMS)
                if int(json_hash(q['qid'])[-1],16)%2:arms.reverse()
                for arm in arms:
                    if (q['qid'],arm) in seen:continue
                    verify_manifest(root,manifest,full_data=False)
                    budget.check()
                    adapter=ArmRetriever(base,ARMS[arm]);start=time.monotonic()
                    record=dict(run_id=RUN,manifest_hash=identity,stage=stage,qid=q['qid'],arm=arm,question=q['question'],question_hash=json_hash(q['question']))
                    if stage=='retrieval':
                        with request_options():record['hits']=adapter.search(SearchArgs(query=q['question'],top_k=5))
                    else:
                        server._agent=Agent(ProxyClient(settings),adapter,settings)
                        request=dict(question=q['question'],use_cache=False,use_reranker=True)
                        record['request_id']=stage+':'+q['qid']+':'+arm
                        reserve_request(reservation,budget,record['request_id'])
                        response=client.post('/api/ask',json=request,auth=auth)
                        payload=response.json()
                        if response.status_code not in (200,502):
                            payload=dict(status='error',answer='',citations=[],sources=[],trace=[],stats={},stop_reason='http_'+str(response.status_code))
                        record.update(request=request,http_status=response.status_code,prediction=payload)
                    record.update(search_calls=adapter.calls,elapsed_seconds=time.monotonic()-start)
                    append_record(output,record)
                    if stage!='retrieval':reconcile_reservation(reservation,[record],budget)
                    print(json.dumps(dict(stage=stage,completed=len(seen)+1,qid=q['qid'],arm=arm,seconds=round(record['elapsed_seconds'],2),status=record.get('prediction',{}).get('status','retrieved'))),flush=True)
                    seen.add((q['qid'],arm))
    finally:server._agent=original_agent
    verify_manifest(root,manifest)
    if len(seen)!=len(qs)*2:raise ValueError('Incomplete stage')
    return output
