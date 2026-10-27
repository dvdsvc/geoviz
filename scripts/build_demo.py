"""Rebuild explicitly synthetic sample/spot/provenance fixtures.

Writes only the bundled demo paths in this showcase. No source paper or
historical research record is used to generate these observations.
"""
from pathlib import Path
import csv
import json
import math

ROOT=Path(__file__).resolve().parents[1]


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    samples=[];spots=[];ages=[];provenances=[]
    paper='synthetic-demo-paper'
    centers=[103.,110.,118.,125.,130.,138.,145.,150.]
    positions=[(28.9,121.0),(28.6,120.0),(27.3,119.0),(26.6,118.1),
               (28.1,118.7),(29.,120.1),(27.8,117.3),(28.2,119.2)]
    provinces=['浙江','浙江','福建','福建','江西','浙江','江西','浙江']
    rocks=['凝灰岩','流纹岩','凝灰岩','砂岩','玄武岩','凝灰岩','流纹岩','凝灰岩']
    for index,(age,(lat,lng)) in enumerate(zip(centers,positions),1):
        sid=f'DEMO{index:02d}'
        sample={
            'id':str(index),'dataId':f'D{index:03d}','sampleId':sid,
            'region':'华南','regionProvince':provinces[index-1],
            'basin':f'合成盆地{(index+1)//2}','location':'合成位置',
            'city':'演示地点','specificLocation':'虚构采样点，非真实观测',
            'gps':f'{lat}, {lng}','lat':lat,'lng':lng,
            'group':'演示群','formation':f'合成组{(index+1)//2}','memberDepth':'演示层位',
            'rockType':rocks[index-1],'datingMineral':'Zircon','datingSystem':'U-Th-Pb dating',
            'technique':'LA-ICPMS','ageMa':age,'error':round(1/math.sqrt(3),4) if index==1 else .4,
            'mswd':None,'nGrains':6,'ageType':'Synthetic weighted mean',
            'physicalMethod':'Spot','distributionState':'Synthetic illustrative distribution',
            'reference':paper,'remarks':'SYNTHETIC DEMO ONLY; no geological inference.'}
        samples.append(sample)
        ages.append({'sample_id':sid,'age_Ma':f"{age}±{sample['error']}",
            'Region_Province':sample['regionProvince'],'GPS':sample['gps'],
            'Basin':sample['basin'],'Formation':sample['formation'],'Group':sample['group'],
            'Rock_type':sample['rockType'],'Dating_mineral':sample['datingMineral'],
            'Isotope_system':sample['datingSystem'],'Dating_Technique':sample['technique'],
            'Statistical_Model':sample['ageType'],'n':6})
        values=[100.,102.,104.,106.,108.,110.] if index==1 else [age+d for d in (-1.,-.6,-.2,.2,.6,1.)]
        errors=[1.,1.,2.,2.,2.,2.] if index==1 else [1.]*6
        for j,(value,error) in enumerate(zip(values,errors),1):
            spots.append({'spot_id':str(j),'sample_id':sid,'s_discarded':False,
                'u_ppm':100.+j,'th_ppm':40.+j,'th_u_ratio':.4,
                'r206_238_val':math.expm1(1.55125e-10*value*1e6),
                'r206_238_err':.0001,
                'r207_235_val':math.expm1(9.8485e-10*value*1e6),
                'r207_235_err':.0005,'r207_206_val':None,'r207_206_err':None,
                'age_206_238_val':value,'age_206_238_err':error,
                'age_207_235_val':value,'age_207_235_err':error,'concordance':100.})
        y=240+(index-1)*78
        provenances.append({'data_type':'age','record_id':sid,'label':'Synthetic age',
            'display':f'{age} Ma','page':1,'bbox':[70,y-27,820,y+28],
            'bbox_norm':[70/900,(y-27)/1200,820/900,(y+28)/1200],
            'matched_text':f'{sid} age {age} Ma','match_type':'synthetic_fixture'})

    write_json(ROOT/'frontend/src/data/realSamples.json',samples)
    write_json(ROOT/'frontend/src/data/realSpots.json',spots)
    write_json(ROOT/'data/demo/pipeline'/f'{paper}_ages.json',ages)
    write_json(ROOT/'data/demo/papers.json',[paper])
    with (ROOT/'frontend/src/data/spots.csv').open('w',newline='') as handle:
        headers=[key for key in spots[0] if key!='s_discarded']
        writer=csv.DictWriter(handle,fieldnames=headers,extrasaction='ignore')
        writer.writeheader();writer.writerows(spots)
    page_dir=ROOT/'data/demo/provenance'/f'{paper}_pages'
    page_dir.mkdir(parents=True,exist_ok=True)
    rows=''.join(f'<text x="80" y="{240+i*78}" font-size="21">{s["sampleId"]} | {s["ageMa"]} Ma | SYNTHETIC</text>' for i,s in enumerate(samples))
    (page_dir/'page_1.svg').write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200" viewBox="0 0 900 1200">
<rect width="900" height="1200" fill="white"/><g font-family="sans-serif" fill="#1e293b">
<text x="80" y="100" font-size="31" font-weight="bold">SYNTHETIC DATA SHEET</text>
<text x="80" y="145" font-size="17">Generated demonstration. No source publication or measured observations.</text>
{rows}<text x="80" y="1030" font-size="17">Coordinates and values illustrate the GeoViz interface only.</text>
</g></svg>''')
    write_json(ROOT/'data/demo/provenance'/f'{paper}_provenance.json',{
        'paper_name':paper,'pdf_path':'','total_pages':1,'total_fields':len(provenances),
        'found_count':len(provenances),'not_found_count':0,
        'page_images':[{'page':1,'image':'page_1.svg','width':900,'height':1200,'dpi':72}],
        'provenances':provenances})
    write_json(ROOT/'data/demo/README.json',{'kind':'synthetic demonstration only',
        'samples':len(samples),'spots':len(spots),'provenance_fields':len(provenances),
        'source_paper_used':False,'historical_observations_used':False,
        'legacy_frontend_filenames':'realSamples.json / realSpots.json kept for import compatibility; contents are synthetic.'})
    print(json.dumps({'samples':len(samples),'spots':len(spots),'source_page':'synthetic SVG','model_api_called':False}))


if __name__=='__main__':main()
