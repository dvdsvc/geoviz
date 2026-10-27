"""Offline API, source-data binding, graph and PDF-matching smoke checks."""
from pathlib import Path
import json
import math
import os
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ['GEOVIZ_DEMO_MODE']='1'

from fastapi.testclient import TestClient
from main import app
from knowledge_graph import KnowledgeGraph
from provenance_mapper import find_in_pdf
import fitz


def main():
    client=TestClient(app)
    with patch('mimo_client.MiMoClient.chat',side_effect=AssertionError('No model calls allowed')):
        health=client.get('/api/health');assert health.json()['mode']=='synthetic-demo'
        samples=client.get('/api/samples').json()['samples'];assert len(samples)==8
        assert len({s['sampleId'] for s in samples})==8
        spots=client.get('/api/spots').json();assert spots['total_spots']==48
        assert set(spots['samples'])=={s['sampleId'] for s in samples}
        response=client.post('/api/chat',json={'query':'凝灰岩'});assert response.status_code==200
        chat=response.json();assert chat['matched_count']==4
        assert chat['filters']['mode']=='synthetic-keyword-demo'
        assert '合成数据演示' in chat['answer']
        assert client.post('/api/v2/chat',json={'query':'x'}).status_code==503
        assert client.get('/api/graphrag/stats').status_code==503
        provenance=client.get('/api/provenance/synthetic-demo-paper').json()
        assert len(provenance['provenances'])==8
        page=client.get('/api/provenance/synthetic-demo-paper/pages/page_1.svg')
        assert page.status_code==200 and 'SYNTHETIC DATA SHEET' in page.text
        grains=[{'sampleId':'CHECK','ageMa':a,'error':e} for a,e in
                zip([100,102,104,106,108,110],[1,1,2,2,2,2])]
        assert client.post('/api/grains/bulk',json={'grains':grains}).json()['uploaded']==6
        weighted=client.get('/api/grains/CHECK').json()
        assert weighted['weightedMean']==103 and weighted['weightedError']==.5774
        assert weighted['mswd']==6.2
        client.delete('/api/grains')
    graph=KnowledgeGraph(samples)
    assert graph.G.number_of_nodes()>8 and graph.G.number_of_edges()>8
    with fitz.open() as document:
        text='Synthetic DEMO01 zircon age 103.0 Ma. Controlled text for source alignment.'
        document.new_page().insert_text((72,100),text,fontsize=11)
        result=find_in_pdf(document,text,record_id='DEMO01')
        assert result[0]==1 and result[1] and result[2],result
        pdf_method=result[3]
    print(json.dumps({'mode':'offline synthetic checks','samples':8,'spots':48,
        'keyword_matches':chat['matched_count'],'weighted_mean':103,'weighted_error':.5774,
        'mswd':6.2,'provenance_fields':8,'source_page_served':True,
        'graph_nodes':graph.G.number_of_nodes(),'graph_edges':graph.G.number_of_edges(),
        'generated_pdf_match_method':pdf_method,'live_model_called':False,'passed':True},indent=2))


if __name__=='__main__':main()
