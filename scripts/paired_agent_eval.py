"""Paired v30/current agent execution under explicitly normalized controls."""
from __future__ import annotations
import argparse,hashlib,importlib,json,os,subprocess,sys,time,types,multiprocessing
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ncd_gemma.capstone_eval.protocol import read_rows,write_json,json_hash,digest,code_hashes,SETTINGS
from ncd_gemma.capstone_eval.runner import service_failure,append_record,request_options
RUN='paired-agent-v30-current-20261105'
PRIVATE=ROOT/'private'/RUN
OUT=ROOT/'reports'/RUN
ARMS=('old_v30','current')

def order(i):return list(ARMS if i%2==0 else reversed(ARMS))
def validate(records,qids,identity):
    seen=set()
    for r in records:
        k=(r['qid'],r['arm'])
        if r['qid'] not in qids or r['arm'] not in ARMS or k in seen or r['manifest_hash']!=identity:raise ValueError('Foreign or duplicate paired record')
        seen.add(k)
    return seen
def check_budget(requests,attempts,consecutive,elapsed):
    if requests>=120 or attempts>=1440 or consecutive>=3 or elapsed>=14400:raise RuntimeError('Paired run budget/outage guard reached')
def durable_json(path,value):
    temp=path.with_suffix('.tmp')
    with temp.open('w',encoding='utf-8') as f:
        json.dump(value,f);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)
    with path.open('r+b') as f:os.fsync(f.fileno())
def deadline(path,now):
    if not path.exists():durable_json(path,{'deadline':now+14400})
    return json.loads(path.read_text())['deadline']
def require_time(end,now):
    if end-now<150:raise RuntimeError('Insufficient time for a full equal-budget request')
def check_resume(path,records,identity):
    if path.exists():
        p=json.loads(path.read_text())
        if p['manifest_hash']!=identity or not any(r['request_id']==p['request_id'] for r in records):raise RuntimeError('Unresolved request; automatic replay prohibited')
def receive_bounded(process,pipe,seconds):
    if not pipe.poll(max(0,seconds)):
        process.terminate();process.join(timeout=5)
        if process.is_alive():process.kill();process.join(timeout=5)
        raise TimeoutError('Worker exceeded outer deadline')
    return pipe.recv()
def worker(pipe):
    from ncd_gemma.config import load_environment,Settings
    from ncd_gemma.llm import ProxyClient
    load_environment();settings=Settings(**SETTINGS);impl=implementations();pipe.send({'ready':True})
    while True:
        task=pipe.recv()
        if task is None:return
        arm,question=task;klass,retriever=impl[arm]
        with request_options():p=klass(ProxyClient(settings),retriever,settings).run(question)
        pipe.send(p)
def old_files():
    plan=json.loads((ROOT/'reports/history/v30_gemma_dev_plan.json').read_text())
    result={}
    for name,want in plan['implementation_sha256'].items():
        ref='008013a' if name in ('llm.py','schemas.py','config.py') else '0893846'
        b=subprocess.check_output(['git','show',ref+':src/ncd_gemma/'+name],cwd=ROOT)
        if name=='config.py':b=b.replace(b'max_sources: int = 12',b'max_sources: int = 20').replace(b'\r\n',b'\n')
        if hashlib.sha256(b).hexdigest()!=want:raise ValueError('Unverified historical file: '+name)
        result[name]=b
    return result
def questions():
    qids=[]
    for p in ['reports/history/v30_gemma_dev_plan.json','reports/extra_dev_v30_plan.json']:
        qids+=json.loads((ROOT/p).read_text())['qids']
    if len(qids)!=60 or len(set(qids))!=60:raise ValueError('Expected 60 unique historical questions')
    gold={q['qid']:q for q in read_rows(ROOT/'data/gold/questions_all_reviewed.jsonl')}
    return [gold[qid] for qid in qids]
def prepare():
    if (OUT/'manifest.json').exists():raise ValueError('Refuse overwrite')
    old=old_files();qs=questions()
    PRIVATE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    snap=PRIVATE/'old';snap.mkdir(exist_ok=True)
    for n,b in old.items():(snap/n).write_bytes(b)
    current=json.loads((ROOT/'reports/capstone-current-v2/manifest.json').read_text())
    m=dict(run_id=RUN,qids=[q['qid'] for q in qs],questions_sha256=json_hash(qs),old={n:hashlib.sha256(b).hexdigest() for n,b in old.items()},current=code_hashes(ROOT),data=current['data'],harness=digest(Path(__file__)),settings=SETTINGS,
      normalized_controls=['current ProxyClient and Settings for both; temperature 0','current cache-aware PassageReranker with cache disabled for both; ranking algorithm unchanged','shared immutable retrieval index/model; separate retriever wrappers and Agent per request','direct Agent.run for both, bypassing HTTP/UI'],
      scope='60 exposed dev, paired alternating order, 120 fresh requests; historical saved outputs never loaded',judge='GPT-6-Luna xhigh, blinded, same rubric',budgets=dict(requests=120,attempts=1440,seconds=14400,consecutive_errors=3))
    write_json(OUT/'manifest.json',m)
    (OUT/'questions.jsonl').write_text(''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in qs),encoding='utf-8')
    print('Prepared',RUN)
def verify(m):
    if m['current']!=code_hashes(ROOT) or m['harness']!=digest(Path(__file__)) or m['questions_sha256']!=json_hash(questions()):raise ValueError('Runtime/harness/questions drift')
    for n,h in m['old'].items():
        if digest(PRIVATE/'old'/n)!=h:raise ValueError('Historical snapshot drift')
    for n,h in m['data'].items():
        if digest(ROOT/n)!=h:raise ValueError('Data drift: '+n)
def implementations():
    from ncd_gemma import config,llm,passage_rerank
    from ncd_gemma.agent import Agent
    from ncd_gemma.retrieval import EvidenceRetriever
    pkg=types.ModuleType('paired_old');pkg.__path__=[str(PRIVATE/'old')];sys.modules['paired_old']=pkg
    # Normalize transport, settings and cache policy, without changing the old agent logic.
    for n,module in [('config',config),('llm',llm),('passage_rerank',passage_rerank)]:sys.modules['paired_old.'+n]=module
    # tool_protocol did not change; it was not included in the old 18-file lock.
    sys.modules['paired_old.tool_protocol']=importlib.import_module('ncd_gemma.tool_protocol')
    old_agent=importlib.import_module('paired_old.agent').Agent
    old_retriever=importlib.import_module('paired_old.retrieval').EvidenceRetriever
    base=EvidenceRetriever();old=old_retriever.__new__(old_retriever);old.__dict__.update(base.__dict__)
    return {'current':(Agent,base),'old_v30':(old_agent,old)}
def run():
    from ncd_gemma.config import load_environment,Settings
    from ncd_gemma.llm import ProxyClient
    load_environment();m=json.loads((OUT/'manifest.json').read_text());verify(m);identity=json_hash(m)
    settings=Settings(**SETTINGS);qs=questions();output=PRIVATE/'answers.jsonl';reservation=PRIVATE/'reservation.json'
    saved=read_rows(output);seen=validate(saved,m['qids'],identity)
    check_resume(reservation,saved,identity)
    end=deadline(PRIVATE/'deadline.json',time.time());require_time(end,time.time())
    process=None;pipe=None
    attempts=sum(r['prediction'].get('stats',{}).get('api_calls',0) for r in saved);consecutive=0
    for r in saved:consecutive=consecutive+1 if service_failure(r['prediction']) else 0
    for i,q in enumerate(qs):
        for arm in order(i):
            if (q['qid'],arm) in seen:continue
            check_budget(len(seen),attempts,consecutive,14400-(end-time.time()));require_time(end,time.time())
            if process is None:
                pipe,child=multiprocessing.Pipe();process=multiprocessing.Process(target=worker,args=(child,),daemon=True);process.start()
                receive_bounded(process,pipe,min(600,end-time.time()))
            if m['current']!=code_hashes(ROOT) or m['harness']!=digest(Path(__file__)):raise ValueError('Mid-run code drift')
            ident=q['qid']+':'+arm;durable_json(reservation,dict(request_id=ident,manifest_hash=identity))
            require_time(end,time.time());beg=time.monotonic();pipe.send((arm,q['question']))
            try:prediction=receive_bounded(process,pipe,min(150,end-time.time()))
            except TimeoutError:
                prediction=dict(status='error',stop_reason='outer_request_timeout',answer='',citations=[],sources=[],trace=[],stats={'api_calls':12,'attempts_accounting':'conservative upper bound; worker interrupted'})
                process=None;pipe.close();pipe=None
            r=dict(run_id=RUN,manifest_hash=identity,request_id=ident,qid=q['qid'],arm=arm,question=q['question'],prediction=prediction,elapsed_seconds=time.monotonic()-beg)
            append_record(output,r);saved.append(r);seen.add((q['qid'],arm));attempts+=prediction.get('stats',{}).get('api_calls',0)
            consecutive=consecutive+1 if service_failure(prediction) else 0
            print(json.dumps(dict(completed=len(seen),qid=q['qid'],arm=arm,status=prediction['status'],seconds=round(r['elapsed_seconds'],1))),flush=True)
    if process is not None:pipe.send(None);process.join(timeout=5)
    verify(m);summarize()
def summarize():
    from ncd_gemma.capstone_eval.metrics import score_answers,make_review_packet
    m=json.loads((OUT/'manifest.json').read_text());verify(m);qs=questions();rs=read_rows(PRIVATE/'answers.jsonl')
    if len(validate(rs,m['qids'],json_hash(m)))!=120:raise ValueError('Incomplete paired run')
    packet,key=make_review_packet(rs,qs)
    for path,rows in [(OUT/'review_packet.jsonl',packet),(PRIVATE/'review_key.jsonl',key)]:path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    write_json(OUT/'metrics.json',dict(run_id=RUN,complete=True,answers={a:score_answers([r for r in rs if r['arm']==a],qs) for a in ARMS},raw_sha256=digest(PRIVATE/'answers.jsonl'),judge_status='pending',scope=m['scope']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','verify','run','summarize']);a=p.parse_args()
    if a.command=='verify':verify(json.loads((OUT/'manifest.json').read_text()));print('PASS paired manifest')
    else:globals()[a.command]()
