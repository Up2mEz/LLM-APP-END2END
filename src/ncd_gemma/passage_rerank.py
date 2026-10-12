"""Reuse the source project's cross-encoder on short, admitted passages."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path
from .config import ROOT
from .evidence import explicit_row_lookup

MODEL = 'BAAI/bge-reranker-v2-m3'
REVISION = '953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'


class PassageReranker:
    def __init__(self):
        self.model = None
        self.cache = ROOT/'.cache/passage-reranker'
        self.cache.mkdir(parents=True,exist_ok=True)

    def rank(self, question: str, evidence: list[dict]) -> list[dict]:
        if len(evidence)<=1 or any(e.get('table_provenance') for e in evidence):
            return evidence
        keys, scores, missing = [], [], []
        for i,e in enumerate(evidence):
            key = hashlib.sha256(json.dumps([MODEL,REVISION,512,question,e['text']],ensure_ascii=False).encode()).hexdigest()
            keys.append(key)
            path=self.cache/(key+'.json')
            try:
                score=json.loads(path.read_text())['score']
                if type(score) not in (int,float) or not math.isfinite(score):raise ValueError('Invalid cache')
            except (OSError,ValueError,KeyError,TypeError):
                score=None;missing.append(i)
            scores.append(score)
        if missing:
            if self.model is None:
                from sentence_transformers import CrossEncoder
                self.model=CrossEncoder(MODEL,max_length=512,device='cpu',local_files_only=True,revision=REVISION)
            values=self.model.predict([(question,evidence[i]['text']) for i in missing],batch_size=4,show_progress_bar=False)
            for i,value in zip(missing,values):
                scores[i]=float(value)
                (self.cache/(keys[i]+'.json')).write_text(json.dumps({'score':scores[i]}),encoding='utf8')
        # Do not threshold scores as probabilities or remove evidence merely for a low score.
        order=sorted(range(len(evidence)),key=lambda i:(-scores[i],i))
        # Start with a compact evidence pack; multi-part questions keep more
        # passages. The agent can request another search if a part is missing.
        compare = any(t in question for t in ('และ','พร้อม','กี่','เท่าไร','เท่าไหร่','แยก','หรือ')) or bool(re.search(r'\d',question))
        keep=len(evidence) if compare else 2
        if explicit_row_lookup(question):
            keep=2  # Keep the best row and its context, not other survey cohorts.
        return [{**evidence[i],'passage_rerank_score':scores[i]} for i in order[:keep]]
