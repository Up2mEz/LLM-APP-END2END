"""Question-focused windows over admitted evidence; no gold/reference input."""
import math
from collections import Counter
from hashlib import sha256
from .evidence import table_like


class PassageFocus:
    def __init__(self, parents):
        from ncdqa.retrieval.thai_tokens import tokenize
        self.tokenize = lambda text: set(tokenize(text, 'char3', ()))
        df = Counter()
        for parent in parents:
            df.update(self.tokenize(parent['text']))
        self.idf = {t: math.log(1 + len(parents)/(1+n)) for t,n in df.items()}

    def select(self, hit, question):
        # Keep structured rows/headers intact for the deterministic table path.
        if hit.get('table_provenance') or table_like(hit['text']) or len(hit['text']) <= 1400:
            return [hit]
        lines = hit['text'].splitlines()
        tokens = self.tokenize(question)
        windows = []
        for start in range(0,len(lines),3):
            end = start
            while end < len(lines) and (end == start or len('\n'.join(lines[start:end+1])) <= 1100):
                end += 1
            text = '\n'.join(lines[start:end])
            have = self.tokenize(text)
            score = sum(self.idf.get(t,1) for t in tokens & have) / (max(150,len(text)) ** .2)
            windows.append((score,start,end,text))
        selected = []
        for score,start,end,text in sorted(windows,key=lambda w:(-w[0],w[1])):
            if len(text)<8 or any(max(0,min(end,e)-max(start,s)) > .35*min(end-start,e-s) for _,s,e,_ in selected):
                continue
            selected.append((score,start,end,text))
            if len(selected)==2:break
        # A scored window can end on a label just before its value or condition.
        # Keep a bounded continuation from this same parent; never invent text.
        extended = []
        for score,start,end,text in selected:
            stop = min(len(lines), end+4)
            while end < stop and len('\n'.join(lines[start:end+1])) <= 1700:
                end += 1
            extended.append((score,start,end,'\n'.join(lines[start:end])))
        return [{**hit,'text':text,'evidence_id':hit['chunk_id']+':window:'+str(start)+':'+str(end),
                 'focus_window':{'start_line':start+1,'end_line':end,'parent_text_sha256':sha256(hit['text'].encode()).hexdigest()}}
                for _,start,end,text in extended]
