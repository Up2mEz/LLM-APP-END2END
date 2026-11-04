"""Bounded fresh retrieval-only OFF arm paired with the frozen current ON arm.

No model calls; scores the returned passages, never parent expansion or old hits.
"""
import json
from pathlib import Path
import statistics
import time
from ncd_gemma.capstone_eval.protocol import read_rows,verify_manifest,json_hash,write_json
from ncd_gemma.capstone_eval.runner import append_record
from ncd_gemma.capstone_eval.metrics import score_retrieval
from ncd_gemma import runtime_options
from ncd_gemma.config import load_environment
from ncd_gemma.schemas import SearchArgs

ROOT=Path(__file__).resolve().parents[1]
SOURCE='capstone-current-v2'
RUN='capstone-reranker-ablation-v1'

def main():
    load_environment()
    manifest=json.loads((ROOT/'reports'/SOURCE/'manifest.json').read_text(encoding='utf-8'))
    verify_manifest(ROOT,manifest)
    source=ROOT/'private'/SOURCE/'retrieval.jsonl'
    on=[r for r in read_rows(source) if r['arm']=='hybrid_current']
    questions=read_rows(ROOT/'reports'/SOURCE/'questions.jsonl')
    if len(on)!=30 or {r['qid'] for r in on}!={q['qid'] for q in questions} or any(r['manifest_hash']!=json_hash(manifest) or r['run_id']!=SOURCE for r in on):raise ValueError('Complete matching ON arm required')
    out=ROOT/'reports'/RUN;private=ROOT/'private'/RUN
    out.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True,exist_ok=True)
    raw=private/'retrieval_off.jsonl'
    if raw.exists():raise ValueError('Preserve existing ablation; no overwrite or automatic repeat')
    write_json(out/'manifest.json',dict(run_id=RUN,parent_run=SOURCE,parent_manifest_hash=json_hash(manifest),qids=[q['qid'] for q in questions],use_cache=False,use_reranker=False,variant='B',search_budget=30,model_call_budget=0,wall_seconds=2700,scope='Retrieval only; sequential paired ON/OFF timings, no answer-quality inference'))
    from ncd_gemma.retrieval import EvidenceRetriever
    base=EvidenceRetriever();off=[];start=time.monotonic()
    a=runtime_options.use_cache.set(False);b=runtime_options.use_reranker.set(False)
    try:
        for q in questions:
            if time.monotonic()-start>2700:raise RuntimeError('Ablation wall budget reached')
            verify_manifest(ROOT,manifest,full_data=False)
            t=time.monotonic();hits=base.search(SearchArgs(query=q['question'],top_k=5),variant='B')
            row=dict(run_id=RUN,parent_manifest_hash=json_hash(manifest),qid=q['qid'],hits=hits,elapsed_seconds=time.monotonic()-t,use_cache=False,use_reranker=False)
            append_record(raw,row);off.append(row)
            print(json.dumps(dict(completed=len(off),qid=q['qid'],seconds=row['elapsed_seconds'])),flush=True)
    finally:runtime_options.use_cache.reset(a);runtime_options.use_reranker.reset(b)
    verify_manifest(ROOT,manifest)
    result=dict(run_id=RUN,complete=True,n=30,reranker_on=score_retrieval(on,questions),reranker_off=score_retrieval(off,questions),
        median_seconds_on=statistics.median(r['elapsed_seconds'] for r in on),median_seconds_off=statistics.median(r['elapsed_seconds'] for r in off),
        scope='Fresh retrieval only; same current code/data/query and hybrid arm; sequential timing; no LLM calls or end-to-end answer claims')
    write_json(out/'metrics.json',result);print(json.dumps(result))

if __name__=='__main__':main()
