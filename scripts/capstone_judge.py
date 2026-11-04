"""Prepare blinded packets and validate external Luna judgments; never calls a model."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERDICTS={'correct','partial','wrong','unsupported','correct_abstention','false_abstention','service_error','uncertain'}
def read(path):return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rows(path,value):path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in value),encoding='utf-8')

def validate(judgments,expected):
    ids=[r['item_id'] for r in judgments]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):raise ValueError('Incomplete, duplicate or foreign judge item IDs')
    for r in judgments:
        if r.get('verdict') not in VERDICTS or not isinstance(r.get('reason'),str) or not r['reason'].strip() or not isinstance(r.get('evidence_refs'),list):
            raise ValueError('Invalid judge schema')
        if '???' in json.dumps(r,ensure_ascii=False) or '\ufffd' in json.dumps(r,ensure_ascii=False):
            raise ValueError('Corrupted judge rationale encoding')

def aggregate(judgments,packet,key):
    validate(judgments,[p['item_id'] for p in packet])
    mapping={p['item_id']:p for p in key};flags={p['item_id']:p.get('service_failure',False) for p in packet}
    if set(mapping)!=set(flags):raise ValueError('Packet/key mismatch')
    groups={}
    for r in judgments:
        arm=mapping[r['item_id']]['arm']
        verdict='service_error' if flags[r['item_id']] else r['verdict']
        groups.setdefault(arm,[]).append(verdict)
    return {arm:dict(n=len(vs),successes=sum(v in ('correct','correct_abstention') for v in vs),
                     semantic_success=sum(v in ('correct','correct_abstention') for v in vs)/len(vs),verdict_counts=dict(Counter(vs))) for arm,vs in groups.items()}

def prepare(run):
    from ncd_gemma.capstone_eval.runner import service_failure
    source=ROOT/'reports'/run;private=ROOT/'private'/run
    metrics=json.loads((source/'metrics.json').read_text(encoding='utf-8'))
    if metrics.get('run_id')!=run or not metrics.get('complete'):raise ValueError('Fresh complete run required')
    packet=read(source/'review_packet.jsonl');key=read(private/'review_key.jsonl')
    raw={(r['qid'],r['arm']):r for r in read(private/'answers.jsonl')}
    mapping={r['item_id']:r for r in key}
    for p in packet:
        k=mapping[p['item_id']];p['service_failure']=service_failure(raw[k['qid'],k['arm']]['prediction'])
    folder=private/'judge';folder.mkdir(exist_ok=True)
    if (folder/'batch_manifest.json').exists():raise ValueError('Judge packets already frozen')
    rows(folder/'packet.jsonl',packet)
    batches=[]
    for start in range(0,len(packet),6):
        name=f'batch-{start//6+1:02}.jsonl';path=folder/name;part=packet[start:start+6];rows(path,part)
        batches.append(dict(file=name,sha256=sha(path),item_ids=[p['item_id'] for p in part]))
    save(folder/'batch_manifest.json',dict(run_id=run,raw_sha256=sha(private/'answers.jsonl'),packet_sha256=sha(folder/'packet.jsonl'),
        key_sha256=sha(private/'review_key.jsonl'),rubric_sha256=sha(ROOT/'docs/CAPSTONE_JUDGE_RUBRIC.md'),batches=batches))
    print(json.dumps(dict(batches=len(batches),items=len(packet))))

def collect(run):
    folder=ROOT/'private'/run/'judge';manifest=json.loads((folder/'batch_manifest.json').read_text(encoding='utf-8'))
    if manifest['run_id']!=run or manifest['packet_sha256']!=sha(folder/'packet.jsonl') or manifest['raw_sha256']!=sha(folder.parent/'answers.jsonl') or manifest['key_sha256']!=sha(folder.parent/'review_key.jsonl') or manifest['rubric_sha256']!=sha(ROOT/'docs/CAPSTONE_JUDGE_RUBRIC.md'):raise ValueError('Judge provenance drift')
    judgments=[]
    for batch in manifest['batches']:
        if sha(folder/batch['file'])!=batch['sha256']:raise ValueError('Batch drift')
        output=folder/batch['file'].replace('.jsonl','.judgments.jsonl')
        part=read(output);validate(part,batch['item_ids']);judgments+=part
    packet=read(folder/'packet.jsonl');key=read(folder.parent/'review_key.jsonl')
    result=dict(run_id=run,review_type='LLM-as-judge',model='gpt-6-luna',reasoning_effort='xhigh',temperature='not exposed by T3 transport',
        human_review=False,complete=True,arms=aggregate(judgments,packet,key),packet_sha256=manifest['packet_sha256'],
        judgments_sha256={b['file']:sha(folder/b['file'].replace('.jsonl','.judgments.jsonl')) for b in manifest['batches']})
    out=ROOT/'reports'/run;save(out/'judge_metrics.json',result);rows(out/'judge_verdicts.jsonl',judgments)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','collect']);parser.add_argument('--run',required=True)
    args=parser.parse_args();{'prepare':prepare,'collect':collect}[args.command](args.run)
