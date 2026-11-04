import argparse
import json
from .protocol import RUN, select_questions, build_manifest, verify_manifest, write_json

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['plan','verify','pilot','retrieval','answers','run','summarize']);p.add_argument('--run',choices=[RUN],default=RUN);args=p.parse_args()
    from ncd_gemma.config import ROOT,load_environment
    load_environment();out=ROOT/'reports'/RUN;mp=out/'manifest.json'
    if args.command=='plan':
        if mp.exists():raise ValueError('Refuse overwrite: manifest exists')
        qs=select_questions(ROOT/'data/gold/questions_all_reviewed.jsonl');m=build_manifest(ROOT,qs)
        write_json(mp,m);(out/'questions.jsonl').write_text('\n'.join(json.dumps(q,ensure_ascii=False) for q in qs)+'\n',encoding='utf-8');print(json.dumps({'manifest':str(mp),'settings':m['settings'],'qids':m['qids']}));return
    m=json.loads(mp.read_text(encoding='utf-8'));verify_manifest(ROOT,m)
    if args.command=='verify':print('PASS manifest, code, data, questions');return
    if args.command=='summarize':
        from .metrics import summarize
        print(json.dumps(summarize(ROOT,m),ensure_ascii=False));return
    from .runner import run_stage
    if args.command=='run':
        from ncd_gemma.retrieval import EvidenceRetriever
        base=EvidenceRetriever()
        for stage in ('pilot','retrieval','answers'):run_stage(ROOT,m,stage,base)
    else:run_stage(ROOT,m,args.command)

if __name__=='__main__':main()
