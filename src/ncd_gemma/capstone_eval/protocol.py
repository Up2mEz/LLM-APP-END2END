from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RUN='capstone-current-v2'
PROJECT='ncd-gemma-capstone'
ARMS={'dense_default':'A','hybrid_current':'B'}
SETTINGS=dict(model='gemma-4-E4B-it',max_steps=6,max_searches=3,request_timeout=45.0,agent_timeout=150.0,max_output_tokens=1400,context_chars=18000,max_sources=20)

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def json_hash(value) -> str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def read_rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()] if path.exists() else []

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)

def select_questions(gold_path: Path) -> list[dict]:
    buckets=defaultdict(list)
    for q in read_rows(gold_path):
        if q['status']=='gold' and q['split']=='dev':buckets[q['type']].append(q)
    kinds=['condition','fact','multi_page','number_unit','table','unanswerable']
    if set(buckets)!=set(kinds) or any(len(buckets[k])<5 for k in kinds):raise ValueError('Need six types with five questions each')
    for rows in buckets.values():rows.sort(key=lambda q:hashlib.sha256(('ncd-gemma-dev-v1:'+q['qid']).encode()).hexdigest())
    result=[buckets[k][i] for i in range(5) for k in kinds]
    if len({q['qid'] for q in result})!=30:raise ValueError('Duplicate qids')
    return result

def code_hashes(root: Path) -> dict:
    files=[]
    for folder in ('src/ncd_gemma','src/ncdqa','configs','schemas'):
        files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for name in ('requirements-runtime.txt','pyproject.toml','run.ps1'):
        if (root/name).exists():files.append(root/name)
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(files)}

def build_manifest(root: Path, questions: list[dict]) -> dict:
    gold=root/'data/gold/questions_all_reviewed.jsonl'
    data={gold.relative_to(root).as_posix():digest(gold)}
    release=root/'provenance/public_data_release.json'
    if release.exists():
        for r in json.loads(release.read_text(encoding='utf-8'))['files']:
            rel=r['path']
            # Old ranked hits are explicitly excluded: only serving data and gold.
            if rel.startswith('data/frozen/'):continue
            p=(root/rel).resolve()
            if not p.is_relative_to((root/'data').resolve()):raise ValueError('Unsafe data path')
            actual=digest(p)
            if actual!=r['sha256']:raise ValueError('Data hash mismatch: '+rel)
            data[rel]=actual
    return dict(project_id=PROJECT,run_id=RUN,created_utc=datetime.now(timezone.utc).isoformat(),
                code=code_hashes(root),data=data,questions_sha256=json_hash(questions),qids=[q['qid'] for q in questions],
                settings=SETTINGS,temperature=0,use_cache=False,use_reranker=True,arms=ARMS,
                selection='30 exposed dev; six types x five; SHA256(ncd-gemma-dev-v1:qid)',
                budgets=dict(app_requests=62,proxy_attempts=744,wall_seconds=10800,consecutive_service_errors=3),
                judge=dict(model='gpt-6-luna',reasoningEffort='xhigh',transport='T3 delegated agent',temperature='not exposed'))

def verify_manifest(root: Path, manifest: dict, *, full_data: bool=True) -> None:
    if manifest['project_id']!=PROJECT or manifest['run_id']!=RUN:raise ValueError('Foreign project/run')
    if manifest['settings']!=SETTINGS or manifest['arms']!=ARMS or manifest['use_cache'] or not manifest['use_reranker']:raise ValueError('Settings drift')
    if code_hashes(root)!=manifest['code']:raise ValueError('Code drift')
    qs=select_questions(root/'data/gold/questions_all_reviewed.jsonl')
    if json_hash(qs)!=manifest['questions_sha256'] or [q['qid'] for q in qs]!=manifest['qids']:raise ValueError('Question drift')
    if full_data:
        for rel,expected in manifest['data'].items():
            if digest(root/rel)!=expected:raise ValueError('Data drift: '+rel)
