import numpy as np
from ncd_gemma.passage_rerank import PassageReranker

def test_rerank_reorders_without_changing_evidence_and_reuses_score_cache(tmp_path):
    class Model:
        calls=0
        def predict(self,pairs,**kwargs):
            self.calls+=1
            return np.array([.2,.8])
    ranker=PassageReranker.__new__(PassageReranker)
    ranker.model=Model();ranker.cache=tmp_path
    evidence=[{'chunk_id':'a','text':'หลักฐาน A'},{'chunk_id':'b','text':'หลักฐาน B'}]
    result=ranker.rank('คำถามทดสอบ',evidence)
    assert [s['chunk_id'] for s in result]==['b','a']
    assert {s['text'] for s in result}=={s['text'] for s in evidence}
    assert ranker.rank('คำถามทดสอบ',evidence)==result and ranker.model.calls==1

def test_structured_table_path_does_not_use_prose_reranker():
    ranker=PassageReranker.__new__(PassageReranker)
    evidence=[{'text':'เซลล์ตาราง','table_provenance':[{'pdf_page':1}]},{'text':'ข้อความ'}]
    assert ranker.rank('คำถาม',evidence)==evidence


def test_multi_part_or_numeric_query_keeps_lower_ranked_evidence(tmp_path):
    class Model:
        def predict(self,pairs,**kwargs):return np.arange(len(pairs))
    ranker=PassageReranker.__new__(PassageReranker)
    ranker.model=Model();ranker.cache=tmp_path
    evidence=[{'text':'หลักฐาน '+str(i)} for i in range(6)]
    assert len(ranker.rank('อุปกรณ์มีราคาและน้ำหนักเท่าไร',evidence))==6
    assert [s['text'] for s in ranker.rank('กลุ่ม A มีจำนวนและสัดส่วนเท่าไร',evidence)]==['หลักฐาน 5','หลักฐาน 4']
    assert len(ranker.rank('กิจกรรมสำหรับผู้เริ่มต้นคืออะไร',evidence))==2
