"""Synthetic PDF table fixture: no course gold or corpus is used."""
from types import SimpleNamespace

from ncd_gemma.pdf_tables import transcribe_table
from ncd_gemma.evidence import TableContext
from ncd_gemma.pdf_tables import render_table_selection
from ncd_gemma.pdf_tables import resolve_table_line, reviewed_table_answer
import pytest


def test_merged_headers_and_missing_left_border_preserve_value_meaning():
    # Two stacked headers, with a parent header spanning the two components.
    rows = [SimpleNamespace(cells=[(100,0,200,40),(200,0,400,20),None], bbox=(100,0,400,40)),
            SimpleNamespace(cells=[None,(200,20,300,40),(300,20,400,40)], bbox=(200,20,400,40)),
            SimpleNamespace(cells=[(100,40,200,60),(200,40,300,60),(300,40,400,60)], bbox=(100,40,400,60)),
            SimpleNamespace(cells=[(100,60,200,80),(200,60,300,80),(300,60,400,80)], bbox=(100,60,400,80))]
    table = SimpleNamespace(rows=rows, bbox=(100,0,400,80),
                            extract=lambda: [['Total','Components',None],[None,'Milk','Food'],['90','40','50'],['95','42','53']])
    page = SimpleNamespace(get_text=lambda _: [(20,10,80,30,'Age',0,0,0),
                                               (20,43,80,61,'Group-A',0,0,0),
                                               (20,63,80,81,'Group-B',0,0,0)])
    result = transcribe_table(page, table)
    assert result['rows'][0]['cells'] == {'Age':'Group-A','Total':'90','Components / Milk':'40','Components / Food':'50'}
    assert result['rows'][1]['cells']['Age'] == 'Group-B'


def test_table_context_requires_same_document_edition_and_page():
    hit = dict(chunk_id='chunk',document_id='doc',edition_id='current',pdf_page_start=2,pdf_page_end=2,text='1 2 3 4\n5 6 7 8')
    table = dict(document_id='doc',edition_id='current',pdf_page=2,bbox=[0,0,10,10],pdf_sha256='hash',rows=[{'cells':{'Age':'A','Total':'90','Food':'50'}}])
    wrong = {**table,'edition_id':'old','rows':[{'cells':{'Wrong':'999'}}]}
    result = TableContext([hit],[table,wrong]).enrich(hit)
    assert 'Food = 50' in result['text']
    assert '999' not in result['text']
    assert result['table_provenance'][0]['pdf_sha256'] == 'hash'


def test_table_answer_cannot_rename_total_as_one_component():
    source = {'S1':{'text':'ตาราง PDF หน้า 3: C0 อายุ = A; C1 โปรตีนรวม = 93; C2 โปรตีนจากนม = 41; C3 โปรตีนจากอาหาร = 52'}}
    result = render_table_selection({'status':'answered','table_cells':[{'source_id':'S1','line':1,'columns':[1]}]}, source)
    assert result['answer'] == 'อายุ = A: โปรตีนรวม = 93 [S1]'
    assert 'โปรตีนจากอาหาร = 93' not in result['answer']
    with pytest.raises(ValueError):
        render_table_selection({'status':'answered','table_cells':[{'source_id':'S1','line':1,'columns':[99]}]}, source)
    with pytest.raises(ValueError):
        render_table_selection({'status':'answered','answer':'invented','table_cells':[]}, source)


def test_flattened_row_resolves_only_when_all_values_match_uniquely():
    source = {'text':'ตาราง PDF หน้า 3: C0 อายุ = 5-7; C1 รวม = 93; C2 นม = 41; C3 อาหาร = 52\n5-7 93 41 52'}
    assert resolve_table_line(source,2) == 1
    source['text'] += '\n' + source['text'].splitlines()[0]
    with pytest.raises(ValueError): resolve_table_line(source,2)


def test_reviewed_table_renders_all_checked_rows_without_dropping_a_required_value():
    sources = {'S1':{'text':'ตาราง PDF หน้า 3: C0 อายุ = 5-7; C1 พลังงานรวม = 900; C2 จากอาหาร = 450\nตาราง PDF หน้า 4: C0 อายุ = 5-7; C1 โปรตีนรวม = 99; C2 จากอาหาร = 49'}}
    review = SimpleNamespace(checks=[SimpleNamespace(source_id='S1',start_line=1,end_line=1),SimpleNamespace(source_id='S1',start_line=2,end_line=2)])
    result = reviewed_table_answer(review,sources)
    assert 'พลังงานรวม = 900' in result['answer'] and 'โปรตีนรวม = 99' in result['answer']
    assert 'จากอาหาร = 450' in result['answer'] and 'จากอาหาร = 49' in result['answer']


def test_extra_model_prose_cannot_override_selected_cell_values():
    source = {'S1':{'text':'ตาราง PDF หน้า 3: C0 กลุ่ม = A; C1 รวม = 900; C2 อาหาร = 450'}}
    result=render_table_selection({'status':'answered','answer':'อาหาร = 900', 'citations':[],
        'table_cells':[{'source_id':'S1','line':1,'columns':[2]}]},source)
    assert result['answer'] == 'กลุ่ม = A: อาหาร = 450 [S1]'
