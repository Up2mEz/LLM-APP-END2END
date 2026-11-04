"""Paired answer-score comparison; requires complete blinded judgments."""
from __future__ import annotations
import json,math,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from ncd_gemma.capstone_eval.runner import service_failure
RUN='paired-agent-v30-current-20261105'
def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def paired_counts(old,new):
    if set(old)!=set(new) or not old:raise ValueError('Unpaired questions')
    pairs=[(old[k],new[k]) for k in sorted(old)]
    gained=sum(not a and b for a,b in pairs);lost=sum(a and not b for a,b in pairs);n=len(pairs)
    discordant=gained+lost
    p=min(1,2*sum(math.comb(discordant,k) for k in range(min(gained,lost)+1))/2**discordant) if discordant else 1.0
    rng=random.Random(20261105);diffs=[]
    for _ in range(5000):
        sample=rng.choices(pairs,k=n);diffs.append(sum(int(b)-int(a) for a,b in sample)/n)
    diffs.sort()
    return dict(n=n,old_successes=sum(a for a,b in pairs),current_successes=sum(b for a,b in pairs),both_success=sum(a and b for a,b in pairs),both_fail=sum(not a and not b for a,b in pairs),current_only_success=gained,old_only_success=lost,success_rate_difference=(gained-lost)/n,paired_bootstrap_95_interval=[diffs[124],diffs[4874]],mcnemar_exact_two_sided_p=p)
def main():
    out=ROOT/'reports'/RUN;private=ROOT/'private'/RUN
    metric=json.loads((out/'judge_metrics.json').read_text())
    if not metric['complete']:raise ValueError('Incomplete judge')
    key={r['item_id']:r for r in rows(private/'review_key.jsonl')}
    failed={(r['qid'],r['arm']):service_failure(r['prediction']) for r in rows(private/'answers.jsonl')}
    groups={'old_v30':{},'current':{}}
    paired={}
    for r in rows(out/'judge_verdicts.jsonl'):
        k=key[r['item_id']];groups[k['arm']][k['qid']]=not failed[k['qid'],k['arm']] and r['verdict'] in ('correct','correct_abstention')
        paired.setdefault(k['qid'],{'qid':k['qid']})[k['arm']]={**r,'verdict':'service_error' if failed[k['qid'],k['arm']] else r['verdict']}
    if any(len(g)!=60 for g in groups.values()):raise ValueError('Expected two complete 60-question arms')
    result=paired_counts(groups['old_v30'],groups['current']);result.update(run_id=RUN,scope='Paired exposed development set; one draw per arm; LLM judge uncertainty not included in statistical interval')
    for arm in groups:
        if sum(groups[arm].values())!=metric['arms'][arm]['successes']:raise ValueError('Paired scorer differs from judge collector')
    (out/'paired_verdicts.jsonl').write_text(''.join(json.dumps(paired[q],ensure_ascii=False)+'\n' for q in sorted(paired)),encoding='utf-8')
    (out/'paired_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
def public_summary():
    records=rows(ROOT/'reports'/RUN/'paired_verdicts.jsonl')
    if len(records)!=60 or len({r['qid'] for r in records})!=60:raise ValueError('Expected 60 unique public pairs')
    groups={arm:{r['qid']:r[arm]['verdict'] in ('correct','correct_abstention') for r in records} for arm in ('old_v30','current')}
    result=paired_counts(groups['old_v30'],groups['current'])
    saved=json.loads((ROOT/'reports'/RUN/'paired_summary.json').read_text())
    if any(saved[k]!=v for k,v in result.items()):raise ValueError('Public verdicts do not reproduce saved aggregate')
    print(json.dumps({'verified_from_public_verdicts':True,**result}))

if __name__=='__main__':
    if '--public' in sys.argv:public_summary()
    else:main()
