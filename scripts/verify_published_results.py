"""Recompute published scores from saved evidence, without network/model calls."""
from pathlib import Path
import gzip
import hashlib
import json
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from ncd_gemma.capstone_eval.metrics import score_retrieval, score_answers
from ncd_gemma.capstone_eval.runner import service_failure
from summarize_paired_agents import paired_counts

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]

def verify():
    folder = ROOT / 'reports/published-evidence'
    data = {}
    for f in read(folder / 'manifest.json')['files']:
        compressed = (folder / f['file']).read_bytes()
        if hashlib.sha256(compressed).hexdigest() != f['compressed_sha256']:
            raise ValueError('Compressed evidence hash mismatch')
        raw = gzip.decompress(compressed)
        if hashlib.sha256(raw).hexdigest() != f['sha256']:
            raise ValueError('Evidence hash mismatch')
        records = [json.loads(line) for line in raw.decode('utf-8').splitlines() if line]
        if len(records) != f['rows']:
            raise ValueError('Evidence row count mismatch')
        data[f['run'], f['name']] = records
    results = {}
    for run, arms, count in [('capstone-current-v2', ('dense_default','hybrid_current'),30), ('paired-agent-v30-current-20261105', ('old_v30','current'),60)]:
        base = ROOT / 'reports' / run
        answers = data[run,'answers.jsonl']
        questions = rows(base / 'questions.jsonl')
        qids = {q['qid'] for q in questions}
        if len(qids) != count or len(answers) != count * 2 or len({(a['qid'],a['arm']) for a in answers}) != count * 2:
            raise ValueError('Missing or duplicated answer records')
        if any(a['run_id'] != run or a['qid'] not in qids or a['arm'] not in arms for a in answers):
            raise ValueError('Foreign run/question/arm')
        if run == 'capstone-current-v2':
            saved = read(base / 'metrics.json')
            retrieval = data[run,'retrieval.jsonl']
            if len(retrieval)!=count*2 or {(r['qid'],r['arm']) for r in retrieval}!={(q,arm) for q in qids for arm in arms}:
                raise ValueError('Missing or duplicated retrieval records')
            if any(r['run_id']!=run for r in retrieval):raise ValueError('Foreign retrieval run')
            for arm in arms:
                if score_retrieval([r for r in retrieval if r['arm']==arm],questions) != saved['retrieval'][arm]:
                    raise ValueError('Retrieval scores differ')
                if score_answers([r for r in answers if r['arm']==arm],questions) != saved['answers'][arm]:
                    raise ValueError('Answer scores differ')
        key = {k['item_id']:k for k in data[run,'review_key.jsonl']}
        judgments = rows(base / 'judge_verdicts.jsonl')
        if len(judgments)!=count*2 or {j['item_id'] for j in judgments}!=set(key):
            raise ValueError('Incomplete judge IDs')
        failed={(a['qid'],a['arm']):service_failure(a['prediction']) for a in answers}
        groups={arm:{} for arm in arms};counts={arm:Counter() for arm in arms}
        for j in judgments:
            k=key[j['item_id']];arm=k['arm'];qid=k['qid']
            verdict='service_error' if failed[qid,arm] else j['verdict']
            counts[arm][verdict]+=1
            groups[arm][qid]=verdict in ('correct','correct_abstention')
        saved_judge=read(base/'judge_metrics.json')
        for arm in arms:
            if set(groups[arm])!=qids or sum(groups[arm].values())!=saved_judge['arms'][arm]['successes']:
                raise ValueError('Judge scores differ')
            if dict(counts[arm]) != saved_judge['arms'][arm]['verdict_counts']:
                raise ValueError('Judge verdict distribution differs')
        if run.startswith('paired-'):
            paired=paired_counts(groups['old_v30'],groups['current'])
            saved_pair=read(base/'paired_summary.json')
            if any(saved_pair[k]!=v for k,v in paired.items()):raise ValueError('Paired summary differs')
        results[run]={arm:sum(groups[arm].values()) for arm in arms}
    return {'verified':True,'model_calls':0,'results':results}

if __name__ == '__main__':
    print(json.dumps(verify(),indent=2))
