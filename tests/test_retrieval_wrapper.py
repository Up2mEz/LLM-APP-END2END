from threading import Lock

from ncd_gemma.retrieval import EvidenceRetriever
from ncd_gemma.schemas import SearchArgs


def test_explicit_field_comparison_admits_literal_frozen_parent():
    class Raw:
        def __init__(self):
            self.queries = []

        def search(self, query, **kwargs):
            self.queries.append(query)
            return [{'chunk_id': 'generic', 'document_id': 'doc', 'edition_id': 'e', 'text': 'generic'}]

    class Identity:
        def enrich(self, hit):
            return hit

        def select(self, hit, query):
            return [hit]

        def rank(self, query, hits):
            return hits

    retriever = EvidenceRetriever.__new__(EvidenceRetriever)
    retriever.raw = Raw()
    retriever.raw.parents = [{'chunk_id': 'specific', 'document_id': 'doc', 'edition_id': 'e',
                              'text': 'แยกน้ำหนักและส่วนสูง รอบเอว รอบสะโพก'}]
    retriever.lock = Lock()
    retriever.table_context = Identity()
    retriever.focus = Identity()
    retriever.passage_reranker = Identity()
    retriever.allowed = {key: set() for key in ('document_id','primary_group','document_type','population')}
    question = 'ฐานข้อมูลควรแยกเก็บน้ำหนักกับส่วนสูงหรือรวมเป็นค่าเดียว'
    result = retriever.search(SearchArgs(query=question))
    assert retriever.raw.queries == [question]
    assert [hit['chunk_id'] for hit in result] == ['specific', 'generic']
